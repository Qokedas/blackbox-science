import sys, os, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq0 = setup('X9af54a2', [5.1777,8.2521,32.9450,90,92.7521,90], 'P 1 21/c 1', ttmax=16, verbose=False)
restore_from_cif(cr, mols, 'X9af54a2/sol_a/P121_c1_run0_rw0.140.cif')
p.FitScaleFactorForRw(); print('Rwp0', p.GetRw(), flush=True)
ok = polish(p, cr, ncycle=30)
print('after polish', p.GetRw(), ok, 'restraint', cr.GetRestraintCost())
write_cif(cr, 'X9af54a2/sol_a/polished_test.cif')
os._exit(0)
