import sys, warnings; warnings.filterwarnings('ignore')
from pymatgen.io.cif import CifParser
from pymatgen.core import Lattice
from pymatgen.symmetry.groups import SpaceGroup
import numpy as np, itertools
f = sys.argv[1]; dmax = float(sys.argv[2]) if len(sys.argv) > 2 else 3.5
d = CifParser(f).as_dict(); blk = list(d.values())[0]
labs = blk['_atom_site_label']; els = blk['_atom_site_type_symbol']
x = np.array([[float(v) for v in blk[k]] for k in ('_atom_site_fract_x', '_atom_site_fract_y', '_atom_site_fract_z')]).T
keep = [i for i, e in enumerate(els) if e != 'H']
labs = [labs[i] for i in keep]; x = x[keep]
lat = Lattice.from_parameters(*[float(blk[k]) for k in ('_cell_length_a', '_cell_length_b', '_cell_length_c', '_cell_angle_alpha', '_cell_angle_beta', '_cell_angle_gamma')])
sgsym = blk.get('_symmetry_space_group_name_H-M') or blk.get('_space_group_name_H-M_alt')
sg = SpaceGroup(sgsym.replace(' ', '') if 'P-1' in sgsym.replace(' ', '') else sgsym)
ops = sg.symmetry_ops
cart0 = lat.get_cartesian_coords(x)
rows = []
for k, op in enumerate(ops):
    xo = op.operate_multi(x)
    for t in itertools.product([-2, -1, 0, 1, 2], repeat=3):
        if np.allclose(op.rotation_matrix, np.eye(3)) and np.allclose(np.mod(op.translation_vector, 1), 0) and t == (0, 0, 0): continue
        c = lat.get_cartesian_coords(xo + np.array(t))
        dd = np.linalg.norm(cart0[:, None, :] - c[None, :, :], axis=2)
        ii, jj = np.where(dd < dmax)
        for i, j in zip(ii, jj):
            rows.append((dd[i, j], labs[i], labs[j], k, t))
rows.sort(key=lambda r: r[0])
seen = set()
for r in rows:
    key = (r[1], r[2], round(r[0], 2))
    if key in seen: continue
    seen.add(key)
    print('%.2f  %-4s %-4s op%d %s' % r)
