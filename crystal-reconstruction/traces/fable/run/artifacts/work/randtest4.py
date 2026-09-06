import sys, os, numpy as np
sys.path.insert(0, '/app/work')
from solve import *
import warnings; warnings.filterwarnings('ignore')
iid = 'X3c176e2'
cell = [14.0067, 9.3253, 11.0305, 90, 90, 90]
smi = 'O[C@H]1[C@@H](O)[C@@H](O)[C@@H](O)[C@@H](O)[C@H]1O'
for spg in sys.argv[1:]:
    p, cr, pd, mols, lsq = setup(iid, cell, spg, ttmax=40, components=[{'smiles': smi, 'count': 1}], verbose=False)
    x = np.degrees(p.GetPowderPatternX()); obs = np.array(p.GetPowderPatternObs())
    bg = np.array(p.GetPowderPatternComponent(0).GetPowderPatternCalc()) if False else None
    for t in range(3):
        cr.RandomizeConfiguration()
        p.FitScaleFactorForRw()
        tot = np.array(p.GetPowderPatternCalc())
        dif = np.array(pd.GetPowderPatternCalc())
        # scaled diffraction part = tot - background; background = tot - scaled_diff; get scale by ratio
        i = np.argmax(dif)
        print(spg, 'Rwp %.3f' % p.GetRw(), 'tot max %.0f at %.2f' % (tot.max(), x[np.argmax(tot)]), 'obs max %.0f' % obs.max(), 'diff-calc argmax at %.2f' % x[i], 'tot-min %.0f' % tot.min())
        # crude: scaled diffraction = tot - min(tot)?? print tot at the 020 (19.02) and 211 (17.75)
        for ang in (16.05, 17.75, 19.02, 9.48, 10.2):
            j = np.argmin(abs(x-ang)); print('    2th %.2f obs %.0f tot %.0f' % (ang, obs[j], tot[j]))
os._exit(0)
