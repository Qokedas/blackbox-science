import sys,os,json,itertools,numpy as np,torch
from scipy.optimize import minimize_scalar
from gallop_io import load_structure
from gallop import tensor_prep,zm_to_cart,intensities
from hydrogen_prefix import enable_hydrogen_prefix
sid=sys.argv[1];run=sys.argv[2];G='/app/work/'+sid+'/gallop_'+run;torch.set_num_threads(1);torch.set_num_interop_threads(1)
s=load_structure(G+'/structure.json');enable_hydrogen_prefix(s,G+'/model.json');v=np.load(G+'/best.npz');ts=tensor_prep.get_all_required_tensors(s,external=v['external'],internal=v['internal'],requires_grad=False,device=torch.device('cpu'),verbose=False)
with torch.no_grad():
 fr=zm_to_cart.get_asymmetric_coords(**ts['zm']);f=intensities.calculate_intensities(fr,**ts['int_tensors']).numpy()[0]
hkl=s.hkl;rec=s.lattice.reciprocal_lattice_crystallographic.matrix;nm=s.inverse_covariance_matrix/(len(hkl)-2);obs=s.intensities;no=nm@obs;oo=obs@no
rv=hkl@rec;norm=np.linalg.norm(rv,axis=-1)
def score(fc):
 nf=nm@fc;dot=fc@no;return oo-max(0,dot)**2/(fc@nf)
rows=[]
for ax in itertools.product(range(-2,3),repeat=3):
 if max(abs(x) for x in ax)==0:continue
 if np.gcd.reduce(np.abs(ax))>1:continue
 u=np.array(ax)@rec;co=(rv@u/(norm*np.linalg.norm(u)))**2
 def ev(lr):
  r=np.exp(lr);md=(r*r*co+(1-co)/r)**(-1.5);return score(f*md)
 z=minimize_scalar(ev,bounds=(np.log(.4),np.log(2.5)),method='bounded');rows.append((z.fun,ax,float(np.exp(z.x))))
rows.sort();print('PO_SCAN',sid,run,'original',score(f),'best',rows[:12],flush=True)
json.dump({'baseline':float(score(f)),'candidates':rows},open(G+'/po_scan.json','w'),indent=1)
