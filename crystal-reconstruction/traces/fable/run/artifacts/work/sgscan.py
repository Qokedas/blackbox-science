import sys, json, numpy as np, gemmi, os, time
sys.path.insert(0, '/app/work')
from lebail import *
# usage: sgscan.py <id> a b c al be ga <system: ortho|mono|tri> ttmax
iid = sys.argv[1]; cell = [float(v) for v in sys.argv[2:8]]; system = sys.argv[8]; ttmax = float(sys.argv[9])
# enumerate candidate space groups (all settings) with unique extinction patterns
hkls = [(h,k,l) for h in range(0,5) for k in range(0,5) for l in range(0,5) if (h,k,l)!=(0,0,0)]
hkls += [(h,k,l) for h in range(-4,0) for k in range(0,5) for l in range(0,5)]
cands = {}
for sg in gemmi.spacegroup_table():
    cs = sg.crystal_system_str()
    if system == 'ortho' and cs != 'orthorhombic': continue
    if system == 'mono' and cs != 'monoclinic': continue
    if system == 'tri' and cs != 'triclinic': continue
    if system == 'mono' and sg.hm.split()[1] == '1' and sg.hm.split()[3] == '1':
        pass
    elif system == 'mono':
        continue  # only b-unique settings
    ops = sg.operations()
    pat = tuple(ops.is_systematically_absent(h) for h in hkls)
    key = (sg.centring_type(), pat)
    if key not in cands or (sg.is_centrosymmetric() and not cands[key].is_centrosymmetric()):
        cands[key] = sg
    elif sg.is_centrosymmetric() == cands[key].is_centrosymmetric() and sg.number > cands[key].number:
        cands[key] = sg
print(len(cands), 'unique extinction patterns')
res = []
for key, sg in cands.items():
    t0 = time.time()
    try:
        r, p, cr, pd, lsq = lebail(iid, cell, sg.hm, tt_max=ttmax, verbose=False)
        # count observed peaks without any reflection nearby handled by Rwp; report
        res.append((r['rw'], sg.hm, sg.number, r['nrefl'], r['cell']))
        print(f'{sg.hm:14s} #{sg.number:3d} Rwp={r["rw"]:.4f} nrefl={r["nrefl"]:4d} t={time.time()-t0:.0f}s', flush=True)
    except Exception as e:
        print(sg.hm, 'failed', e, flush=True)
res.sort()
print('--- sorted by Rwp (fewer reflections with same Rwp preferred)')
for rw, hm, num, nrefl, c in res:
    print(f'{hm:14s} #{num:3d} Rwp={rw:.4f} nrefl={nrefl:4d} cell={["%.4f"%v for v in c]}')
os._exit(0)
