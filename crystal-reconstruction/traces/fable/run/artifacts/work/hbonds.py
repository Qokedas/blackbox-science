import sys, warnings; warnings.filterwarnings('ignore')
from pymatgen.io.cif import CifParser
from pymatgen.core import Structure
import numpy as np
s0 = CifParser(sys.argv[1]).parse_structures(primitive=False)[0]
s = Structure(s0.lattice, [site.species.elements[0].symbol for site in s0], s0.frac_coords)
s.remove_species(['H'])
dmax = float(sys.argv[2]) if len(sys.argv) > 2 else 3.4
n = len(s)
polar = [i for i, sp in enumerate(s) if sp.specie.symbol in ('N', 'O')]
seen = set()
for i in polar:
    for nb in s.get_neighbors(s[i], dmax):
        j = nb.index
        if s[j].specie.symbol not in ('N', 'O'): continue
        d = nb.nn_distance
        if d < 1.6: continue
        key = tuple(sorted((i, j))) + (round(d, 2),)
        if key in seen: continue
        seen.add(key)
        # intramolecular check: same asymmetric-unit molecule and image (0,0,0) and both in same molecule -> skip if graph distance small: approximate by cartesian distance in asymmetric unit (same molecule, image 0)
        print('%s%d - %s%d  %.2f  image %s' % (s[i].specie.symbol, i, s[j].specie.symbol, j, d, nb.image))
mind = 9; pair = None
for i in range(n):
    for nb in s.get_neighbors(s[i], 3.3):
        if nb.nn_distance > 1.7 and nb.nn_distance < mind and (nb.image != (0, 0, 0) or abs(nb.index - i) > 6):
            mind = nb.nn_distance; pair = (i, nb.index, nb.image)
print('shortest non-bonded contact: %.2f %s' % (mind, pair))
