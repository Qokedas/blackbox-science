"""Patterson/partial-structure search for two inversion-related heavy-atom pairs.
Only used as a source of direct-space starting positions, not a final model.
"""
import os,sys,json,time,numpy as np,torch,gemmi
from gallop.structure import Structure
from rdkit import Chem
sid=sys.argv[1];run=sys.argv[2];G='/app/work/'+sid+'/gallop_'+run
s=Structure();s.from_json(open(G+'/structure.json').read());md=json.load(open(G+'/model.json'));assert s.original_sg_number==2
els=[e for z in s.zmatrices for e in z.elements_no_H];atomic=np.array([gemmi.Element(e).atomic_number for e in els]);idx=np.flatnonzero(atomic==atomic.max());assert len(idx)==2
T=lambda x:torch.tensor(x,dtype=torch.float32)
torch.set_num_threads(1);torch.set_num_interop_threads(1)
ss=np.linalg.norm(s.hkl@s.lattice.reciprocal_lattice_crystallographic.matrix,axis=1)/2
sf=np.array([[gemmi.Element(el).it92.calculate_sf(float(v*v)) for el in els] for v in ss])*np.exp(-3*ss[:,None]**2)
fh=T(2*sf[:,idx[0]]);wilson=T(2*np.sum(np.delete(sf,idx,axis=1)**2,axis=1));hk=T(s.hkl);nm=T(s.inverse_covariance_matrix/(len(s.hkl)-2));obs=T(s.intensities);no=nm@obs;oo=obs@no;lm=T(s.lattice.matrix)
def score(x):
 f=(torch.cos(2*np.pi*(x@hk.T)).sum(1)*fh)**2+wilson
 nf=f@nm;of=f@no;cost=oo-of.clamp(min=0)**2/(f*nf).sum(1).clamp(min=1e-20)
 # Suppress merged Br sites; this is a partial heavy atom model, not chemistry.
 df=x[:,0]-x[:,1];df-=torch.round(df).detach();dr=x[:,0]+x[:,1];dr-=torch.round(dr).detach()
 penalty=200*(torch.clamp(2.6-torch.linalg.norm(df@lm,dim=-1),min=0)**2+torch.clamp(2.6-torch.linalg.norm(dr@lm,dim=-1),min=0)**2)
 return cost+penalty
N=int(os.environ.get('PARTICLES','384'));IT=int(os.environ.get('ITERATIONS','450'));maxsec=float(os.environ.get('SEARCH_TIME','300'));t0=time.time();pool=[];best=None
for batch in range(99):
 x=T(np.random.rand(N,2,3))
 if best is not None:x[:N//4]=T(best)[None]+torch.randn_like(x[:N//4])*.045
 x.requires_grad_(True);opt=torch.optim.Adam([x],lr=.025)
 for it in range(IT):
  opt.zero_grad();loss=score(x).sum();loss.backward();opt.step()
  if it==IT*3//4:
   for g in opt.param_groups:g['lr']=.003
 with torch.no_grad():
  vals=score(x).numpy();positions=x.numpy()%1
 for j in np.argsort(vals)[:80]:pool.append((float(vals[j]),positions[j].copy()))
 pool.sort(key=lambda a:a[0]);pool=pool[:120];best=pool[0][1]
 np.savez_compressed(G+'/heavy_pool.npz',positions=np.array([v[1] for v in pool]),chi2=np.array([v[0] for v in pool]),indices=idx)
 print('HEAVY',batch,'best',pool[0][0],'q25',np.quantile(vals,.25),'elapsed',time.time()-t0,flush=True)
 if time.time()-t0>maxsec:break
