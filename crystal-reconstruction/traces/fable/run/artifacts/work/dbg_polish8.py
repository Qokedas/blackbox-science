import sys, os, re, numpy as np
sys.path.insert(0,'/app/work')
from solve import *
p, cr, pd, mols, lsq0 = setup('X9af54a2', [5.1777,8.2521,32.9450,90,92.7521,90], 'P 1 21/c 1', ttmax=16, verbose=False)
restore_from_cif(cr, mols, 'X9af54a2/sol_a/P121_c1_run0_rw0.140.cif')
for i in range(cr.GetNbScatterer()):
    sc = cr.GetScatt(i)
    if hasattr(sc, 'GetNbOption'):
        for k in range(sc.GetNbOption()):
            o = sc.GetOption(k)
            if 'Auto Optimize' in o.GetName(): o.SetChoice(1)
p.FitScaleFactorForRw(); print('Rwp0', p.GetRw(), flush=True)
lsq = LSQ()
lsq.SetRefinedObj(p, 0, True, True)
lsq.PrepareRefParList(True)
lsqr = lsq.GetCompiledRefinedObj()
lsqr.UnFixAllPar()
atomcoord = re.compile(r'^[A-Z][a-z]?\d+_[xyz]$')
nfree=0
for i in range(lsqr.GetNbPar()):
    par = lsqr.GetPar(i); n = par.GetName()
    if n.startswith('Biso') or n.startswith('Occup') or n.startswith('Asym') or n in ('Eta1',) or n.startswith('ML-') or n.endswith('occup') or atomcoord.match(n) or n.startswith('Global'):
        par.SetIsFixed(True)
    if not par.IsFixed():
        nfree+=1; print('free:', n, par.GetHumanValue())
print('nfree', nfree)
try:
    lsq.Refine(20, True, True, False)
except Exception as e:
    print('Refine exception', e)
print('after Refine', p.GetRw(), 'chi2', p.GetChi2(), 'restraint', cr.GetRestraintCost())
write_cif(cr, 'X9af54a2/sol_a/polished_rb.cif')
os._exit(0)
