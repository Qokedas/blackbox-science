import sys, os, json, time, argparse, numpy as np
sys.path.insert(0, '/app/work')
import warnings; warnings.filterwarnings('ignore')
from rdkit import Chem
from rdkit.Chem import AllChem
import pyobjcryst
from pyobjcryst.crystal import Crystal
from pyobjcryst.molecule import Molecule
from pyobjcryst.atom import Atom
from pyobjcryst.scatteringpower import ScatteringPowerAtom
from pyobjcryst.globaloptim import MonteCarlo, AnnealingSchedule
from pyobjcryst.powderpattern import ReflectionProfileType
from lebail import make_pattern, add_crystal, fit_sequence
from pyobjcryst.lsq import LSQ

def embed(smiles, seed=42, nconf=30):
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    ps = AllChem.ETKDGv3(); ps.randomSeed = seed
    cids = AllChem.EmbedMultipleConfs(mol, nconf, ps)
    if len(cids) == 0:
        ps.useRandomCoords = True
        cids = AllChem.EmbedMultipleConfs(mol, nconf, ps)
    res = AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=2000)
    energies = [e for (c, e) in res]
    order = list(np.argsort(energies))
    # distinct conformers (heavy-atom RMSD > 0.25 A), sorted by energy
    heavy = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() > 1]
    from rdkit.Chem import rdMolAlign
    distinct = []
    for cid in order:
        cid = int(cid)
        if all(rdMolAlign.GetBestRMS(Chem.RemoveHs(mol), Chem.RemoveHs(mol), c2, cid) > 0.25 for c2 in distinct):
            distinct.append(cid)
    k = min(CONF_RANK, len(distinct) - 1)
    best = distinct[k]
    print(f'  conformers: {len(distinct)} distinct; energies {[round(energies[c],1) for c in distinct[:6]]}; using rank {k} (E={energies[best]:.1f})', flush=True)
    return mol, best, energies
CONF_RANK = 0

def classify_bonds(mol):
    """Return set of bond indices whose torsion should be restrained (kept as in conformer).
    Fixed: ring bonds, multiple bonds, terminal bonds, amide/ester/thioester C(=O)-X (X=N,O,S) and
    conjugated C(=O)-C=C / N-N=C hydrazone / C=C-C=C (planar). Everything else (biaryl, aryl-N, aryl-O, sp3) is free."""
    fixed = set()
    dbl_nb = lambda y: any(mol.GetBondBetweenAtoms(y.GetIdx(), nb.GetIdx()).GetBondType() == Chem.BondType.DOUBLE for nb in y.GetNeighbors())
    is_carbonyl = lambda y: y.GetAtomicNum() == 6 and any(nb.GetAtomicNum() in (8, 16) and mol.GetBondBetweenAtoms(y.GetIdx(), nb.GetIdx()).GetBondType() == Chem.BondType.DOUBLE for nb in y.GetNeighbors())
    for b in mol.GetBonds():
        a1, a2 = b.GetBeginAtom(), b.GetEndAtom()
        if a1.GetAtomicNum() == 1 or a2.GetAtomicNum() == 1:
            continue
        if b.IsInRing():
            fixed.add(b.GetIdx()); continue
        if b.GetBondType() != Chem.BondType.SINGLE:
            fixed.add(b.GetIdx()); continue
        hd1 = sum(1 for n in a1.GetNeighbors() if n.GetAtomicNum() > 1)
        hd2 = sum(1 for n in a2.GetNeighbors() if n.GetAtomicNum() > 1)
        if hd1 < 2 or hd2 < 2:
            fixed.add(b.GetIdx()); continue  # terminal: no torsion needed
        if a1.GetHybridization() == Chem.HybridizationType.SP or a2.GetHybridization() == Chem.HybridizationType.SP:
            fixed.add(b.GetIdx()); continue  # linear: rotation meaningless
        for x, y in ((a1, a2), (a2, a1)):
            # amide / ester / thioester / carbamate: X-C(=O) with X = N, O, S  (planar)
            if x.GetAtomicNum() in (7, 8, 16) and is_carbonyl(y):
                fixed.add(b.GetIdx())
            # acyclic conjugated: C(=O)-C=C (enone), C=C-C=C (diene), N-N=C hydrazone/azine: both atoms carry a double bond and are not aromatic
            elif (not x.GetIsAromatic()) and (not y.GetIsAromatic()) and dbl_nb(x) and dbl_nb(y) and x.GetAtomicNum() == 6 and y.GetAtomicNum() == 6:
                fixed.add(b.GetIdx())
            elif x.GetAtomicNum() == 7 and y.GetAtomicNum() == 7 and (dbl_nb(x) or dbl_nb(y)):
                fixed.add(b.GetIdx())  # hydrazone N-N
    return fixed

def add_molecule(cr, mol, confid, name, sps, allH=False):
    m = Molecule(cr, name)
    conf = mol.GetConformer(confid)
    heavy = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() > 1 or allH]
    pos = np.array([list(conf.GetAtomPosition(i)) for i in heavy])
    pos -= pos.mean(axis=0)
    idxmap = {}
    counts = {}
    for k, i in enumerate(heavy):
        a = mol.GetAtomWithIdx(i)
        sym = a.GetSymbol()
        counts[sym] = counts.get(sym, 0) + 1
        if sym not in sps:
            sp = ScatteringPowerAtom(sym, sym)
            cr.AddScatteringPower(sp)
            sps[sym] = sp
        at = m.AddAtom(pos[k,0], pos[k,1], pos[k,2], sps[sym], f'{sym}{counts[sym]}')
        idxmap[i] = m.GetNbAtoms() - 1
    getat = lambda i: m.GetAtom(idxmap[i])
    fixed = classify_bonds(mol)
    # bonds
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in idxmap and j in idxmap:
            d = np.linalg.norm(pos[heavy.index(i)] - pos[heavy.index(j)])
            m.AddBond(getat(i), getat(j), d, 0.01, 0.02)
    # angles
    from rdkit.Chem import rdMolTransforms as T
    for a in mol.GetAtoms():
        if a.GetIdx() not in idxmap: continue
        nbs = [n.GetIdx() for n in a.GetNeighbors() if n.GetIdx() in idxmap]
        for x in range(len(nbs)):
            for y in range(x+1, len(nbs)):
                ang = T.GetAngleRad(conf, nbs[x], a.GetIdx(), nbs[y])
                m.AddBondAngle(getat(nbs[x]), getat(a.GetIdx()), getat(nbs[y]), ang, 0.01, 0.02)
    # dihedrals for fixed bonds
    ndih = 0; nfree = 0
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i not in idxmap or j not in idxmap: continue
        ni = [n.GetIdx() for n in mol.GetAtomWithIdx(i).GetNeighbors() if n.GetIdx() in idxmap and n.GetIdx() != j]
        nj = [n.GetIdx() for n in mol.GetAtomWithIdx(j).GetNeighbors() if n.GetIdx() in idxmap and n.GetIdx() != i]
        if not ni or not nj: continue
        if b.GetIdx() in fixed:
            # restrain all dihedrals around this bond (one is enough with angles, but add all for robustness)
            for p in ni:
                for q in nj:
                    ang = T.GetDihedralRad(conf, p, i, j, q)
                    m.AddDihedralAngle(getat(p), getat(i), getat(j), getat(q), ang, 0.02, 0.05)
                    ndih += 1
        else:
            nfree += 1
    cr.AddScatterer(m)
    print(f'  molecule {name}: {len(heavy)} atoms, {m.GetNbBonds()} bonds, {m.GetNbBondAngles()} angles, {ndih} dihedral restraints, {nfree} free torsions', flush=True)
    return m

def setup(iid, cell, spg, ttmax=None, components=None, verbose=True, nbg=24, lebail_first=True, asym=False):
    comp = json.load(open(f'/app/data/instances/{iid}/composition.json'))
    p, ins = make_pattern(iid, tt_max=ttmax, nbg=nbg)
    cr, pd = add_crystal(p, cell, spg)
    pd.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 1e-7)
    steps = [['Zero'], ['W'], ['a', 'b', 'c', 'alpha', 'beta', 'gamma'], ['U', 'V'], ['Eta0'], ['Eta1'], ['background']]
    if asym: steps.append(['Asym0', 'Asym1'])
    steps.append(['Zero', 'W', 'U', 'V', 'Eta0', 'background', 'a', 'b', 'c', 'alpha', 'beta', 'gamma'])
    lsq = fit_sequence(p, pd, steps, verbose=verbose)
    print(f'LeBail Rwp={p.GetRw():.4f} chi2={p.GetChi2():.1f} cell=', cr.a, cr.b, cr.c, np.degrees(cr.beta), flush=True)
    pd.SetExtractionMode(False)
    sps = {}
    mols = []
    comps = comp['components'] if components is None else components
    for ci, c in enumerate(comps):
        smi = c['smiles']
        n = c['count']
        molr = Chem.MolFromSmiles(smi)
        nheavy = molr.GetNumHeavyAtoms()
        for k in range(n):
            if nheavy == 1:
                sym = molr.GetAtomWithIdx(0).GetSymbol()
                if sym not in sps:
                    sp = ScatteringPowerAtom(sym, sym); cr.AddScatteringPower(sp); sps[sym] = sp
                at = Atom(np.random.rand(), np.random.rand(), np.random.rand(), f'{sym}_{ci}_{k}', sps[sym])
                cr.AddScatterer(at)
                mols.append(at)
                print(f'  single atom {sym}', flush=True)
            else:
                mol, best, en = embed(smi, seed=42+k)
                m = add_molecule(cr, mol, best, f'mol{ci}_{k}', sps)
                m._crystal = cr
                mols.append(m)
    cr.SetUseDynPopCorr(1)
    return p, cr, pd, mols, lsq

def polish(p, cr, ncycle=20, verbose=True):
    """restrained LSQ (Rietveld-like) refinement of molecule position/orientation/geometry + profile + background"""
    rw0 = p.GetRw()
    # disable 'Auto Optimize Starting Conformation' (it re-randomises free torsions on BeginOptimization)
    for i in range(cr.GetNbScatterer()):
        sc = cr.GetScatt(i)
        if hasattr(sc, 'GetNbOption'):
            for k in range(sc.GetNbOption()):
                o = sc.GetOption(k)
                if 'Auto Optimize' in o.GetName(): o.SetChoice(1)
    lsq = LSQ()
    lsq.SetRefinedObj(p, 0, True, True)
    lsq.PrepareRefParList(True)
    lsqr = lsq.GetCompiledRefinedObj()
    lsqr.UnFixAllPar()
    # fix Biso, occupancies, and anything exotic
    import re
    atomcoord = re.compile(r'^[A-Z][a-z]?\d+_[xyz]$')
    for i in range(lsqr.GetNbPar()):
        par = lsqr.GetPar(i)
        n = par.GetName()
        if (n.startswith('Biso') or 'ccup' in n or n.startswith('Asym') or n in ('Eta1', 'Zero', 'a', 'b', 'c', 'alpha', 'beta', 'gamma') or n.startswith('ML')
                or atomcoord.match(n) or n.startswith('Global') or n.startswith('B1') or n.startswith('B2') or n.startswith('B3') or n.startswith('Formal')):
            par.SetIsFixed(True)
    sid = lsqr.CreateParamSet('prepolish')
    lsqr.SaveParamSet(sid)
    ok = False
    try:
        lsq.Refine(ncycle, True, True, False)
        rw1 = p.GetRw()
        if np.isfinite(rw1) and rw1 < rw0:
            ok = True
        else:
            lsqr.RestoreParamSet(sid)
    except Exception as e:
        if verbose: print('polish failed', e, flush=True)
        lsqr.RestoreParamSet(sid)
    if verbose: print(f'polish: Rwp {rw0:.4f} -> {p.GetRw():.4f} ({"accepted" if ok else "rejected"}) restraint cost={cr.GetRestraintCost():.2f}', flush=True)
    return ok

def optimize(p, cr, nsteps=1e6, nruns=1, seed=None, maxtime=-1, save_prefix=None, do_polish=True, norand=False):
    mc = MonteCarlo()
    mc.AddRefinableObj(cr)
    mc.AddRefinableObj(p)
    mc.SetAlgorithmParallTempering(AnnealingSchedule.SMART, 0.1, 0.01, AnnealingSchedule.EXPONENTIAL, 16, 0.125) if False else None
    results = []
    for r in range(nruns):
        t0 = time.time()
        if not (norand and r == 0): mc.RandomizeStartingConfig()
        mc.Optimize(int(nsteps), 0, maxtime)
        cost = mc.GetLogLikelihood()
        rw = p.GetRw()
        chi2 = p.GetChi2()
        print(f'run {r}: cost={cost:.1f} Rwp={rw:.4f} chi2={chi2:.1f} t={time.time()-t0:.0f}s', flush=True)
        if save_prefix:
            write_cif(cr, f'{save_prefix}_run{r}_rw{rw:.3f}.cif')
        if do_polish:
            try:
                sid = cr.CreateParamSet('mc_best'); cr.SaveParamSet(sid)
                ok = polish(p, cr)
                if ok and save_prefix:
                    write_cif(cr, f'{save_prefix}_run{r}_lsq_rw{p.GetRw():.3f}.cif')
                cr.RestoreParamSet(sid)  # continue next run from MC state (randomized anyway)
            except Exception as e:
                print('polish error', e, flush=True)
        results.append((cost, rw, chi2))
    return mc, results

def restore_from_cif(cr, mols, ciffile):
    """Place molecules/atoms at positions read from an ObjCryst-written CIF with the same atom naming/order."""
    import gemmi
    doc = gemmi.cif.read(ciffile); blk = doc.sole_block()
    names = list(blk.find_values('_atom_site_label'))
    fx = [float(v) for v in blk.find_values('_atom_site_fract_x')]
    fy = [float(v) for v in blk.find_values('_atom_site_fract_y')]
    fz = [float(v) for v in blk.find_values('_atom_site_fract_z')]
    seq = [(n, np.array([x, y, z])) for n, x, y, z in zip(names, fx, fy, fz)]
    k = 0  # sequential consumption (labels may collide between molecules)
    for m in mols:
        if hasattr(m, 'GetNbAtoms'):
            nat = m.GetNbAtoms()
            fr = []
            for i in range(nat):
                nm = m.GetAtom(i).GetName()
                if seq[k][0] != nm:
                    print('restore: name mismatch', seq[k][0], nm, flush=True)
                fr.append(seq[k][1]); k += 1
            fr = np.array(fr)
            # unwrap: make molecule contiguous around first atom
            fr = fr - np.round(fr - fr[0])
            cen = fr.mean(axis=0)
            cart = np.array([cr.FractionalToOrthonormalCoords(*(f - cen)) for f in fr])
            for i in range(nat):
                a = m.GetAtom(i); a.SetX(cart[i, 0]); a.SetY(cart[i, 1]); a.SetZ(cart[i, 2])
            m.X, m.Y, m.Z = cen
            m.Q0, m.Q1, m.Q2, m.Q3 = 1.0, 0.0, 0.0, 0.0
        else:
            f = seq[k][1]; k += 1
            m.X, m.Y, m.Z = f
    cr.UpdateDisplay() if hasattr(cr, 'UpdateDisplay') else None

def write_cif(cr, fn):
    cr.CIFOutput(fn)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('iid'); ap.add_argument('cell', nargs=6, type=float); ap.add_argument('spg')
    ap.add_argument('--nsteps', type=float, default=2e6); ap.add_argument('--nruns', type=int, default=1)
    ap.add_argument('--ttmax', type=float, default=None); ap.add_argument('--tag', default='a')
    ap.add_argument('--maxtime', type=float, default=-1)
    ap.add_argument('--restore', default=None, help='CIF from a previous run: restore and polish only')
    ap.add_argument('--restore-sa', default=None, help='CIF from a previous run: restore, then SA without initial randomization (run 0), then polish')
    ap.add_argument('--zprime', type=int, default=1)
    ap.add_argument('--conf', type=int, default=0, help='rank of distinct conformer to use (0 = lowest MMFF energy)')
    a = ap.parse_args()
    seed = int(time.time()*1000) % 2**31
    np.random.seed(seed)
    import ctypes; ctypes.CDLL(None).srand(seed)  # ObjCryst uses libc rand()
    print('seed', seed, flush=True)
    CONF_RANK = a.conf
    globals()['CONF_RANK'] = a.conf
    comps = None
    if a.zprime > 1:
        comps = [dict(c, count=c['count']*a.zprime) for c in json.load(open(f'/app/data/instances/{a.iid}/composition.json'))['components']]
    p, cr, pd, mols, lsq = setup(a.iid, a.cell, a.spg, ttmax=a.ttmax, components=comps)
    outdir = f'/app/work/{a.iid}/sol_{a.tag}'
    os.makedirs(outdir, exist_ok=True)
    if a.restore:
        restore_from_cif(cr, mols, a.restore)
        p.FitScaleFactorForRw()
        print(f'restored from {a.restore}: Rwp={p.GetRw():.4f} restraint cost={cr.GetRestraintCost():.2f}', flush=True)
        write_cif(cr, f'{outdir}/restored_check.cif')
        ok = polish(p, cr, ncycle=30)
        write_cif(cr, f'{outdir}/restored_lsq_rw{p.GetRw():.3f}.cif')
        print('RESTORE-POLISH', a.iid, p.GetRw(), flush=True)
        os._exit(0)
    norand = False
    if a.restore_sa:
        restore_from_cif(cr, mols, a.restore_sa)
        p.FitScaleFactorForRw()
        print(f'restored from {a.restore_sa}: Rwp={p.GetRw():.4f} restraint cost={cr.GetRestraintCost():.2f}', flush=True)
        for i in range(cr.GetNbScatterer()):
            sc = cr.GetScatt(i)
            if hasattr(sc, 'GetNbOption'):
                for k in range(sc.GetNbOption()):
                    o = sc.GetOption(k)
                    if 'Auto Optimize' in o.GetName(): o.SetChoice(1)
        norand = True
    mc, res = optimize(p, cr, nsteps=a.nsteps, nruns=a.nruns, maxtime=a.maxtime, save_prefix=f'{outdir}/{a.spg.replace(" ","").replace("/","_")}', norand=norand)
    print('RESULTS', a.iid, a.spg, res, flush=True)
    os._exit(0)
