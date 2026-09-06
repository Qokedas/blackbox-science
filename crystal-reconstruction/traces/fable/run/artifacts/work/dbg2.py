import sys, time, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq = setup('X07806d9', [16.8866, 8.2184, 11.2380, 90, 90, 90], 'P b c a', ttmax=30, verbose=False)
print('nb scatterers', cr.GetNbScatterer())
mc = MonteCarlo()
mc.AddRefinableObj(cr)
mc.AddRefinableObj(p)
mc._fix_parameters_for_global_optim()
print('llk', mc.GetLogLikelihood(), 'Rwp', p.GetRw())
t0=time.time()
mc.Optimize(20000, 0, -1)
print('20000 steps', time.time()-t0, 'llk', mc.GetLogLikelihood(), 'Rwp', p.GetRw(), 'chi2', p.GetChi2())
for i in range(cr.GetNbPar()):
    par = cr.GetPar(i)
    print(par.GetName(), par.GetValue(), par.IsFixed())
os._exit(0)
