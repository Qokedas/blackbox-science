import sys, os, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq0 = setup('X9af54a2', [5.1777,8.2521,32.9450,90,92.7521,90], 'P 1 21/c 1', ttmax=16, verbose=False)
restore_from_cif(cr, mols, 'X9af54a2/sol_a/P121_c1_run0_rw0.140.cif')
p.FitScaleFactorForRw(); print('Rwp', p.GetRw())
lsq = LSQ(); lsq.SetRefinedObj(p, 0, True, True); lsq.PrepareRefParList(True)
lsqr = lsq.GetCompiledRefinedObj()
print('npar', lsqr.GetNbPar(), 'notfixed', lsqr.GetNbParNotFixed())
lsq.UnFixAllPar()
print('after lsq.UnFixAllPar notfixed', lsqr.GetNbParNotFixed())
names = [lsqr.GetPar(i).GetName() for i in range(lsqr.GetNbPar())]
print(names[:60])
for i in range(lsqr.GetNbPar()):
    par = lsqr.GetPar(i); n = par.GetName()
    if n.startswith('Biso') or n.startswith('Occup') or n.startswith('Asym') or n == 'Eta1':
        par.SetIsFixed(True)
print('notfixed', lsqr.GetNbParNotFixed())
try:
    lsq.SafeRefine(nbCycle=10, useLevenbergMarquardt=True, silent=False)
except Exception as e:
    print('err', e)
p.FitScaleFactorForRw(); print('Rwp after', p.GetRw(), 'restraint', cr.GetRestraintCost())
os._exit(0)
