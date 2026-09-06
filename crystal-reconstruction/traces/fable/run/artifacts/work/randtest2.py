import sys, os, numpy as np
sys.path.insert(0, '/app/work')
from solve import *
import warnings; warnings.filterwarnings('ignore')
iid = 'X3c176e2'
cell = [14.0067, 9.3253, 11.0305, 90, 90, 90]
smi = 'O[C@H]1[C@@H](O)[C@@H](O)[C@@H](O)[C@@H](O)[C@H]1O'
spg = sys.argv[1]
p, cr, pd, mols, lsq = setup(iid, cell, spg, ttmax=40, components=[{'smiles': smi, 'count': 1}], verbose=False)
m = mols[0]
sg = cr.GetSpaceGroup()
print('nsym', sg.GetNbSymmetrics(), 'asym unit', sg.GetAsymUnit().Xmax(), sg.GetAsymUnit().Ymax(), sg.GetAsymUnit().Zmax() if hasattr(sg.GetAsymUnit(), 'Zmax') else '')
for t in range(6):
    cr.RandomizeConfiguration()
    p.FitScaleFactorForRw()
    rw1 = p.GetRw()
    cr.SetUseDynPopCorr(0); p.FitScaleFactorForRw(); rw0 = p.GetRw(); cr.SetUseDynPopCorr(1)
    print('xyz %.3f %.3f %.3f  Rwp dyn=%.3f nodyn=%.3f' % (m.X, m.Y, m.Z, rw1, rw0), flush=True)
# print the scattering component list occupancy
sc = cr.GetScatteringComponentList()
print('n components', len(sc))
for i in range(min(4, len(sc))):
    c = sc[i]
    print('  occ %.3f dynpop %.3f  xyz %.3f %.3f %.3f' % (c.mOccupancy, c.mDynPopCorr, c.X, c.Y, c.Z))
os._exit(0)
