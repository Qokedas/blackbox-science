"""Alternating conditional rigid-fragment direct-space searches.
A validated native seed supplies the unchanged fragments; only the selected
fragments are randomized/optimized in each pass. Final Rietveld refinement must
release all fragments. This is a search, not an assertion of convergence.
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
warm=np.load(G+'/warm.npz');N=int(os.getenv('PARTICLES','128'));IT=int(os.getenv('ITERATIONS','350'));t0=time.time()
cur_e=warm['external'][0].copy();cur_t=warm['internal'][0].copy();best=1.e100
schedule=[list(map(int,v.split(','))) for v in os.getenv('FREE_SCHEDULE','0;1;0;1').split(';')]
def save(e,t,v,step):
 np.savez_compressed(G+'/best.npz',external=e[None],internal=t[None],chi2=v)
 ts=tensor_prep.get_all_required_tensors(s,external=e[None],internal=t[None],requires_grad=False,device=torch.device('cpu'),verbose=False)
 with torch.no_grad():fr=zm_to_cart.get_asymmetric_coords(**ts['zm']).numpy()[0]
 np.save(G+'/best_frac.npy',fr);json.dump(dict(chi2=float(v),elapsed=time.time()-t0,step=step),open(G+'/best.json','w'))
ts=tensor_prep.get_all_required_tensors(s,external=cur_e[None],internal=cur_t[None],requires_grad=False,device=torch.device('cpu'),verbose=False)
with torch.no_grad():best=float(chi2.get_chi_2(ts['zm'],ts['int_tensors'],ts['chisqd_tensors'])[0])
save(cur_e,cur_t,best,-1);print('INITIAL',sid,best,flush=True)
for step,free in enumerate(schedule):
 me=np.zeros(s.total_external_degrees_of_freedom);mi=np.zeros(s.total_internal_degrees_of_freedom)
 for j in free:
  me[np.r_[s.position_indices[j],s.rotation_indices[j]]]=1;mi[s.torsion_indices[j]]=1
 masks=[torch.tensor(me,dtype=torch.float32),torch.tensor(mi,dtype=torch.float32)]
 class MaskedAdam(torch.optim.Adam):
  def step(self,closure=None):
   for p,m in zip(self.param_groups[0]['params'],masks):
    if p.grad is not None:p.grad.mul_(m)
   return super().step(closure)
 e=np.tile(cur_e,(N,1));t=np.tile(cur_t,(N,1));near=N//4
 for j in free:
  pp=s.position_indices[j];rr=s.rotation_indices[j];tt=s.torsion_indices[j]
  e[1:near,pp]+=np.random.normal(size=(near-1,len(pp)))*.10
  e[near:,pp]=np.random.rand(N-near,len(pp))
  if len(rr):
   e[1:near,rr]+=np.random.normal(size=(near-1,len(rr)))*.25
   e[near:,rr]=np.random.normal(size=(N-near,len(rr)))
  if len(tt):
   t[1:near,tt]+=np.random.normal(size=(near-1,len(tt)))*.4
   t[near:,tt]=np.random.uniform(-np.pi,np.pi,size=(N-near,len(tt)))
 opt=MaskedAdam([torch.zeros(1,requires_grad=True)],lr=.04)
 r=local.minimise(s,external=e,internal=t,n_iterations=IT,n_cooldown=IT//4,learning_rate=.04,optimizer=opt,device=torch.device('cpu'),loss='sum',use_progress_bar=False,save_CIF=False,verbose=False,check_min=25)
 assert np.max(np.abs(r['external'][:,me==0]-e[:,me==0]),initial=0)<1e-5,'Fixed external DoFs moved'
 assert np.max(np.abs(r['internal'][:,mi==0]-t[:,mi==0]),initial=0)<1e-5,'Fixed internal DoFs moved'
 k=int(r['chi_2'].argmin());v=float(r['chi_2'][k]);print('CONDITIONAL',step,free,'best',v,'q25',np.quantile(r['chi_2'],.25),'sec',time.time()-t0,flush=True)
 if v<best:
  best=v;cur_e=r['external'][k].copy();cur_t=r['internal'][k].copy();save(cur_e,cur_t,best,step)
print('FINISHED',sid,best,flush=True)
