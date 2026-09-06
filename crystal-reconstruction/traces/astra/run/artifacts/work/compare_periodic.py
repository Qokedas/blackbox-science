"""Origin-optimised, element-wise periodic RMS differences between candidate CIFs.
This is a diagnostic/lower bound (not a molecular-graph-aware match).
"""
import sys,numpy as np
from pymatgen.io.cif import CifParser
from scipy.optimize import minimize,linear_sum_assignment
A=CifParser(sys.argv[1]).parse_structures(primitive=False)[0];A.remove_species(['H']);L=A.lattice;fa=A.frac_coords;ea=np.array([a.specie.symbol for a in A]);els=np.unique(ea)
for path in sys.argv[2:]:
 B=CifParser(path).parse_structures(primitive=False)[0];B.remove_species(['H']);fb=B.frac_coords;eb=np.array([b.specie.symbol for b in B]);assert all((ea==e).sum()==(eb==e).sum() for e in els)
 def calc(t,detail=False):
  ds=[]
  for el in els:
   D=L.get_all_distances(fa[ea==el],fb[eb==el]+t);i,j=linear_sum_assignment(D**2);ds.extend(D[i,j])
  return (np.sqrt(np.mean(np.array(ds)**2)),max(ds)) if detail else sum(np.array(ds)**2)
 starts=[]
 for e in els:
  a=fa[ea==e][0]
  for b in fb[eb==e]:starts.append(a-b)
 best=min((minimize(calc,t,method='BFGS',options={'maxiter':90,'gtol':1e-6}) for t in starts),key=lambda r:r.fun);print(path,'origin',best.x%1,'rms/max',calc(best.x,True),flush=True)
