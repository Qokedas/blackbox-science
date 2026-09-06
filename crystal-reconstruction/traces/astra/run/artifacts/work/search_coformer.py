"""Conditional direct-space search of only the lactam pose, with the acid fixed.
Uses a chemically validated native-refinement seed; candidates are fully refined
without freezing afterwards. No structure claim follows from this conditional fit.
"""
import os,sys,json,time,shutil,numpy as np,torch
from gallop_io import load_structure
from gallop import tensor_prep,zm_to_cart,chi2
from gallop.optim import local
from hydrogen_prefix import enable_hydrogen_prefix
from gallop_fast_symmetry import enable_fast_symmetry
from gallop_packing import enable_packing
from gallop_hbond import enable_hbonds
sid,source,run=sys.argv[1:4];W='/app/work/'+sid;S=W+'/gallop_'+source;G=W+'/gallop_'+run;os.makedirs(G,exist_ok=True)
for f in os.listdir(S):
 if f.endswith('.zmatrix') or f in ['structure.json','model.json','base.xml','warm.npz']:shutil.copyfile(S+'/'+f,G+'/'+f)
torch.set_num_threads(1);torch.set_num_interop_threads(1);s=load_structure(G+'/structure.json');enable_fast_symmetry(s);enable_hydrogen_prefix(s,G+'/model.json');enable_packing(s,G+'/model.json');enable_hbonds(s,G+'/model.json');s.get_total_degrees_of_freedom(verbose=False)
tensor_prep.get_zm_related_tensors(s,1,torch.float32,torch.device('cpu'))
warm=np.load(G+'/warm.npz');N=int(os.getenv('PARTICLES','128'));IT=int(os.getenv('ITERATIONS','350'));best=1e100;t0=time.time();me=np.ones(s.total_external_degrees_of_freedom);mi=np.ones(s.total_internal_degrees_of_freedom);me[np.r_[s.position_indices[0],s.rotation_indices[0]]]=0;mi[s.torsion_indices[0]]=0;masks=[torch.tensor(me,dtype=torch.float32),torch.tensor(mi,dtype=torch.float32)]
class MaskedAdam(torch.optim.Adam):
 def step(self,closure=None):
  for p,m in zip(self.param_groups[0]['params'],masks):
   if p.grad is not None:p.grad.mul_(m)
  return super().step(closure)
for batch in range(int(os.getenv('BATCHES','3'))):
 e=np.tile(warm['external'],(N,1));t=np.tile(warm['internal'],(N,1))
 for j in range(1,len(s.zmatrices)):
  e[1:,s.position_indices[j]]=np.random.rand(N-1,len(s.position_indices[j]));e[1:,s.rotation_indices[j]]=np.random.normal(size=(N-1,len(s.rotation_indices[j])))
 if batch:
  for j in range(1,len(s.zmatrices)):
   e[:N//4,s.position_indices[j]]=ebest[s.position_indices[j]]+np.random.normal(size=(N//4,len(s.position_indices[j])))*.10;e[:N//4,s.rotation_indices[j]]=ebest[s.rotation_indices[j]]+np.random.normal(size=(N//4,len(s.rotation_indices[j])))*.15
 opt=MaskedAdam([torch.zeros(1,requires_grad=True)],lr=.04)
 r=local.minimise(s,external=e,internal=t,n_iterations=IT,n_cooldown=IT//4,learning_rate=.04,optimizer=opt,device=torch.device('cpu'),loss='sum',use_progress_bar=False,save_CIF=False,verbose=False,check_min=25)
 assert np.max(np.abs(r['external'][:,me==0]-e[:,me==0]))<1e-5, 'Frozen acid external DOFs moved'
 if np.any(mi==0): assert np.max(np.abs(r['internal'][:,mi==0]-t[:,mi==0]))<1e-5, 'Frozen acid torsions moved'
 k=int(r['chi_2'].argmin());v=float(r['chi_2'][k]);print('COFORMER',batch,'best',v,'q25',np.quantile(r['chi_2'],.25),'sec',time.time()-t0,flush=True)
 if v<best:
  best=v;ebest=r['external'][k].copy();tbest=r['internal'][k].copy();np.savez_compressed(G+'/best.npz',external=ebest[None],internal=tbest[None],chi2=best);ts=tensor_prep.get_all_required_tensors(s,external=ebest[None],internal=tbest[None],requires_grad=False,device=torch.device('cpu'),verbose=False)
  with torch.no_grad():fr=zm_to_cart.get_asymmetric_coords(**ts['zm']).numpy()[0]
  np.save(G+'/best_frac.npy',fr);json.dump(dict(chi2=best,elapsed=time.time()-t0),open(G+'/best.json','w'))
print('FINISHED',sid,best,flush=True)
