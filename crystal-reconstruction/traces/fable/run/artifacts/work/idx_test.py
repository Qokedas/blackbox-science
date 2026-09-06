import sys, time
sys.path.insert(0,'/app/work')
from index1 import *
iid='X4f6fe58'
t0=time.time()
res = run_index(iid, nmax=20, systems=[(CS.MONOCLINIC,[CC.LATTICE_P])], stop_score=60, vmin=900, vmax=1800)
print('time', time.time()-t0)
for r in res[:10]: print(r)
