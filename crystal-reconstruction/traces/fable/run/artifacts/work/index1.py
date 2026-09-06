import numpy as np, json, sys, os, time
import pyobjcryst.indexing as I
from pyobjcryst.indexing import CrystalSystem as CS, CrystalCentering as CC

def load_peaks(iid, nmax=25, merge_frac=0.6, min_snr=8.0):
    ins = json.load(open(f'/app/data/instances/{iid}/instrument.json'))
    wl = ins['radiation']['wavelengths_A'][0]
    p = np.loadtxt(f'/app/work/{iid}/peaks.txt')
    # merge close peaks
    out = []
    for row in p:
        if out and abs(row[0]-out[-1][0]) < merge_frac*max(row[3], out[-1][3]):
            # keep stronger
            if row[2] > out[-1][2]: out[-1] = row
        else:
            out.append(row)
    p = np.array(out)
    p = p[p[:,4] >= min_snr]
    p = p[:nmax]
    d = wl/(2*np.sin(np.radians(p[:,0]/2)))
    return p, d, wl

def run_index(iid, nmax=25, vmin=None, vmax=None, systems=None, nspur=0, lengthmax=None, verbose=False, min_snr=8.0, stop_score=60):
    p, d, wl = load_peaks(iid, nmax, min_snr=min_snr)
    comp = json.load(open(f'/app/data/instances/{iid}/composition.json'))
    pl = I.PeakList()
    # write temporary file 2theta intensity
    fn = f'/app/work/{iid}/pl_{nmax}.txt'
    with open(fn, 'w') as f:
        for row in p:
            f.write(f'{row[0]:.5f} {row[1]:.3f}\n')
    pl.Import2ThetaIntensity(fn, wl)
    print(f'{iid}: {len(pl)} peaks, d range {d.min():.3f}-{d.max():.3f}')
    if systems is None:
        systems = [(CS.CUBIC, [CC.LATTICE_P, CC.LATTICE_I, CC.LATTICE_F]),
                   (CS.TETRAGONAL, [CC.LATTICE_P, CC.LATTICE_I]),
                   (CS.RHOMBOEDRAL, [CC.LATTICE_P]),
                   (CS.HEXAGONAL, [CC.LATTICE_P]),
                   (CS.ORTHOROMBIC, [CC.LATTICE_P, CC.LATTICE_A, CC.LATTICE_B, CC.LATTICE_C, CC.LATTICE_I, CC.LATTICE_F]),
                   (CS.MONOCLINIC, [CC.LATTICE_P, CC.LATTICE_A, CC.LATTICE_C, CC.LATTICE_I]),
                   (CS.TRICLINIC, [CC.LATTICE_P])]
    results = []
    for csys, cents in systems:
        for cent in cents:
            ex = I.CellExplorer(pl, csys, nspur)
            ex.SetCrystalCentering(cent)
            ex.SetD2Error(0)
            ex.SetAngleMinMax(np.radians(90), np.radians(140))
            if vmin is None:
                vmin_ = I.EstimateCellVolume(1/d.min(), 1/d.max()/10, len(d), csys, cent, 1.5)
                vmax_ = I.EstimateCellVolume(1/d.min(), 1/d.max()/10, len(d), csys, cent, 0.3)
            else:
                vmin_, vmax_ = vmin, vmax
            ex.SetVolumeMinMax(vmin_, vmax_)
            lm = lengthmax or max(25, 3*vmax_**(1/3))
            ex.SetLengthMinMax(3, lm)
            t0 = time.time()
            ex.DicVol(10, 4, stop_score, 6, verbose)
            sols = ex.GetSolutions()
            best = ex.GetBestScore()
            print(f'  {csys.name:12s} {cent.name} V={vmin_:.0f}-{vmax_:.0f} nsol={len(sols)} best={best:.1f} t={time.time()-t0:.1f}s', flush=True)
            for s in sols:
                ruc, score = s
                cell = ruc.DirectUnitCell(False, True)
                results.append((score, csys.name, cent.name, cell))
    results.sort(key=lambda r: -r[0])
    return results

if __name__ == '__main__':
    iid = sys.argv[1]
    nmax = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    nspur = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    res = run_index(iid, nmax=nmax, nspur=nspur)
    comp = json.load(open(f'/app/data/instances/{iid}/composition.json'))
    nheavy = json.load(open('/app/data/instances.json'))
    nheavy = {x['id']: x['heavy_atoms_per_formula_unit'] for x in nheavy['instances']}[iid]
    print(f'heavy atoms/fu = {nheavy}, V(Z=1)~{18*nheavy:.0f}')
    with open(f'/app/work/{iid}/index_{nmax}_{nspur}.txt', 'w') as f:
        for score, cs, cc, cell in res[:40]:
            a, b, c, al, be, ga, V = cell
            line = f'{score:7.1f} {cs:12s} {cc:9s} a={a:8.4f} b={b:8.4f} c={c:8.4f} al={al:7.3f} be={be:7.3f} ga={ga:7.3f} V={V:8.1f} Z~{V/18/nheavy:.2f}'
            print(line); f.write(line+'\n')
