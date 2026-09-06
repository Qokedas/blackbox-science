#!/usr/bin/env python3
"""Direct-space solution with ObjCryst++/FOX (pyobjcryst) for calibration runs. Authoring-side only.

Modes
  oracle : cell + space group taken from the truth; molecular model built from the shipped SMILES with RDKit
           (ETKDG + MMFF conformer, heavy atoms only) and imported as a Fenske-Hall Z-matrix (torsions free).
           This is the "oracle-assisted" resource check of the spec: does the search find the structure at all,
           and how long does it take, when indexing and symmetry are handed over?
  routine: nothing handed over. Peak search + quick_index on the pattern, SpaceGroupExplorer on the best cell,
           then the same model and search. This is the no-judgement comparator.

Progress: the best configuration is exported as CIF every chunk and graded with tests/grade.py's S logic
against the truth; the log records chi2, Rwp and S status per chunk, so time-to-solution can be read off.

Usage: fox_solve.py --mode oracle --instance <dir with pattern.xye/composition.json/instrument.json>
                    --truth <truth json> --grader <tests dir> --out <dir> [--runs 4 --steps 3000000 --max-minutes 120 --seed 0]
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np


def build_zmatrix(smiles, seed=0):
    """RDKit conformer (heavy atoms only) -> named Fenske-Hall Z-matrix text and heavy-atom element list."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    ps = AllChem.ETKDGv3()
    ps.randomSeed = seed
    if AllChem.EmbedMolecule(mol, ps) < 0:
        ps.useRandomCoords = True
        AllChem.EmbedMolecule(mol, ps)
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=2000)
    except Exception:
        pass
    heavy = Chem.RemoveHs(mol)
    conf = heavy.GetConformer()
    n = heavy.GetNumAtoms()
    pos = np.array([list(conf.GetAtomPosition(i)) for i in range(n)])
    els = [a.GetSymbol() for a in heavy.GetAtoms()]
    if n == 1:
        return "1\n%s1 %s 0\n" % (els[0], els[0]), els
    # BFS order from the most central atom
    import networkx as nx
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for b in heavy.GetBonds():
        G.add_edge(b.GetBeginAtomIdx(), b.GetEndAtomIdx())
    centre = min(G.nodes, key=lambda i: max(nx.single_source_shortest_path_length(G, i).values()))
    order = list(nx.bfs_tree(G, centre))
    parent = dict(nx.bfs_predecessors(G, centre))
    newidx = {a: k for k, a in enumerate(order)}

    def dist(i, j):
        return float(np.linalg.norm(pos[i] - pos[j]))

    def angle(i, j, k):
        v1, v2 = pos[i] - pos[j], pos[k] - pos[j]
        c = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        return math.degrees(math.acos(max(-1, min(1, c))))

    def dihedral(i, j, k, l):
        b0, b1, b2 = pos[i] - pos[j], pos[k] - pos[j], pos[l] - pos[k]
        b1n = b1 / np.linalg.norm(b1)
        v = b0 - np.dot(b0, b1n) * b1n
        w = b2 - np.dot(b2, b1n) * b1n
        x = np.dot(v, w)
        y = np.dot(np.cross(b1n, v), w)
        return math.degrees(math.atan2(y, x))

    # named Fenske-Hall format (FOX): "name symbol bondName bond angleName angle dihedName dihed"; first line "name symbol 0"
    names = {a: "%s%d" % (els[a], k + 1) for k, a in enumerate(order)}
    lines = ["%d" % n]
    for k, a in enumerate(order):
        name = names[a]
        if k == 0:
            lines.append("%s %s 0" % (name, els[a]))
            continue
        p = parent[a]
        if k == 1:
            lines.append("%s %s %s %.4f" % (name, els[a], names[p], dist(a, p)))
            continue
        gp = parent.get(p)
        if gp is None or gp == a:
            cands = [x for x in order[:k] if x != p and G.has_edge(x, p)]
            gp = cands[0] if cands else [x for x in order[:k] if x != p][0]
        if k == 2:
            lines.append("%s %s %s %.4f %s %.3f" % (name, els[a], names[p], dist(a, p), names[gp], angle(a, p, gp)))
            continue
        ggp = parent.get(gp)
        if ggp is None or ggp in (a, p):
            cands = [x for x in order[:k] if x not in (a, p, gp) and (G.has_edge(x, gp) or G.has_edge(x, p))]
            ggp = cands[0] if cands else [x for x in order[:k] if x not in (a, p, gp)][0]
        lines.append("%s %s %s %.4f %s %.3f %s %.3f" % (name, els[a], names[p], dist(a, p), names[gp], angle(a, p, gp), names[ggp], dihedral(a, p, gp, ggp)))
    return "\n".join(lines) + "\n", [els[a] for a in order]


def read_xye(path):
    x, y, s = [], [], []
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        p = line.split()
        x.append(float(p[0]))
        y.append(float(p[1]))
        s.append(float(p[2]) if len(p) > 2 else math.sqrt(max(abs(float(p[1])), 1)))
    return np.array(x), np.array(y), np.array(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("oracle", "routine"), required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--grader", required=True, help="tests dir containing grade.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=4)
    ap.add_argument("--steps", type=int, default=2000000, help="MC trials per run")
    ap.add_argument("--chunk", type=int, default=200000)
    ap.add_argument("--max-minutes", type=float, default=120)
    ap.add_argument("--dmin", type=float, default=1.7, help="resolution cut for the search (A)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    log = open(os.path.join(args.out, "log.jsonl"), "a")

    def L(**kw):
        kw["t"] = round(time.time() - T0, 1)
        log.write(json.dumps(kw) + "\n")
        log.flush()
        print(kw, flush=True)

    T0 = time.time()
    import pyobjcryst
    from pyobjcryst.crystal import Crystal
    from pyobjcryst.powderpattern import PowderPattern, ReflectionProfileType, SpaceGroupExplorer
    from pyobjcryst.molecule import ImportFenskeHallZMatrix
    from pyobjcryst.globaloptim import MonteCarlo, AnnealingSchedule
    from pyobjcryst.indexing import quick_index
    from pyobjcryst.radiation import RadiationType
    sys.path.insert(0, args.grader)
    import grade as GR
    GR.load_deps()

    truth = json.load(open(args.truth))
    comp = json.load(open(os.path.join(args.instance, "composition.json")))
    inst = json.load(open(os.path.join(args.instance, "instrument.json")))
    xye = os.path.join(args.instance, "pattern.xye")
    wl = inst["radiation"]["wavelength_A"]
    x, y, s = read_xye(xye)

    # -------- cell and space group
    if args.mode == "oracle":
        ref = GR.structure_from_cif(truth["reference_cif"])
        a, b, c, al, be, ga = ref.lattice.parameters
        sg = truth["space_group_symbol"]
        L(stage="cell", source="truth", cell=[a, b, c, al, be, ga], sg=sg)
    else:
        p0 = PowderPattern()
        p0.ImportPowderPattern2ThetaObsSigma(xye, 1)
        p0.SetWavelength(wl)
        pl = p0.FindPeaks(1.9, 0.01, 40, False)
        ex = quick_index(pl, verbose=False)
        sols = list(ex.GetSolutions())
        if not sols:
            L(stage="index", result="no solution")
            return
        def unpack(sol):
            if isinstance(sol, (tuple, list)):
                return sol[0], float(sol[1])
            return getattr(sol, "first", sol), float(getattr(sol, "second", 0.0))
        pairs = [unpack(sv) for sv in sols]
        pairs.sort(key=lambda t: -t[1])
        ruc, score = pairs[0]
        cell7 = list(ruc.DirectUnitCell())
        a, b, c = cell7[0], cell7[1], cell7[2]
        al, be, ga = (math.degrees(v) for v in cell7[3:6])
        centring = str(getattr(ruc, "centering", "P")).split(".")[-1].replace("LATTICE_", "")
        L(stage="index", score=score, cell=[a, b, c, al, be, ga], centring=centring, nsol=len(pairs))
        cr0 = Crystal(a, b, c, math.radians(al), math.radians(be), math.radians(ga), "P1")
        p0.SetMaxSinThetaOvLambda(0.3)
        d0 = p0.AddPowderPatternDiffraction(cr0)
        p0.quick_fit_profile(plot=False, verbose=False)
        spgex = SpaceGroupExplorer(d0)
        spgex.RunAll(False, False, True, False, True)
        res = list(spgex.GetScores())
        best_sg = res[0]
        sg = getattr(best_sg, "hermann_mauguin", None) or getattr(best_sg, "hm", None) or str(best_sg)
        L(stage="spacegroup", sg=sg, score_fields={k: str(getattr(best_sg, k))[:30] for k in dir(best_sg) if not k.startswith("_")})
        a, b, c, al, be, ga = cr0.a, cr0.b, cr0.c, math.degrees(cr0.alpha), math.degrees(cr0.beta), math.degrees(cr0.gamma)

    # -------- crystal with molecules
    cryst = Crystal(a, b, c, math.radians(al), math.radians(be), math.radians(ga), sg)
    cryst.SetName("cryst")
    cryst.SetUseDynPopCorr(1)
    ncomp = 0
    from pyobjcryst.atom import Atom
    from pyobjcryst.scatteringpower import ScatteringPowerAtom
    from pyobjcryst.molecule import Molecule
    spows = {}

    def spow(el):
        if el not in spows:
            sp = ScatteringPowerAtom(el, el)
            cryst.AddScatteringPower(sp)
            spows[el] = sp
        return spows[el]
    for ci, cpt in enumerate(comp["components"]):
        z, els = build_zmatrix(cpt["smiles"], seed=args.seed)
        zp = os.path.join(args.out, "comp%d.zmat" % ci)
        open(zp, "w").write(z)
        for k in range(int(cpt["count"])):
            if len(els) == 1:
                at = Atom(0.1 * k, 0.2, 0.3, "c%d_%d" % (ci, k), spow(els[0]))
                cryst.AddScatterer(at)
            elif len(els) == 2:
                m = Molecule(cryst, "c%d_%d" % (ci, k))
                m.AddAtom(0.0, 0.0, 0.0, spow(els[0]), els[0] + "1")
                m.AddAtom(1.4, 0.0, 0.0, spow(els[1]), els[1] + "2")
                m.AddBond(m.GetAtom(0), m.GetAtom(1), 1.4, 0.01, 0.02)
                cryst.AddScatterer(m)
            else:
                m = ImportFenskeHallZMatrix(cryst, zp, named=True)
                m.SetName("c%d_%d" % (ci, k))
            ncomp += 1
    L(stage="model", n_molecules=ncomp, n_par=cryst.GetNbParNotFixed())

    # -------- pattern
    pp = PowderPattern()
    pp.ImportPowderPattern2ThetaObsSigma(xye, 1)
    pp.SetWavelength(wl)
    pp.SetRadiationType(RadiationType.RAD_XRAY)
    pp.SetMaxSinThetaOvLambda(0.5 / args.dmin)
    diff = pp.AddPowderPatternDiffraction(cryst)
    diff.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 0.0000001)
    try:
        pp.quick_fit_profile(plot=False, verbose=False, cell=(args.mode == "routine"))
    except Exception as e:
        L(stage="profile", error=repr(e)[:200])
    diff.SetExtractionMode(False)
    pp.FixAllPar()
    for i in range(cryst.GetNbScatterer()):
        cryst.GetScatt(i).UnFixAllPar()
    L(stage="profile_done", rw=pp.GetRw(), chi2=pp.GetChi2())

    # -------- Monte Carlo (parallel tempering, FOX defaults)
    mc = MonteCarlo()
    mc.SetName("mc")
    mc.AddRefinableObj(cryst)
    mc.AddRefinableObj(pp)
    mc.SetAlgorithmParallTempering(AnnealingSchedule.SMART, 0.1, 0.01, AnnealingSchedule.SMART, 16, 0.125)
    best_cost = None
    solved_at = None
    deadline = T0 + args.max_minutes * 60
    for run in range(args.runs):
        mc.RandomizeStartingConfig() if hasattr(mc, "RandomizeStartingConfig") else None
        done = 0
        while done < args.steps and time.time() < deadline:
            mc.Optimize(args.chunk)
            done += args.chunk
            mc.RestoreBestConfiguration()
            cost = mc.GetLogLikelihood()
            cifp = os.path.join(args.out, "best_run%d.cif" % run)
            cryst.CIFOutput(cifp)
            # FOX writes dynamical-occupancy values; the oracle check grades the arrangement, so reset occupancies to 1
            import gemmi as _g
            _d = _g.cif.read(cifp)
            for _b in _d:
                _occ = _b.find_values("_atom_site_occupancy")
                for _i in range(len(_occ)):
                    _occ[_i] = "1"
            _d.write_file(cifp)
            # grade with the shipped grader (same code path as the trial): write the JSON cell alongside the CIF
            gdir = os.path.join(args.out, "grade_tmp")
            os.makedirs(gdir, exist_ok=True)
            for f in os.listdir(gdir):
                os.remove(os.path.join(gdir, f))
            import shutil
            shutil.copy(cifp, os.path.join(gdir, truth["id"] + ".cif"))
            json.dump(dict(cell=dict(a=a, b=b, c=c, alpha=al, beta=be, gamma=ga), space_group=sg), open(os.path.join(gdir, truth["id"] + ".json"), "w"))
            try:
                gr = GR.grade_instance(truth["id"], truth, gdir)
                S = bool(gr["S"])
                m = dict(rmsd=gr["S_detail"].get("rmsd"), dmax=gr["S_detail"].get("dmax"), reason=gr["S_detail"].get("reason"), L=gr["L"])
            except Exception as e:
                m, S = dict(reason=repr(e)[:120]), False
            L(stage="mc", run=run, trials=done, cost=cost, rw=pp.GetRw(), chi2=pp.GetChi2(), S=S, rmsd=m.get("rmsd"), dmax=m.get("dmax"), reason=m.get("reason"))
            if S and solved_at is None:
                solved_at = time.time() - T0
                L(stage="solved", run=run, trials=done, seconds=round(solved_at, 1))
            if best_cost is None or cost < best_cost:
                best_cost = cost
                cryst.CIFOutput(os.path.join(args.out, "best_overall.cif"))
        if time.time() >= deadline:
            L(stage="deadline", run=run)
            break
    summary = dict(mode=args.mode, solved_seconds=solved_at, best_cost=best_cost, runs=args.runs, steps=args.steps, minutes=round((time.time() - T0) / 60, 1),
                   cell=[a, b, c, al, be, ga], sg=sg)
    json.dump(summary, open(os.path.join(args.out, "summary.json"), "w"), indent=1)
    L(stage="end", **summary)


if __name__ == "__main__":
    main()
