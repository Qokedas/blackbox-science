import sys, os, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq0 = setup('X9af54a2', [5.1777,8.2521,32.9450,90,92.7521,90], 'P 1 21/c 1', ttmax=16, verbose=False)
restore_from_cif(cr, mols, 'X9af54a2/sol_a/P121_c1_run0_rw0.140.cif')
p.FitScaleFactorForRw(); print('Rwp', p.GetRw())
lsq = LSQ(); lsq.SetRefinedObj(p, 0, True, True); lsq.PrepareRefParList(True)
lsqr = lsq.GetCompiledRefinedObj()
names = [lsqr.GetPar(i).GetName() for i in range(lsqr.GetNbPar())]
print(names[55:])
lsqr.FixAllPar()
def unfix(pred):
    n=0
    for i in range(lsqr.GetNbPar()):
        par = lsqr.GetPar(i)
        if pred(par.GetName()): par.SetIsFixed(False); n+=1
    return n
for stage, pred in [('scale+bg', lambda n: n.startswith('Background') or n=='Scale_' or n=='Zero'),
                    ('mol pos/orient', lambda n: any(n.endswith(s) for s in ('_x','_y','_z','_Q0','_Q1','_Q2','_Q3')) and 'Background' not in n),
                    ('profile+cell', lambda n: n in ('U','V','W','Eta0','a','b','c','beta')),
                    ('atoms', lambda n: n.startswith('mol') and not any(n.endswith(s) for s in ('_x','_y','_z','_Q0','_Q1','_Q2','_Q3','_Occ')))]:
    k = unfix(pred)
    try:
        lsq.SafeRefine(nbCycle=10, useLevenbergMarquardt=True, silent=True)
    except Exception as e:
        print('err', e)
    p.FitScaleFactorForRw(); print(stage, k, 'Rwp after', p.GetRw(), 'restraint', cr.GetRestraintCost(), flush=True)
write_cif(cr, 'X9af54a2/sol_a/dbg_polished.cif')
os._exit(0)
