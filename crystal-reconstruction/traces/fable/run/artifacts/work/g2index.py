import sys, json, time, numpy as np
sys.path.insert(0, '/opt/g2/GSAS-II')
from GSASII import GSASIIindex as G2indx
from GSASII import GSASIIlattice as G2lat

bravaisNames = ['Cubic-F','Cubic-I','Cubic-P','Trigonal-R','Trigonal/Hexagonal-P',
        'Tetragonal-I','Tetragonal-P','Orthorhombic-F','Orthorhombic-I','Orthorhombic-A',
        'Orthorhombic-B','Orthorhombic-C',
        'Orthorhombic-P','Monoclinic-I','Monoclinic-A','Monoclinic-C','Monoclinic-P','Triclinic']

def load_peaks(iid, nmax=20, min_snr=8.0, pkfile=None):
    ins = json.load(open(f'/app/data/instances/{iid}/instrument.json'))
    wl = ins['radiation']['wavelengths_A'][0]
    import os
    fn = pkfile or f'/app/work/{iid}/peaks_clean.txt'
    if not os.path.exists(fn): fn = f'/app/work/{iid}/peaks.txt'
    p = np.loadtxt(fn)
    p = p[p[:,4] >= min_snr][:nmax]
    peaks = []
    for row in p:
        d = wl/(2*np.sin(np.radians(row[0]/2)))
        peaks.append([row[0], row[1], True, False, 0, 0, 0, d, 0.0])
    return peaks, wl

def run(iid, nmax=20, brav=None, ncno=4, V1=25.0, timeout=300, zero=0.0, min_snr=8.0, M20_min=2.0, pkfile=None):
    peaks, wl = load_peaks(iid, nmax, min_snr, pkfile)
    print('peaks used:', [round(x[0],3) for x in peaks])
    if brav is None:
        brav = [0]*18
        for i in [16, 15, 12, 11, 9, 8, 13]:  # mono-P, mono-C, ortho-P, ortho-C, A, I, mono-I
            brav[i] = 1
    controls = [0, zero, ncno, V1, 0, 'P1', 0,0,0,90,90,90]
    t0 = time.time()
    OK, dmin, cells = G2indx.DoIndexPeaks(peaks, controls, brav, None, timeout=timeout, M20_min=M20_min, X20_max=None, return_Nc=True)
    print('elapsed', time.time()-t0, 'ncells', len(cells))
    cells.sort(key=lambda c: -c[0])
    return cells

if __name__ == '__main__':
    iid = sys.argv[1]
    nmax = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    bravsel = sys.argv[3] if len(sys.argv) > 3 else 'mono'
    timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    brav = [0]*18
    sel = {'mono': [16, 15], 'ortho': [12, 11, 9, 8, 7, 10], 'tri': [17], 'high': [0,1,2,3,4,5,6], 'monoP': [16], 'monoC': [15], 'orthoP': [12]}
    for k in bravsel.split(','):
        for i in sel[k]: brav[i] = 1
    nheavy = {x['id']: x['heavy_atoms_per_formula_unit'] for x in json.load(open('/app/data/instances.json'))['instances']}[iid]
    tag = sys.argv[5] if len(sys.argv) > 5 else ''
    pkfile = sys.argv[6] if len(sys.argv) > 6 else None
    cells = run(iid, nmax, brav, timeout=timeout, pkfile=pkfile)
    with open(f'/app/work/{iid}/g2index_{bravsel}{tag}_{nmax}.txt', 'w') as f:
        for c in cells[:30]:
            M20, X20, ibrav, a, b, cc, al, be, ga, V = c[:10]
            Nc = c[12] if len(c) > 12 else -1
            line = f'M20={M20:7.1f} X20={X20:2d} Nc={Nc:3d} {bravaisNames[ibrav]:16s} a={a:8.4f} b={b:8.4f} c={cc:8.4f} al={al:7.3f} be={be:7.3f} ga={ga:7.3f} V={V:8.1f} Z~{V/18/nheavy:.2f}'
            print(line); f.write(line+'\n')
