import sys, os, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq0 = setup('X9af54a2', [5.1777,8.2521,32.9450,90,92.7521,90], 'P 1 21/c 1', ttmax=16, verbose=False)
restore_from_cif(cr, mols, 'X9af54a2/sol_a/P121_c1_run0_rw0.140.cif')
m = mols[0]
for i in range(m.GetNbOption()):
    o = m.GetOption(i); print('option', i, o.GetName(), o.GetChoice(), o.GetChoiceName(o.GetChoice()), [o.GetChoiceName(k) for k in range(o.GetNbChoice())])
p.FitScaleFactorForRw(); print('Rwp0', p.GetRw())
# set all options to "No"/rigid where meaningful
for i in range(m.GetNbOption()):
    o = m.GetOption(i)
    nm = o.GetName()
    if 'Auto Optimize' in nm or 'Optimize Orientation' in nm:
        o.SetChoice(1); print('set', nm, '->', o.GetChoiceName(o.GetChoice()))
sid = cr.CreateParamSet('s0'); cr.SaveParamSet(sid)
cr.BeginOptimization(True, True); p.FitScaleFactorForRw(); print('after cr.BeginOptimization(True,True)', p.GetRw()); cr.EndOptimization()
cr.RestoreParamSet(sid); p.FitScaleFactorForRw(); print('restored', p.GetRw())
# try flexibility model option
for i in range(m.GetNbOption()):
    o = m.GetOption(i)
    if 'Flex' in o.GetName():
        o.SetChoice(1); print('set', o.GetName(), '->', o.GetChoiceName(o.GetChoice()))
cr.BeginOptimization(True, True); p.FitScaleFactorForRw(); print('after cr.BeginOptimization(True,True) rigid', p.GetRw()); cr.EndOptimization()
os._exit(0)
