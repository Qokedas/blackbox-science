import sys, os, json, numpy as np, time
sys.path.insert(0, '/app/work')
from lebail import make_pattern, fit_sequence
from pyobjcryst.crystal import create_crystal_from_cif
from pyobjcryst.powderpattern import ReflectionProfileType
from pyobjcryst.lsq import LSQ
import warnings; warnings.filterwarnings('ignore')
# usage: fitplot.py <id> <cif> <ttmax> [out.png]
iid, cif, ttmax = sys.argv[1], sys.argv[2], float(sys.argv[3])
out = sys.argv[4] if len(sys.argv) > 4 else cif.replace('.cif', '_fit.png')
p, ins = make_pattern(iid, tt_max=ttmax)
cr = create_crystal_from_cif(open(cif, 'rb'))
cr.SetUseDynPopCorr(1)
pd = p.AddPowderPatternDiffraction(cr)
pd.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 1e-7)
pd.SetExtractionMode(False)
p.FitScaleFactorForRw()
lsq = LSQ(); lsq.SetRefinedObj(p, 0, True, True); lsq.PrepareRefParList(True)
lsqr = lsq.GetCompiledRefinedObj(); lsqr.FixAllPar()
from pyobjcryst.powderpattern import refpartype_scattdata_background
for names in [['Zero'], ['W'], ['U', 'V'], ['Eta0'], ['background'], ['Zero', 'W', 'U', 'V', 'Eta0', 'background']]:
    for n in names:
        try:
            if n == 'background': lsq.SetParIsFixed(refpartype_scattdata_background, False)
            else: lsq.SetParIsFixed(n, False)
        except Exception as e: pass
    try:
        lsq.SafeRefine(nbCycle=8, useLevenbergMarquardt=True, silent=True)
    except Exception as e:
        print('fail', names, e)
    p.FitScaleFactorForRw()
    print(names, 'Rwp=%.4f' % p.GetRw(), flush=True)
print(f'{iid} {cif}: Rwp={p.GetRw():.4f} chi2={p.GetChi2():.1f}')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
x = np.degrees(p.GetPowderPatternX()); yo = p.GetPowderPatternObs(); yc = p.GetPowderPatternCalc()
fig, axs = plt.subplots(2, 1, figsize=(18, 10))
axs[0].plot(x, yo, 'k', lw=0.5); axs[0].plot(x, yc, 'r', lw=0.5); axs[0].plot(x, yo-yc-0.2*yo.max(), 'b', lw=0.5)
axs[0].set_title(f'{iid} {os.path.basename(cif)} Rwp={p.GetRw():.3f}')
n = len(x); m = slice(0, n//2)
axs[1].plot(x[m], yo[m], 'k', lw=0.6); axs[1].plot(x[m], yc[m], 'r', lw=0.6); axs[1].plot(x[m], (yo-yc)[m]-0.2*yo[m].max(), 'b', lw=0.5)
plt.tight_layout(); plt.savefig(out, dpi=65); print(out)
os._exit(0)
