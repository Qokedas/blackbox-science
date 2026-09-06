#!/usr/bin/env python3
"""Fixture battery for the grader: every variant from the spec applied to every instance, graded with the
shipped tests/grade.py against the shipped truth. Writes calibration_table.{json,md}.

Variants (legitimate, must pass the unit named): oracle (L+S), p1 (S only, L fails), shift_origin (S),
jitter0.2 (S), stretch0.5pct (L), nojson (L from CIF + S), mirror (S for achiral or non-Sohncke; fails for chiral in Sohncke).
Defective (must fail the unit named): jitter0.6 (S), randcoords (S; L passes), wrongmol (S), wrongsg (L), subcell (L),
stretch2pct (L), hedge (both 0), nocif (S), missing (both 0), other_polymorph (both), swapmol (S) for Z'>=2 where two
independent copies of the same component exist, ringflip (S): one terminal 6-ring rotated 60 deg about its attachment axis.
Also: the 2014 defective battery (original vs corrected experimental structures) in defective_2014().
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(TASK, "tests"))
sys.path.insert(0, HERE)


def load_truths():
    man = json.load(open(os.path.join(TASK, "tests", "manifest.json")))
    return {i: json.load(open(os.path.join(TASK, "tests", "truth", i + ".json"))) for i in man["ids"]}


def cell_json_from_truth(t, GR):
    s = GR.structure_from_cif(t["reference_cif"])
    a, b, c, al, be, ga = s.lattice.parameters
    return dict(cell=dict(a=a, b=b, c=c, alpha=al, beta=be, gamma=ga), space_group=t["space_group_symbol"])


def write_struct_cif(struct, path):
    from pymatgen.io.cif import CifWriter
    CifWriter(struct).write_file(path)


def ringflip(struct_full, GR):
    """Rotate one terminal six-membered ring (heavy atoms) by 60 deg about the bond joining it to the rest."""
    import networkx as nx
    from pymatgen.core import Structure
    heavy = GR.heavy_only(struct_full)
    comps = GR.molecule_graphs(heavy)
    for G in comps:
        try:
            cycles = nx.cycle_basis(G)
        except Exception:
            continue
        for cyc in cycles:
            if len(cyc) != 6:
                continue
            ext = [(u, v) for u in cyc for v in G[u] if v not in cyc]
            if len(ext) != 1:
                continue
            u, v = ext[0]  # ring atom u bonded to external atom v
            # rotate ring atoms (except u) by 60 deg about axis v->u passing through u ... use Cartesian with unwrapped positions
            # unwrap ring around u
            lat = heavy.lattice
            fu = heavy[u].frac_coords
            cart = {}
            for a in cyc + [v]:
                d = GR.pbc_diff(heavy[a].frac_coords, fu)
                cart[a] = lat.get_cartesian_coords(fu + d)
            axis = cart[u] - cart[v]
            axis /= np.linalg.norm(axis)
            th = np.radians(60)
            K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
            R = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K
            new = heavy.copy()
            for a in cyc:
                if a == u:
                    continue
                p = R @ (cart[a] - cart[u]) + cart[u]
                new.replace(a, heavy[a].specie, lat.get_fractional_coords(p) % 1.0)
            return new
    return None


def swapmol(struct_full, GR, truth):
    """For Z'>=2: swap the positions (centroids) of two independent copies of the largest component in the P1 cell.
    Both copies keep their orientation, so the arrangement is wrong but composition is intact."""
    heavy = GR.heavy_only(struct_full)
    comps = GR.molecule_graphs(heavy)
    sizes = sorted(set(len(c) for c in comps), reverse=True)
    big = [c for c in comps if len(c) == sizes[0]]
    if len(big) < 2:
        return None
    # centroids (unwrapped) of the first two
    lat = heavy.lattice

    def unwrap(G):
        nodes = list(G.nodes)
        f0 = heavy[nodes[0]].frac_coords
        pts = {}
        for n in nodes:
            pts[n] = f0 + GR.pbc_diff(heavy[n].frac_coords, f0)
        return pts
    A, B = unwrap(big[0]), unwrap(big[1])
    ca = np.mean(list(A.values()), axis=0)
    cb = np.mean(list(B.values()), axis=0)
    new = heavy.copy()
    for n, f in A.items():
        new.replace(n, heavy[n].specie, (f - ca + cb) % 1.0)
    for n, f in B.items():
        new.replace(n, heavy[n].specie, (f - cb + ca) % 1.0)
    return new


def make_variant(name, truth, GR, outdir, iid, other_truth=None):
    import variants
    cif = truth["reference_cif"]
    cj = cell_json_from_truth(truth, GR)
    os.makedirs(outdir, exist_ok=True)
    if name in ("oracle", "p1", "jitter0.2", "jitter0.6", "mirror", "randcoords", "hedge", "nocif", "nojson", "wrongsg", "subcell", "stretch2pct", "stretch0p5pct", "shift_origin", "wrongmol"):
        variants.make(name, cif, iid, outdir, cj)
        return True
    if name == "missing":
        return True
    if name == "other_polymorph":
        if other_truth is None:
            return False
        variants.make("oracle", other_truth["reference_cif"], iid, outdir, cell_json_from_truth(other_truth, GR))
        return True
    if name == "ringflip":
        s = ringflip(GR.structure_from_cif(cif), GR)
        if s is None:
            return False
        write_struct_cif(s, os.path.join(outdir, iid + ".cif"))
        json.dump(cj, open(os.path.join(outdir, iid + ".json"), "w"))
        return True
    if name == "swapmol":
        s = swapmol(GR.structure_from_cif(cif), GR, truth)
        if s is None:
            return False
        write_struct_cif(s, os.path.join(outdir, iid + ".cif"))
        json.dump(cj, open(os.path.join(outdir, iid + ".json"), "w"))
        return True
    raise ValueError(name)


def grade(subdir, outdir):
    subprocess.run([sys.executable, os.path.join(TASK, "tests", "grade.py"), "--reference-root", os.path.join(TASK, "tests"), "--submission-dir", subdir, "--out", outdir],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p = os.path.join(outdir, "score_breakdown.json")
    return json.load(open(p)) if os.path.exists(p) else None


# same-compound different-phase pairs in the panel (by source): psilocybin A/B, carvedilol phosphate hemihydrate/isopropanol
POLYMORPH_PAIRS = [("PMC8725723:Form_A", "PMC8725723:Form_B"), ("PMC2977435:I", "PMC2983528:I")]


def main(out_root):
    import grade as GR
    GR.load_deps()
    truths = load_truths()
    key = json.load(open(os.path.join(TASK, "..", "..", "pxrd-work", "keys", "manifest_SECRET.json"))) if os.path.exists(os.path.join(TASK, "..", "..", "pxrd-work", "keys", "manifest_SECRET.json")) else {}
    src2id = {v["source"] + ":" + str(v["block"]): k for k, v in key.items()}
    os.makedirs(out_root, exist_ok=True)
    names = ["oracle", "p1", "shift_origin", "jitter0.2", "stretch0p5pct", "nojson", "mirror", "jitter0.6", "randcoords", "wrongmol", "ringflip", "swapmol",
             "wrongsg", "subcell", "stretch2pct", "hedge", "nocif", "missing", "other_polymorph"]
    table = {}
    for name in names:
        subdir = os.path.join(out_root, "sub_" + name)
        shutil.rmtree(subdir, ignore_errors=True)
        os.makedirs(subdir)
        applicable = []
        for iid, t in truths.items():
            other = None
            if name == "other_polymorph":
                for a, b in POLYMORPH_PAIRS:
                    if src2id.get(a) == iid and src2id.get(b):
                        other = truths[src2id[b]]
                    if src2id.get(b) == iid and src2id.get(a):
                        other = truths[src2id[a]]
                if other is None:
                    continue
            try:
                ok = make_variant(name, t, GR, subdir, iid, other)
            except Exception as e:
                print("variant failed", name, iid, repr(e)[:100])
                ok = False
            if ok:
                applicable.append(iid)
        res = grade(subdir, os.path.join(out_root, "out_" + name))
        rows = {r["id"]: r for r in res["instances"]} if res else {}
        L = sum(int(rows[i]["L"]) for i in applicable if i in rows)
        S = sum(int(rows[i]["S"]) for i in applicable if i in rows)
        table[name] = dict(n=len(applicable), L=L, S=S, score=res["score"] if res else None,
                           detail={i: dict(L=rows[i]["L"], S=rows[i]["S"], rmsd=rows[i]["S_detail"].get("rmsd"), dmax=rows[i]["S_detail"].get("dmax"), reason=rows[i]["S_detail"].get("reason")) for i in applicable if i in rows})
        print("%-16s n=%2d  L=%2d  S=%2d  score=%s" % (name, len(applicable), L, S, table[name]["score"]), flush=True)
    json.dump(table, open(os.path.join(out_root, "calibration_table.json"), "w"), indent=1)
    with open(os.path.join(out_root, "calibration_table.md"), "w") as f:
        f.write("| variant | instances | L passes | S passes | score |\n|---|---|---|---|---|\n")
        for name, r in table.items():
            f.write("| %s | %d | %d | %d | %s |\n" % (name, r["n"], r["L"], r["S"], r["score"]))
    return table


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "battery_out"))
