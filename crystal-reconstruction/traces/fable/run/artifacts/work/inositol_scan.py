import sys, os, time, json, numpy as np
sys.path.insert(0, '/app/work')
from solve import *
iid = 'X3c176e2'
spg = sys.argv[1]; zp = int(sys.argv[2]); isos = [int(x) for x in sys.argv[3].split(',')]
nsteps = float(sys.argv[4]); nruns = int(sys.argv[5]); tag = sys.argv[6]
cell = [14.0067, 9.3253, 11.0305, 90, 90, 90]
if len(sys.argv) > 7: cell = [float(x) for x in sys.argv[7].split(',')]
smis = ['O[C@H]1[C@@H](O)[C@@H](O)[C@@H](O)[C@@H](O)[C@H]1O',
'O[C@H]1[C@@H](O)[C@@H](O)[C@@H](O)[C@@H](O)[C@@H]1O',
'O[C@H]1[C@H](O)[C@H](O)[C@@H](O)[C@@H](O)[C@H]1O',
'O[C@H]1[C@H](O)[C@@H](O)[C@H](O)[C@@H](O)[C@H]1O',
'O[C@H]1[C@H](O)[C@H](O)[C@H](O)[C@@H](O)[C@H]1O',
'O[C@H]1[C@H](O)[C@@H](O)[C@@H](O)[C@H](O)[C@H]1O',
'O[C@H]1[C@H](O)[C@@H](O)[C@H](O)[C@H](O)[C@H]1O',
'O[C@H]1[C@H](O)[C@H](O)[C@@H](O)[C@H](O)[C@H]1O',
'O[C@H]1[C@H](O)[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O']
outdir = f'/app/work/{iid}/inos_{tag}'; os.makedirs(outdir, exist_ok=True)
seed = int(time.time()*1000) % 2**31; np.random.seed(seed)
import ctypes; ctypes.CDLL(None).srand(seed)
for k in isos:
    comps = [{'smiles': smis[k], 'count': zp}]
    p, cr, pd, mols, lsq = setup(iid, cell, spg, ttmax=float(os.environ.get("TTMAX","40")), components=comps, verbose=False)
    mc, res = optimize(p, cr, nsteps=nsteps, nruns=nruns, save_prefix=f'{outdir}/iso{k}_{spg.replace(" ","")}', do_polish=False)
    print(f'ISO {k} {spg} Zp={zp}: ' + ' '.join(f'{r[1]:.4f}' for r in res), flush=True)
os._exit(0)
