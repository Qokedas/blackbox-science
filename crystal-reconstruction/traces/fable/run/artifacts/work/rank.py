import sys, json, glob, re, numpy as np
from pymatgen.core import Lattice

def parse(iid):
    cells = []
    for fn in glob.glob(f'/app/work/{iid}/g2index_*_20.txt') + glob.glob(f'/app/work/{iid}/g2index_*_25.txt') + glob.glob(f'/app/work/{iid}/g2index_*_15.txt') + glob.glob(f'/app/work/{iid}/g2index_*_30.txt') + glob.glob(f'/app/work/{iid}/extra_cells.txt'):
        for line in open(fn):
            m = re.match(r'M20=\s*([\d.]+) X20=\s*(\d+) Nc=\s*(-?\d+) (\S+)\s+a=\s*([\d.]+) b=\s*([\d.]+) c=\s*([\d.]+) al=\s*([\d.]+) be=\s*([\d.]+) ga=\s*([\d.]+) V=\s*([\d.]+)', line)
            if m:
                M20, X20, Nc = float(m.group(1)), int(m.group(2)), int(m.group(3))
                brav = m.group(4)
                cell = [float(m.group(i)) for i in range(5, 11)]
                V = float(m.group(11))
                cells.append(dict(M20=M20, X20=X20, Nc=Nc, brav=brav, cell=cell, V=V, src=fn.split('/')[-1]))
    return cells

def hkl_list(cell, dmin, brav):
    lat = Lattice.from_parameters(*cell)
    rec = lat.reciprocal_lattice_crystallographic
    a, b, c = cell[:3]
    hmax = int(a/dmin)+1; kmax = int(b/dmin)+1; lmax = int(c/dmin)+1
    H, K, L = np.mgrid[-hmax:hmax+1, -kmax:kmax+1, -lmax:lmax+1]
    H = H.ravel(); K = K.ravel(); L = L.ravel()
    m = ~((H == 0) & (K == 0) & (L == 0))
    H, K, L = H[m], K[m], L[m]
    cen = brav.split('-')[-1] if '-' in brav else 'P'
    if cen == 'C': m = (H+K) % 2 == 0
    elif cen == 'A': m = (K+L) % 2 == 0
    elif cen == 'B': m = (H+L) % 2 == 0
    elif cen == 'I': m = (H+K+L) % 2 == 0
    elif cen == 'F': m = ((H+K) % 2 == 0) & ((K+L) % 2 == 0)
    elif cen == 'R': m = ((-H+K+L) % 3 == 0)
    else: m = np.ones(len(H), bool)
    H, K, L = H[m], K[m], L[m]
    g = np.stack([H, K, L], 1) @ rec.matrix
    d = 1/np.linalg.norm(g, axis=1)
    d = d[d >= dmin]
    return np.unique(np.round(d, 5))

def fom(cell, brav, tth, wl, npk=30, tol_frac=0.35, fwhm=0.05):
    """de Wolff-like M(N) using first npk peaks; plus count unindexed"""
    tth = tth[:npk]
    d = wl/(2*np.sin(np.radians(tth/2)))
    q = 1/d**2
    dcalc = hkl_list(cell, d.min()*0.98, brav)
    qc = np.sort(1/dcalc**2)
    # nearest calc line for each obs
    idx = np.searchsorted(qc, q)
    best = np.zeros(len(q))
    for i in range(len(q)):
        cands = [qc[j] for j in (idx[i]-1, idx[i]) if 0 <= j < len(qc)]
        best[i] = min(abs(q[i]-c) for c in cands) if cands else 1e9
    # tolerance in q from tolerance in 2theta
    tol_tth = max(tol_frac*fwhm, 0.008)  # deg
    dq_tol = np.abs(np.gradient(q, tth))*tol_tth if len(tth) > 1 else 0.001
    indexed = best <= dq_tol
    nidx = indexed.sum()
    mean_dq = best[indexed].mean() if nidx else 1
    Ncalc = (qc <= q.max()*1.0001).sum()
    MN = (q.max()/ (2*mean_dq*max(Ncalc,1))) if nidx else 0
    return nidx, len(q), Ncalc, MN

if __name__ == '__main__':
    iid = sys.argv[1]
    npk = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    ins = json.load(open(f'/app/data/instances/{iid}/instrument.json'))
    wl = ins['radiation']['wavelengths_A'][0]
    nheavy = {x['id']: x['heavy_atoms_per_formula_unit'] for x in json.load(open('/app/data/instances.json'))['instances']}[iid]
    import os
    pfn = f'/app/work/{iid}/peaks_clean.txt'
    if not os.path.exists(pfn): pfn = f'/app/work/{iid}/peaks.txt'
    pk = np.loadtxt(pfn)
    fwhm = float(open(f'/app/work/{iid}/peaks.txt').readline().split()[2])
    pk = pk[pk[:,4] >= 8.0]
    tth = pk[:,0]
    cells = parse(iid)
    # dedupe by niggli reduced cell
    seen = []
    out = []
    for c in cells:
        try:
            lat = Lattice.from_parameters(*c['cell'])
            nig = lat.get_niggli_reduced_lattice()
        except Exception:
            continue
        key = tuple(np.round(nig.abc, 2)) + tuple(np.round(nig.angles, 1))
        dup = False
        for s in seen:
            if np.allclose(s[:3], key[:3], rtol=0.01) and np.allclose(s[3:], key[3:], atol=1.0):
                dup = True; break
        if dup: continue
        seen.append(key)
        nidx, nobs, ncalc, MN = fom(c['cell'], c['brav'], tth, wl, npk=npk, fwhm=fwhm)
        zest = c['V']/(18*nheavy)
        c.update(nidx=nidx, nobs=nobs, ncalc=ncalc, MN=MN, zest=zest)
        out.append(c)
    out.sort(key=lambda c: -(c['MN'] if c['nidx'] >= 0.85*c['nobs'] else c['MN']*0.05*c['nidx']/c['nobs']))
    print(f'{iid}: nheavy={nheavy} fwhm={fwhm:.3f} npk={npk}')
    for c in out[:25]:
        a, b, cc, al, be, ga = c['cell']
        print(f"M20={c['M20']:6.1f} Nc={c['Nc']:3d} {c['brav']:16s} a={a:8.4f} b={b:8.4f} c={cc:8.4f} al={al:7.3f} be={be:7.3f} ga={ga:7.3f} V={c['V']:8.1f} Z~{c['zest']:5.2f} | idx {c['nidx']}/{c['nobs']} Ncalc={c['ncalc']:4d} M({npk})={c['MN']:6.1f}")
