import sys, os, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq0 = setup('X9af54a2', [5.1777,8.2521,32.9450,90,92.7521,90], 'P 1 21/c 1', ttmax=16, verbose=False)
restore_from_cif(cr, mols, 'X9af54a2/sol_a/P121_c1_run0_rw0.140.cif')
p.FitScaleFactorForRw(); print('Rwp', p.GetRw(), 'chi2', p.GetChi2())
sid = cr.CreateParamSet('s0'); cr.SaveParamSet(sid)
pid = p.CreateParamSet('p0'); p.SaveParamSet(pid)
for recursive in (False, True):
    for names in (['Scale_'], ['Zero'], ['Background'], ['mol0_0_x','mol0_0_y','mol0_0_z']):
        cr.RestoreParamSet(sid); p.RestoreParamSet(pid); p.FitScaleFactorForRw()
        lsq = LSQ(); lsq.SetRefinedObj(p, 0, True, recursive); lsq.PrepareRefParList(True)
        lsqr = lsq.GetCompiledRefinedObj(); lsqr.FixAllPar()
        k=0
        for i in range(lsqr.GetNbPar()):
            par = lsqr.GetPar(i)
            if any(par.GetName().startswith(n) for n in names): par.SetIsFixed(False); k+=1
        c0 = lsq.ChiSquare()
        try:
            lsq.Refine(nbCycle=5, useLevenbergMarquardt=True, silent=True)
        except Exception as e:
            print('err', e)
        print(f'recursive={recursive} names={names} k={k} chi2 {c0:.1f} -> {lsq.ChiSquare():.1f} Rwp {p.GetRw():.4f}', flush=True)
os._exit(0)
