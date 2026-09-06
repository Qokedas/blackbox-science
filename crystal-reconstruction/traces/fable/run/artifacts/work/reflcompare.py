import sys, os, json, numpy as np
sys.path.insert(0, '/app/work')
from lebail import make_pattern, fit_sequence, add_crystal
from pyobjcryst.crystal import create_crystal_from_cif
from pyobjcryst.powderpattern import ReflectionProfileType
import warnings; warnings.filterwarnings('ignore')
iid, cif, ttmax = sys.argv[1], sys.argv[2], float(sys.argv[3])
cr = create_crystal_from_cif(open(cif, 'rb'))
cell = (cr.a, cr.b, cr.c, np.degrees(cr.alpha), np.degrees(cr.beta), np.degrees(cr.gamma))
spg = cr.GetSpaceGroup().GetName()
# Le Bail
p, ins = make_pattern(iid, tt_max=ttmax)
cr2, pd = add_crystal(p, cell, spg)
pd.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 1e-7)
steps = [['Zero'], ['W'], ['U', 'V'], ['Eta0'], ['background'], ['Zero', 'W', 'U', 'V', 'Eta0', 'background']]
fit_sequence(p, pd, steps)
print('LeBail Rwp %.4f' % p.GetRw())
h, k, l = pd.GetH().astype(int), pd.GetK().astype(int), pd.GetL().astype(int)
fobs = np.array(pd.GetFhklObsSq()); mult = np.array(pd.GetMultiplicity()) if hasattr(pd, 'GetMultiplicity') else np.ones_like(fobs)
tt = np.degrees(2*np.arcsin(np.array(pd.GetSinThetaOverLambda())*ins['radiation']['wavelengths_A'][0]))
# calc from model: build second pattern
p3, _ = make_pattern(iid, tt_max=ttmax)
cr.SetUseDynPopCorr(1)
pd3 = p3.AddPowderPatternDiffraction(cr)
pd3.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 1e-7)
pd3.SetExtractionMode(False)
p3.FitScaleFactorForRw()
h3, k3, l3 = pd3.GetH().astype(int), pd3.GetK().astype(int), pd3.GetL().astype(int)
fc = np.array(pd3.GetFhklCalcSq())
d3 = {(a, b, c): v for a, b, c, v in zip(h3, k3, l3, fc)}
fcal = np.array([d3.get((a, b, c), np.nan) for a, b, c in zip(h, k, l)])
m = np.isfinite(fcal) & (fobs > 0)
# scale: on strong reflections with LP-ish weighting via multiplicity
scale = np.sum(fobs[m]*fcal[m]) / np.sum(fcal[m]**2)
fcal *= scale
n = int(sys.argv[4]) if len(sys.argv) > 4 else 25
print('R(F2) = %.3f' % (np.sum(np.abs(fobs[m]-fcal[m]))/np.sum(fobs[m])))
order = np.argsort(-np.abs(fobs - fcal))
print(' h  k  l   2th    Fobs2    Fcalc2   ratio')
for i in order[:n]:
    print('%2d %2d %2d  %6.3f  %8.0f  %8.0f  %5.2f' % (h[i], k[i], l[i], tt[i], fobs[i], fcal[i], fobs[i]/max(fcal[i], 1e-6)))
print('--- strongest obs')
for i in np.argsort(-fobs)[:15]:
    print('%2d %2d %2d  %6.3f  %8.0f  %8.0f  %5.2f' % (h[i], k[i], l[i], tt[i], fobs[i], fcal[i], fobs[i]/max(fcal[i], 1e-6)))
os._exit(0)
