import sys, numpy as np, gemmi
def read(f):
    d = gemmi.cif.read(f).sole_block()
    lab = list(d.find_values('_atom_site_label'))
    xyz = np.array([[float(v) for v in d.find_values(k)] for k in ('_atom_site_fract_x','_atom_site_fract_y','_atom_site_fract_z')]).T
    cell = [float(d.find_value(k)) for k in ('_cell_length_a','_cell_length_b','_cell_length_c','_cell_angle_alpha','_cell_angle_beta','_cell_angle_gamma')]
    return lab, xyz, gemmi.UnitCell(*cell)
l1, x1, c1 = read(sys.argv[1]); l2, x2, c2 = read(sys.argv[2])
m = {l: i for i, l in enumerate(l2)}
ds = []
for i, l in enumerate(l1):
    if l not in m or l.startswith('H'): continue
    j = m[l]
    df = x2[j] - x1[i]; df -= np.round(df)
    p = c1.orthogonalize(gemmi.Fractional(*df))
    ds.append(np.sqrt(p.x**2+p.y**2+p.z**2))
ds = np.array(ds)
print(f'n={len(ds)} rms={np.sqrt((ds**2).mean()):.3f} max={ds.max():.3f} (same-label, minimal image, no symmetry)')
