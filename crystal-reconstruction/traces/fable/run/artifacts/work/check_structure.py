import sys, json, numpy as np, networkx as nx
from pymatgen.io.cif import CifParser
from pymatgen.core import Structure
from rdkit import Chem

COV = {'H':0.31,'C':0.76,'N':0.71,'O':0.66,'F':0.57,'P':1.07,'S':1.05,'Cl':1.02,'Br':1.20,'I':1.39,'B':0.84,'Si':1.11,'Na':1.66,'K':2.03}

def perceive(struct, tol=0.45):
    s = struct
    n = len(s)
    G = nx.Graph()
    for i, site in enumerate(s):
        G.add_node(i, el=site.specie.symbol)
    # neighbor search
    allnb = s.get_all_neighbors(3.2)
    for i in range(n):
        for nb in allnb[i]:
            j = nb.index
            if j < i: continue
            ri = COV.get(s[i].specie.symbol, 1.0); rj = COV.get(s[j].specie.symbol, 1.0)
            if nb.nn_distance < ri + rj + tol:
                # note: periodic images -> the same pair may be bonded via different images; we only record the pair
                G.add_edge(i, j, d=nb.nn_distance)
    return G

def smiles_graphs(comp):
    out = []
    for c in comp['components']:
        m = Chem.MolFromSmiles(c['smiles'])
        G = nx.Graph()
        for a in m.GetAtoms():
            G.add_node(a.GetIdx(), el=a.GetSymbol())
        for b in m.GetBonds():
            G.add_edge(b.GetBeginAtomIdx(), b.GetEndAtomIdx())
        out.append((G, c['count']))
    return out

def check(cif, iid, verbose=True):
    comp = json.load(open(f'/app/data/instances/{iid}/composition.json'))
    s = CifParser(cif).parse_structures(primitive=False)[0]
    s.remove_species(['H', 'D']) if any(sp.symbol in ('H','D') for sp in s.composition.elements) else None
    G = perceive(s)
    comps = [G.subgraph(c).copy() for c in nx.connected_components(G)]
    refs = smiles_graphs(comp)
    nm = nx.algorithms.isomorphism.categorical_node_match('el', '')
    counts = [0]*len(refs)
    bad = []
    for cg in comps:
        matched = False
        for k, (rg, cnt) in enumerate(refs):
            if cg.number_of_nodes() == rg.number_of_nodes() and nx.is_isomorphic(cg, rg, node_match=nm):
                counts[k] += 1; matched = True; break
        if not matched:
            bad.append(cg)
    ok = not bad and all(counts[k] > 0 for k in range(len(refs)))
    ratios = [counts[k]/refs[k][1] for k in range(len(refs))]
    ok = ok and all(abs(r - ratios[0]) < 1e-6 for r in ratios)
    if verbose:
        print(f'{iid}: {len(s)} atoms in cell; fragments={len(comps)}; matched counts={counts} (expected ratio {[r[1] for r in refs]}); unmatched={len(bad)}; OK={ok}')
        for cg in bad[:5]:
            els = sorted([d['el'] for _, d in cg.nodes(data=True)])
            print('   unmatched fragment:', len(cg), 'atoms', ''.join(els)[:80], 'edges', cg.number_of_edges())
        # short contacts
        dm = s.distance_matrix
        np.fill_diagonal(dm, 10)
        mn = dm.min()
        print(f'   min interatomic distance in cell: {mn:.2f} A')
    return ok

if __name__ == '__main__':
    check(sys.argv[1], sys.argv[2])
