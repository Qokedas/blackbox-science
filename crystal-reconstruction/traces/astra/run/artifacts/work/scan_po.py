"""Test whether a single March-Dollase texture term explains a residual.
This is conditional on a candidate structure and is not evidence of solution.
"""
import sys,os,json,numpy as np,torch,itertools
from scipy.optimize import minimize_scalar
from gallop import tensor_prep,zm_to_cart,intensities
from gallop_io import load_structure
from hydrogen_prefix import enable_hydrogen_prefix
from gallop_fast_symmetry import enable_fast_symmetry
torch.set_num_threads(1);torch.set_num_interop_threads(1)
sid=sys.argv[1];run=sys.argv[2];G='/app/work/'+sid+'/gallop_'+run;s=load_structure(G+'/structure.json');enable_fast_symmetry(s);enable_hydrogen_prefix(s,G+'/model.json');best=np.load(G+'/best.npz');ts=tensor_prep.get_all_required_tensors(s,external=best['external'],internal=best['internal'],requires_grad=False,device=torch.device('cpu'),verbose=False)
with torch.no_grad():fr=zm_to_cart.get_asymmetric_coords(**ts['zm']);f=intensities.calculate_intensities(fr,**ts['int_tensors']).numpy()[0]
obs=s.intensities;N=np.asarray(s.inverse_covariance_matrix)/(len(s.hkl)-2);no=N@obs;oo=obs@no;B=s.lattice.reciprocal_lattice_crystallographic.matrix;g=s.hkl@B;gn=np.linalg.norm(g,axis=1)
def chi(f):return float(oo-max(f@no,0)**2/max(f@N@f,1e-30))
base=chi(f);out=[]
for ax in itertools.product(range(-1,2),repeat=3):
 if not any(ax):continue
 if next(x for x in ax if x)!=1:continue
 u=np.array(ax)@B;c2=((g@u)/(gn*np.linalg.norm(u)))**2
 def fun(lr):
  r=np.exp(lr);md=(r*r*c2+(1-c2)/r)**(-1.5);return chi(f*md)
 fit=minimize_scalar(fun,bounds=(np.log(.25),np.log(4)),method='bounded');out.append(dict(axis=ax,MD=float(np.exp(fit.x)),chi=float(fit.fun)))
out.sort(key=lambda a:a['chi']);print('BASE',base,flush=True)
for a in out[:8]:print(a,flush=True)
json.dump({'untextured_chi':base,'scan':out},open(G+'/po_scan.json','w'),indent=1)
