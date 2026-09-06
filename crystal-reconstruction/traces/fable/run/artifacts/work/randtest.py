import sys, os, numpy as np
sys.path.insert(0, '/app/work')
from solve import *
import warnings; warnings.filterwarnings('ignore')
iid = 'X3c176e2'
cell = [14.0067, 9.3253, 11.0305, 90, 90, 90]
smi = 'O[C@H]1[C@@H](O)[C@@H](O)[C@@H](O)[C@@H](O)[C@H]1O'
for spg in sys.argv[1:]:
    p, cr, pd, mols, lsq = setup(iid, cell, spg, ttmax=40, components=[{'smiles': smi, 'count': 1}], verbose=False)
    rws = []
    for t in range(40):
        cr.RandomizeConfiguration()
        p.FitScaleFactorForRw()
        rws.append(p.GetRw())
    rws = np.array(rws)
    print(spg, 'random Rwp: min %.3f median %.3f max %.3f' % (rws.min(), np.median(rws), rws.max()), flush=True)
os._exit(0)
