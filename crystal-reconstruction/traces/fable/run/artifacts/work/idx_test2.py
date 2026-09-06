import sys, time
sys.path.insert(0,'/app/work')
from index1 import *
iid='X07806d9'
t0=time.time()
res = run_index(iid, nmax=20, systems=[(CS.ORTHOROMBIC,[CC.LATTICE_P])], stop_score=60, vmin=1400, vmax=1700, lengthmax=25)
print('ortho time', time.time()-t0, flush=True)
for r in res[:5]: print(r, flush=True)
t0=time.time()
res = run_index(iid, nmax=20, systems=[(CS.MONOCLINIC,[CC.LATTICE_P])], stop_score=60, vmin=1400, vmax=1700, lengthmax=25)
print('mono time', time.time()-t0, flush=True)
for r in res[:5]: print(r, flush=True)
