import sys, warnings; warnings.filterwarnings('ignore')
from pymatgen.io.cif import CifParser
from pymatgen.analysis.structure_matcher import StructureMatcher
import numpy as np
def load(f):
    s = CifParser(f).parse_structures(primitive=False)[0]
    s.remove_species(['H'])
    return s
a = load(sys.argv[1]); b = load(sys.argv[2])
sm = StructureMatcher(ltol=0.2, stol=0.5, angle_tol=5, primitive_cell=True, scale=False, attempt_supercell=False)
print('fit:', sm.fit(a, b))
r = sm.get_rms_dist(a, b)
print('rms(normalized), max:', r)
if r is not None:
    # convert normalized to Å: pymatgen normalizes by (V/N)^(1/3)
    n = (a.volume/len(a))**(1/3)
    print('approx rms Å = %.3f  max Å = %.3f' % (r[0]*n, r[1]*n))
