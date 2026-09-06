import warnings; warnings.filterwarnings('ignore')
import sys, numpy as np
from pymatgen.io.cif import CifParser
import scipy.sparse.csgraph as cg, scipy.sparse as sp

def contacts(fn, dmax=3.0, nshow=12):
    s = CifParser(fn).parse_structures(primitive=False)[0]
    s.remove_species(['H'])
    n = len(s)
    dm = s.distance_matrix
    adj = sp.csr_matrix(dm < 1.9)
    ncomp, lab = cg.connected_components(adj)
    print(fn, 'atoms', n, 'fragments', ncomp)
    out = []
    for i in range(n):
        for x in s.get_neighbors(s[i], dmax):
            j = x.index
            if lab[i] != lab[j] and i <= j:
                out.append((round(float(x.nn_distance), 2), s[i].species_string + str(i), s[j].species_string + str(j)))
    out.sort()
    for o in out[:nshow]:
        print('  ', o)
    return out

if __name__ == '__main__':
    dmax = 3.0
    for fn in sys.argv[1:]:
        contacts(fn, dmax)
