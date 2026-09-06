import sys, os, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq0 = setup('X9af54a2', [5.1777,8.2521,32.9450,90,92.7521,90], 'P 1 21/c 1', ttmax=16, verbose=False)
restore_from_cif(cr, mols, 'X9af54a2/sol_a/P121_c1_run0_rw0.140.cif')
m = mols[0]
for i in range(m.GetNbOption()):
    o = m.GetOption(i); print('option', o.GetName(), o.GetChoice(), o.GetChoiceName(o.GetChoice()))
p.FitScaleFactorForRw(); print('Rwp0', p.GetRw())
sid = cr.CreateParamSet('s0'); cr.SaveParamSet(sid)
cr.BeginOptimization(True, True); p.FitScaleFactorForRw(); print('after cr.BeginOptimization(True,True)', p.GetRw()); cr.EndOptimization()
cr.RestoreParamSet(sid); p.FitScaleFactorForRw(); print('restored', p.GetRw())
cr.BeginOptimization(False, False); p.FitScaleFactorForRw(); print('after cr.BeginOptimization(False,False)', p.GetRw()); cr.EndOptimization()
cr.RestoreParamSet(sid); p.FitScaleFactorForRw(); print('restored', p.GetRw())
p.BeginOptimization(True, True); p.FitScaleFactorForRw(); print('after p.BeginOptimization(True,True)', p.GetRw()); p.EndOptimization()
cr.RestoreParamSet(sid); p.FitScaleFactorForRw(); print('restored', p.GetRw())
pd.BeginOptimization(True, True); p.FitScaleFactorForRw(); print('after pd.BeginOptimization(True,True)', p.GetRw()); pd.EndOptimization()
os._exit(0)
