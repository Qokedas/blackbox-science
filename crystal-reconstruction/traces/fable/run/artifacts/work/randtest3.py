import sys, os, numpy as np
sys.path.insert(0, '/app/work')
from solve import *
import warnings; warnings.filterwarnings('ignore')
iid = 'X3c176e2'
cell = [14.0067, 9.3253, 11.0305, 90, 90, 90]
smi = 'O[C@H]1[C@@H](O)[C@@H](O)[C@@H](O)[C@@H](O)[C@H]1O'
for spg in sys.argv[1:]:
    p, cr, pd, mols, lsq = setup(iid, cell, spg, ttmax=40, components=[{'smiles': smi, 'count': 1}], verbose=False)
    cr.RandomizeConfiguration()
    p.FitScaleFactorForRw()
    calc = np.array(pd.GetPowderPatternCalc())
    tot = np.array(p.GetPowderPatternCalc()); obs = np.array(p.GetPowderPatternObs())
    f2 = np.array(pd.GetFhklCalcSq())
    h = pd.GetH(); k = pd.GetK(); l = pd.GetL()
    print(spg, 'Rwp %.3f' % p.GetRw(), 'nrefl', len(h), 'F2 max %.1f mean %.2f nan %d' % (np.nanmax(f2), np.nanmean(f2), np.isnan(f2).sum()), 'scale', p.GetScaleFactor(0) if hasattr(p, 'GetScaleFactor') else '?', 'calc max %.1f' % np.nanmax(calc), 'obs max %.0f' % obs.max(), flush=True)
    # first 8 reflections
    for i in range(6):
        print('   %d %d %d  F2=%.2f' % (h[i], k[i], l[i], f2[i]))
os._exit(0)
