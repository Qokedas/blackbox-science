import sys, json, numpy as np, time
import pyobjcryst
from pyobjcryst.crystal import Crystal
from pyobjcryst.powderpattern import PowderPattern, PowderPatternBackground, PowderPatternDiffraction, ReflectionProfileType, SpaceGroupExplorer, refpartype_scattdata_background
from pyobjcryst.lsq import LSQ
from pyobjcryst.radiation import RadiationType
import warnings
warnings.filterwarnings('ignore')

def make_pattern(iid, tt_max=None, tt_min=None, nbg=24):
    ins = json.load(open(f'/app/data/instances/{iid}/instrument.json'))
    wls = ins['radiation']['wavelengths_A']
    d = np.loadtxt(f'/app/data/instances/{iid}/pattern.xye')
    tt, y, sig = d[:,0], d[:,1], d[:,2]
    if tt_max is not None:
        m = tt <= tt_max
        tt, y, sig = tt[m], y[m], sig[m]
    if tt_min is None:
        import os
        cfgf = f'/app/work/{iid}/config.json'
        if os.path.exists(cfgf):
            tt_min = json.load(open(cfgf)).get('tt_min')
    if tt_min is not None:
        m = tt >= tt_min
        tt, y, sig = tt[m], y[m], sig[m]
    sig = np.where(sig <= 0, 1.0, sig)
    import os
    excl = os.environ.get('EXCLUDE')
    if excl:
        fac = float(os.environ.get('EXCL_FACTOR', '30'))
        for reg in excl.split(';'):
            lo, hi = [float(v) for v in reg.split(',')]
            mm = (tt > lo) & (tt < hi)
            sig[mm] *= fac
            print(f'down-weighting {lo}-{hi} deg ({mm.sum()} points) by sigma x{fac}', flush=True)
    p = PowderPattern()
    p.SetWavelength(wls[0])
    if len(wls) > 1:
        # Kalpha1/2 doublet
        try:
            p.SetWavelength('Mo' if wls[0] < 1 else 'Cu')
            rad = p.GetRadiation()
            rad.SetWavelength(wls[0])  # hmm
        except Exception as e:
            print('doublet setup failed', e)
        p.SetWavelength(wls[0])
        try:
            p.GetRadiation().SetXRayTubeName('Mo' if wls[0] < 1 else 'Cu')
            p.GetRadiation().SetXRayTubeDeltaLambda(wls[1]-wls[0])
            p.GetRadiation().SetXRayTubeAlpha2Alpha1Ratio(ins['radiation']['wavelength_weights'][1])
        except Exception as e:
            print('doublet setup 2 failed', e)
    if excl:
        tmpf = f'/tmp/pat_{os.getpid()}.xye'
        np.savetxt(tmpf, np.c_[tt, y, sig], fmt='%.5f %.4f %.5f')
        p.ImportPowderPattern2ThetaObsSigma(tmpf, 0)
        os.remove(tmpf)
    else:
        p.SetPowderPatternX(np.radians(tt))
        p.SetPowderPatternObs(y)
    # background
    bx = np.linspace(np.radians(tt[0]), np.radians(tt[-1]), nbg)
    by = np.zeros(nbg)
    b = p.AddPowderPatternBackground()
    b.SetInterpPoints(bx, by)
    b.UnFixAllPar()
    b.OptimizeBayesianBackground()
    return p, ins

def add_crystal(p, cell, spg, name='cryst'):
    a, b, c, al, be, ga = cell
    cr = Crystal(a, b, c, np.radians(al), np.radians(be), np.radians(ga), spg)
    cr.SetName(name)
    pd = p.AddPowderPatternDiffraction(cr)
    return cr, pd

def fit_sequence(p, pd, steps, verbose=False, ncycle=10):
    """steps: list of lists of parameter names to free progressively"""
    pd.SetExtractionMode(True, True)
    pd.ExtractLeBail(10)
    lsq = LSQ()
    lsq.SetRefinedObj(p, 0, True, True)
    lsq.PrepareRefParList(True)
    lsqr = lsq.GetCompiledRefinedObj()
    lsqr.FixAllPar()
    for names in steps:
        for n in names:
            try:
                if n == 'background':
                    lsq.SetParIsFixed(refpartype_scattdata_background, False)
                else:
                    lsq.SetParIsFixed(n, False)
            except Exception as e:
                if verbose: print('cannot free', n, e)
        if lsqr.GetNbParNotFixed() == 0:
            continue
        sid = lsqr.CreateParamSet('save')
        lsqr.SaveParamSet(sid)
        rw0 = p.GetRw()
        try:
            lsq.SafeRefine(nbCycle=ncycle, useLevenbergMarquardt=True, silent=True)
            pd.ExtractLeBail(10)
            lsq.SafeRefine(nbCycle=ncycle, useLevenbergMarquardt=True, silent=True)
            if not np.isfinite(p.GetRw()) or p.GetRw() > rw0*1.5 + 0.05:
                raise ValueError('diverged')
        except Exception as e:
            if verbose: print('refine step failed', names, e)
            lsqr.RestoreParamSet(sid)
            for n in names:
                try:
                    if n != 'background': lsq.SetParIsFixed(n, True)
                except Exception: pass
        if verbose: print('step', names, 'Rwp=%.4f' % p.GetRw(), flush=True)
    pd.ExtractLeBail(20)
    return lsq

def lebail(iid, cell, spg='P1', tt_max=None, plot=None, verbose=False, nbg=24, asym=False, refine_cell=True):
    p, ins = make_pattern(iid, tt_max=tt_max, nbg=nbg)
    cr, pd = add_crystal(p, cell, spg)
    pd.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 1e-7)
    steps = [['Zero'], ['W'], ['U', 'V'], ['Eta0'], ['Eta1'], ['background']]
    if refine_cell:
        steps.insert(2, ['a', 'b', 'c', 'alpha', 'beta', 'gamma'])
    if asym:
        steps.append(['Asym0', 'Asym1'])
    steps.append(['Zero', 'W', 'U', 'V', 'Eta0', 'background'] + (['a', 'b', 'c', 'alpha', 'beta', 'gamma'] if refine_cell else []))
    lsq = fit_sequence(p, pd, steps, verbose=verbose)
    res = dict(rw=p.GetRw(), r=p.GetR(), chi2=p.GetChi2(), rw_int=p.GetIntegratedRw(), gof=p.GetChi2()/max(1, p.GetNbPointUsed()),
               cell=(cr.a, cr.b, cr.c, cr.alpha*180/np.pi, cr.beta*180/np.pi, cr.gamma*180/np.pi), nrefl=pd.GetNbReflBelowMaxSinThetaOvLambda())
    if plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        x = np.degrees(p.GetPowderPatternX()); yo = p.GetPowderPatternObs(); yc = p.GetPowderPatternCalc()
        fig, axs = plt.subplots(2, 1, figsize=(18, 10))
        ax = axs[0]
        ax.plot(x, yo, 'k', lw=0.5); ax.plot(x, yc, 'r', lw=0.5); ax.plot(x, yo-yc - 0.2*yo.max(), 'b', lw=0.5)
        ax.set_title(f'{iid} {spg} Rwp={res["rw"]:.3f} chi2/N={res["gof"]:.2f}  cell={["%.4f"%v for v in res["cell"]]}')
        ax = axs[1]
        n = len(x); m = slice(0, n//3)
        ax.plot(x[m], yo[m], 'k.-', lw=0.5, ms=2); ax.plot(x[m], yc[m], 'r', lw=0.7); ax.plot(x[m], (yo-yc)[m] - 0.2*yo[m].max(), 'b', lw=0.5)
        plt.tight_layout(); plt.savefig(plot, dpi=70); plt.close()
    return res, p, cr, pd, lsq

if __name__ == '__main__':
    iid = sys.argv[1]
    cell = [float(v) for v in sys.argv[2:8]]
    spg = sys.argv[8] if len(sys.argv) > 8 else 'P1'
    tt_max = float(sys.argv[9]) if len(sys.argv) > 9 else None
    t0 = time.time()
    res, p, cr, pd, lsq = lebail(iid, cell, spg, tt_max=tt_max, verbose=True, plot=f'/app/work/{iid}/lebail_{spg.replace(" ","").replace("/","_")}.png')
    print(f'{iid} {spg}: Rwp={res["rw"]:.4f} R={res["r"]:.4f} chi2/N={res["gof"]:.3f} nrefl={res["nrefl"]} cell={["%.4f"%v for v in res["cell"]]} t={time.time()-t0:.1f}s', flush=True)
    import os; os._exit(0)
