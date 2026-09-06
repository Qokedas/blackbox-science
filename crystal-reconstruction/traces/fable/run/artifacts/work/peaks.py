import numpy as np, json, sys, os
from scipy.signal import find_peaks, savgol_filter, peak_widths
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def load(iid):
    d = np.loadtxt(f'/app/data/instances/{iid}/pattern.xye')
    ins = json.load(open(f'/app/data/instances/{iid}/instrument.json'))
    comp = json.load(open(f'/app/data/instances/{iid}/composition.json'))
    return d[:,0], d[:,1], d[:,2], ins, comp

def snip_background(y, niter):
    v = np.log(np.log(np.sqrt(np.maximum(y,0)+1)+1)+1)
    n = len(v)
    w = v.copy()
    for p in range(niter, 0, -1):
        a = w[p:n-p]
        b = 0.5*(w[:n-2*p] + w[2*p:])
        w[p:n-p] = np.minimum(a, b)
    bg = (np.exp(np.exp(w)-1)-1)**2 - 1
    return bg

def pv(x, A, x0, fw, eta):
    s = fw/2.354820
    g = np.exp(-0.5*((x-x0)/s)**2)
    l = 1.0/(1+((x-x0)/(fw/2))**2)
    return A*(eta*l+(1-eta)*g)

def pick(iid, nmax=40, plot=True, minprom_sig=5.0, verbose=True, fwhm_override=None):
    tt, y, sig, ins, comp = load(iid)
    step = np.median(np.diff(tt))
    wl = ins['radiation']['wavelengths_A']
    # smoothing for detection
    sw = max(5, 2*int(0.01/step)+1)
    ysm = savgol_filter(y, sw, 2)
    # first pass: typical FWHM from strongest peaks
    # rough background by SNIP with a generous window
    win_deg = max(0.4, 1.0*(wl[0]/1.54))
    bg = snip_background(ysm, int(win_deg/step))
    net = ysm - bg
    noise = 1.4826*np.median(np.abs((y-ysm) - np.median(y-ysm))) + 1e-9
    noise = max(noise, 0.7*np.median(np.sqrt(np.maximum(y,1))))
    pk, props = find_peaks(net, prominence=minprom_sig*noise)
    if len(pk) == 0:
        return np.zeros((0,5)), (tt, y, bg, net, noise)
    w_res = peak_widths(net, pk, rel_height=0.5)
    widths = w_res[0]*step
    # typical FWHM: median of widths of the 10 most prominent peaks
    order = np.argsort(-props['prominences'])
    fw_typ = fwhm_override or np.median(widths[order[:10]])
    # refine background with window ~ 8*FWHM (min 0.3 deg)
    bg = snip_background(ysm, int(max(0.3, 8*fw_typ)/step))
    net = ysm - bg
    netraw = y - bg
    pk, props = find_peaks(net, prominence=minprom_sig*noise, distance=max(1, int(0.5*fw_typ/step)))
    w_res = peak_widths(net, pk, rel_height=0.5)
    widths = w_res[0]*step
    peaks = []
    for k, p in enumerate(pk):
        fw0 = min(max(widths[k], 0.5*fw_typ), 3*fw_typ)
        w = int(max(3, 1.2*fw0/step))
        a, b = max(0, p-w), min(len(tt), p+w+1)
        x = tt[a:b]; yy = netraw[a:b]
        h = net[p]
        try:
            popt, _ = curve_fit(pv, x, yy, p0=[h, tt[p], fw0, 0.5],
                                bounds=([0.3*h, tt[p]-fw0, 0.4*fw_typ, 0], [3*h+1, tt[p]+fw0, 3*fw_typ, 1]), maxfev=1000)
            A, x0, fw, eta = popt
        except Exception:
            A, x0, fw, eta = h, tt[p], fw0, 0.5
        snr = props['prominences'][k]/noise
        peaks.append((x0, A*fw, A, fw, snr))
    peaks = np.array(peaks)
    # discard broad humps (fw > 2.5 typical) and merge close peaks
    good = peaks[:,3] < 2.5*fw_typ
    peaks = peaks[good]
    peaks = peaks[np.argsort(peaks[:,0])]
    merged = []
    for row in peaks:
        if merged and abs(row[0]-merged[-1][0]) < 0.6*fw_typ:
            if row[2] > merged[-1][2]: merged[-1] = row
        else:
            merged.append(row)
    peaks = np.array(merged)
    # K-alpha2 removal
    if len(wl) > 1:
        l1, l2 = wl[0], wl[1]
        keep = np.ones(len(peaks), bool)
        for i, (x0, I, A, fw, s) in enumerate(peaks):
            for j, (x1, I1, A1, fw1, s1) in enumerate(peaks):
                if i == j or x1 >= x0: continue
                th1 = np.radians(x1/2)
                x2 = 2*np.degrees(np.arcsin(min(1, l2/l1*np.sin(th1))))
                if abs(x0 - x2) < 0.5*fw_typ + 0.01 and A < 0.8*A1:
                    keep[i] = False
        peaks = peaks[keep]
    if verbose:
        print(f'{iid}: step={step:.4f} noise={noise:.1f} fwhm_typ={fw_typ:.4f} npk={len(peaks)}')
    if plot:
        fig, ax = plt.subplots(2, 1, figsize=(18, 9))
        n = len(peaks)
        xmax = peaks[min(nmax, n)-1, 0]*1.05 if n else tt[-1]
        m = tt <= xmax
        ax[0].plot(tt[m], y[m], lw=0.6); ax[0].plot(tt[m], bg[m], lw=0.6)
        for x0, I, A, fw, s in peaks[:nmax]:
            ax[0].axvline(x0, color='r', lw=0.4, alpha=0.6)
        ax[0].set_title(f'{iid} first {nmax} peaks, fwhm_typ={fw_typ:.3f}')
        ax[1].plot(tt, netraw, lw=0.6)
        for x0, I, A, fw, s in peaks:
            ax[1].axvline(x0, color='r', lw=0.3, alpha=0.5)
        ax[1].set_yscale('symlog', linthresh=max(noise*5,1))
        plt.tight_layout(); plt.savefig(f'/app/work/{iid}/peaks.png', dpi=70); plt.close()
    return peaks, (tt, y, bg, netraw, noise, fw_typ)

if __name__ == '__main__':
    ids = sys.argv[1:]
    if not ids:
        ids = json.load(open('/app/data/instances.json'))['ids']
    for iid in ids:
        os.makedirs(f'/app/work/{iid}', exist_ok=True)
        peaks, aux = pick(iid)
        with open(f'/app/work/{iid}/peaks.txt', 'w') as f:
            f.write(f'# fwhm_typ {aux[5]:.5f} noise {aux[4]:.3f}\n')
            for x0, I, A, fw, s in peaks:
                f.write(f'{x0:.5f} {I:.3f} {A:.3f} {fw:.4f} {s:.1f}\n')
