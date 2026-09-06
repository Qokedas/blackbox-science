"""Isolated-molecule shape comparison between a submitted CIF and the reference, for one instance.

This is a display diagnostic, not the grader. It unwraps one molecule from each structure across periodic boundaries,
matches atoms by element and connectivity (all graph isomorphisms), rigidly superimposes them (proper rotation only),
and reports per-atom distances for the best mapping. No coordinates are refined or altered.

Usage: python molecule_shape_compare.py <instance id> <submitted.cif> [out.json]
Requires gemmi, rdkit, networkx, numpy (all in the solver image).
"""
import sys, json, itertools
from pathlib import Path
import numpy as np, networkx as nx, gemmi
from rdkit import Chem

HERE = Path(__file__).resolve().parent
TRUTH = HERE.parent.parent / 'tests' / 'truth'

def heavy_graph_from_cif(text, n_expected):
    st = gemmi.make_small_structure_from_block(gemmi.cif.read_string(text).sole_block())
    sites = [a for a in st.sites if a.element.name not in ('H', 'D')]
    assert len(sites) == n_expected, (len(sites), n_expected)
    els = [a.element.name for a in sites]
    frac = np.array([[a.fract.x, a.fract.y, a.fract.z] for a in sites])
    cell = st.cell
    def cart(f):  # fractional -> Cartesian
        p = cell.orthogonalize(gemmi.Fractional(*f)); return np.array([p.x, p.y, p.z])
    pt = Chem.GetPeriodicTable(); rad = np.array([pt.GetRcovalent(e) for e in els])
    delta = frac[None, :, :] - frac[:, None, :]; images = -np.rint(delta)
    d = np.array([[np.linalg.norm(cart(delta[i, j] + images[i, j])) for j in range(len(els))] for i in range(len(els))])
    for slack in (.45, .35, .55, .25, .65):
        g = nx.Graph(); g.add_nodes_from((i, {'el': e}) for i, e in enumerate(els))
        for i in range(len(els)):
            for j in range(i + 1, len(els)):
                if .5 < d[i, j] <= rad[i] + rad[j] + slack: g.add_edge(i, j)
        if nx.is_connected(g) and g.number_of_edges() >= len(els) - 1: break
    offset = {0: np.zeros(3)}
    for u, v in nx.bfs_edges(g, 0): offset[v] = offset[u] + images[u, v]
    xyz = np.array([cart(frac[i] + offset[i]) for i in range(len(els))])
    labels = [a.label for a in sites]
    return dict(els=els, xyz=xyz, graph=g, labels=labels, cell=[cell.a, cell.b, cell.c, cell.alpha, cell.beta, cell.gamma])

def kabsch(moving, fixed):
    x0, y0 = moving.mean(0), fixed.mean(0)
    u, s, vt = np.linalg.svd((moving - x0).T @ (fixed - y0))
    r = u @ np.diag([1, 1, np.sign(np.linalg.det(u @ vt))]) @ vt
    return (moving - x0) @ r + y0

def main(iid, sub_cif, out=None):
    truth = json.load(open(TRUTH / f'{iid}.json'))
    n = int(float(truth['n_heavy_asym']))
    ref = heavy_graph_from_cif(truth['reference_cif'], n)
    sub = heavy_graph_from_cif(Path(sub_cif).read_text(), n)
    gm = nx.algorithms.isomorphism.GraphMatcher(sub['graph'], ref['graph'], node_match=lambda a, b: a['el'] == b['el'])
    best = None
    for k, m in enumerate(gm.isomorphisms_iter()):
        order = [m[i] for i in range(n)]
        fitted = kabsch(sub['xyz'], ref['xyz'][order])
        dist = np.linalg.norm(fitted - ref['xyz'][order], axis=1)
        rmsd = float(np.sqrt((dist ** 2).mean()))
        if best is None or rmsd < best['rmsd']:
            best = dict(rmsd=rmsd, dmax=float(dist.max()), n_over_1A=int((dist > 1).sum()), n_atoms=n,
                        per_atom=[dict(sub=sub['labels'][i], ref=ref['labels'][order[i]], el=sub['els'][i], dist_A=round(float(dist[i]), 3)) for i in range(n)])
        if k > 500: break
    best.update(id=iid, name=truth.get('candidate_name'), maps_examined=k + 1, submitted_cif=str(sub_cif), reference_cell=ref['cell'], submitted_cell=sub['cell'],
                method='connectivity-matched rigid superposition of one unwrapped molecule; proper rotations only; hydrogens omitted; not the grader metric')
    txt = json.dumps(best, indent=1)
    if out: Path(out).write_text(txt + '\n')
    print(f"{iid} {best['name']}: molecular RMSD {best['rmsd']:.2f} A, worst atom {best['dmax']:.2f} A, {best['n_over_1A']}/{n} atoms > 1 A, {best['maps_examined']} mappings")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
