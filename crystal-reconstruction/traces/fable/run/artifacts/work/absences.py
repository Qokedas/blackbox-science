import sys, json, numpy as np, time, os
sys.path.insert(0, '/app/work')
from lebail import *

def lebail_intensities(iid, cell, spg, ttmax=None, verbose=False):
    p, ins = make_pattern(iid, tt_max=ttmax)
    cr, pd = add_crystal(p, cell, spg)
    pd.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 1e-7)
    steps = [['Zero'], ['W'], ['a', 'b', 'c', 'alpha', 'beta', 'gamma'], ['U', 'V'], ['Eta0'], ['Eta1'], ['background'],
             ['Zero', 'W', 'U', 'V', 'Eta0', 'background', 'a', 'b', 'c', 'alpha', 'beta', 'gamma']]
    lsq = fit_sequence(p, pd, steps, verbose=verbose)
    for i in range(3):
        pd.ExtractLeBail(30)
    h = np.array(pd.GetH(), dtype=int); k = np.array(pd.GetK(), dtype=int); l = np.array(pd.GetL(), dtype=int)
    I = np.array(pd.GetFhklObsSq())
    n = pd.GetNbReflBelowMaxSinThetaOvLambda()
    # multiplicity? GetFhklObsSq are |F|^2 per unique reflection
    stol = np.array(pd.GetSinThetaOverLambda())
    return p, cr, pd, h[:n], k[:n], l[:n], I[:n], stol[:n]

def analyse(h, k, l, I, stol, dmin_frac=0.6, label=''):
    # restrict to lower-angle part where overlap is less severe
    smax = stol.max()*dmin_frac
    m = stol <= smax
    h, k, l, I = h[m], k[m], l[m], I[m]
    tot_mean = I.mean()
    lines = []
    def cls(name, sel, cond):
        s = sel & (h != 0) | sel  # dummy
        sub = sel
        if sub.sum() < 3:
            return
        absent = sub & cond
        present = sub & ~cond
        if absent.sum() == 0 or present.sum() == 0:
            return
        ra = I[absent].mean()/tot_mean
        rp = I[present].mean()/tot_mean
        lines.append((name, int(absent.sum()), ra, int(present.sum()), rp, ra/max(rp, 1e-9)))
    odd = lambda x: (x % 2) != 0
    zero = lambda x: x == 0
    cls('h00: h odd (2_1 a)', zero(k) & zero(l), odd(h))
    cls('0k0: k odd (2_1 b)', zero(h) & zero(l), odd(k))
    cls('00l: l odd (2_1 c)', zero(h) & zero(k), odd(l))
    cls('0kl: k odd (b_a)', zero(h), odd(k))
    cls('0kl: l odd (c_a)', zero(h), odd(l))
    cls('0kl: k+l odd (n_a)', zero(h), odd(k+l))
    cls('h0l: h odd (a_b)', zero(k), odd(h))
    cls('h0l: l odd (c_b)', zero(k), odd(l))
    cls('h0l: h+l odd (n_b)', zero(k), odd(h+l))
    cls('hk0: h odd (a_c)', zero(l), odd(h))
    cls('hk0: k odd (b_c)', zero(l), odd(k))
    cls('hk0: h+k odd (n_c)', zero(l), odd(h+k))
    cls('hkl: h+k odd (C)', np.ones(len(h), bool), odd(h+k))
    cls('hkl: h+l odd (B)', np.ones(len(h), bool), odd(h+l))
    cls('hkl: k+l odd (A)', np.ones(len(h), bool), odd(k+l))
    cls('hkl: h+k+l odd (I)', np.ones(len(h), bool), odd(h+k+l))
    print(f'--- absences {label}: {len(h)} reflections used (stol<={smax:.3f})')
    print(f'{"class":24s} {"nAbs":>5s} {"<I>abs":>8s} {"nPres":>5s} {"<I>pres":>8s} {"ratio":>7s}')
    for name, na, ra, npres, rp, ratio in lines:
        flag = ' <== ABSENT?' if ratio < 0.08 else (' (weak)' if ratio < 0.2 else '')
        print(f'{name:24s} {na:5d} {ra:8.3f} {npres:5d} {rp:8.3f} {ratio:7.3f}{flag}')
    return lines

if __name__ == '__main__':
    iid = sys.argv[1]
    cell = [float(v) for v in sys.argv[2:8]]
    spg = sys.argv[8]
    ttmax = float(sys.argv[9]) if len(sys.argv) > 9 else None
    p, cr, pd, h, k, l, I, stol = lebail_intensities(iid, cell, spg, ttmax)
    print(f'{iid} {spg} Rwp={p.GetRw():.4f} nrefl={len(h)} cell= {cr.a:.5f} {cr.b:.5f} {cr.c:.5f} {np.degrees(cr.alpha):.4f} {np.degrees(cr.beta):.4f} {np.degrees(cr.gamma):.4f}')
    for frac in (0.5, 1.0):
        analyse(h, k, l, I, stol, frac)
    # also list the strongest low-angle reflections
    order = np.argsort(stol)
    print('lowest-angle reflections (h k l  2theta  I):')
    wl = p.GetWavelength()
    for i in order[:40]:
        tth = 2*np.degrees(np.arcsin(stol[i]*wl))
        print(f'  {h[i]:3d} {k[i]:3d} {l[i]:3d}  {tth:7.3f}  {I[i]:10.1f}')
    os._exit(0)
