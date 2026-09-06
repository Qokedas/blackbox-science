import sys, warnings; warnings.filterwarnings('ignore')
import numpy as np
from pymatgen.io.cif import CifParser
from pymatgen.core import Structure
for f in sys.argv[1:]:
    s0 = CifParser(f).parse_structures(primitive=False)[0]
    # asymmetric unit only: read raw
    d = CifParser(f).as_dict(); blk = list(d.values())[0]
    lab = blk['_atom_site_label']; el = blk['_atom_site_type_symbol']
    x = np.array([[float(v) for v in blk[k]] for k in ('_atom_site_fract_x', '_atom_site_fract_y', '_atom_site_fract_z')]).T
    heavy = [i for i, e in enumerate(el) if e != 'H']
    x = x[heavy]; lab = [lab[i] for i in heavy]
    lat = s0.lattice
    cart = lat.get_cartesian_coords(x)
    cen = cart.mean(axis=0)
    print(f)
    print('  centroid frac:', np.round(lat.get_fractional_coords(cen), 3))
    # principal axes
    c = cart - cen
    w, v = np.linalg.eigh(c.T @ c)
    print('  principal axes (cart, columns long->short):', np.round(v[:, ::-1].T, 3), 'eig', np.round(w[::-1], 1))
    # pointers: vector from ring centroid (C7..C14 phenyl) to carbonyl O, methyl C1
    idx = {l: i for i, l in enumerate(lab)}
    print('  O1-C1 vector (cart):', np.round(cart[idx['O1']] - cart[idx['C1']], 2), ' N5-N6:', np.round(cart[idx['N5']] - cart[idx['N6']], 2))
    print('  C1 frac', np.round(x[idx['C1']], 3), 'O1 frac', np.round(x[idx['O1']], 3), 'N5', np.round(x[idx['N5']], 3), 'N6', np.round(x[idx['N6']], 3))
