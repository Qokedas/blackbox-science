"""Topology-preserving basin-hop mutations for small molecular populations."""
import numpy as np, torch, gemmi
from scipy.spatial.transform import Rotation
from gallop import tensor_prep,zm_to_cart

def coords(s,ext,intr):
 z=tensor_prep.get_zm_related_tensors(s,len(ext),torch.float32,torch.device('cpu'));z.pop('nsamples_ones',None)
 with torch.no_grad():
  f=zm_to_cart.get_asymmetric_coords(external=torch.as_tensor(ext,dtype=torch.float32),internal=torch.as_tensor(intr,dtype=torch.float32),lattice_inv_matrix=torch.as_tensor(np.linalg.inv(s.lattice.matrix),dtype=torch.float32),**z)
 return f.numpy()

def macro_mutations(s,external,internal,n):
 e=np.tile(external,(n,1));t=np.tile(internal,(n,1));old=coords(s,e,t);offs=np.cumsum([0]+[len(z.elements_no_H) for z in s.zmatrices]);anchors=[]
 for k in range(n):
  j=np.random.randint(len(s.zmatrices));p=s.position_indices[j];r=s.rotation_indices[j];tors=s.torsion_indices[j];N=offs[j+1]-offs[j]
  znum=np.array([gemmi.Element(str(x)).atomic_number for x in s.zmatrices[j].elements_no_H]);a=int(znum.argmax()) if znum.max()>9 else np.random.randint(N);a+=offs[j]
  mode=np.random.choice(5,p=[.25,.25,.25,.15,.10])
  anchor=False
  if mode==0 and len(tors):
   # Flip one rotatable substituent while retaining most of the phased scaffold.
   tor=np.random.choice(tors);t[k,tor]+=np.random.choice([np.pi,-np.pi,2*np.pi/3,-2*np.pi/3])+np.random.normal(scale=.10);anchor=True
  elif mode in [1,2] and len(r):
   if mode==1 and N>=2:
    b=int(np.argsort(znum)[-2]) if znum.max()>9 else np.random.randint(N)
    if b+offs[j]==a:b=(b+1)%N
    axis=(old[k,b+offs[j]]-old[k,a])@s.lattice.matrix
   else:axis=np.random.normal(size=3)
   axis/=max(np.linalg.norm(axis),1e-10);ang=np.random.choice([np.pi,2*np.pi/3,-2*np.pi/3,np.pi/2])+np.random.normal(scale=.10)
   q=e[k,r];q=q/max(np.linalg.norm(q),1e-10);rot=Rotation.from_rotvec(axis*ang)*Rotation.from_quat(q[[1,2,3,0]]);nq=rot.as_quat();e[k,r]=nq[[3,0,1,2]];anchor=True
  elif mode==3:
   e[k,p]+=np.random.normal(size=len(p))*np.random.choice([.12,.25,.4])
   if len(tors):t[k,tors]+=np.random.normal(size=len(tors))*.25
  else:
   # Restart only one fragment, not the whole crystal.
   e[k,p]=np.random.rand(len(p))
   if len(r):e[k,r]=np.random.normal(size=len(r))
   if len(tors):t[k,tors]=np.random.uniform(-np.pi,np.pi,size=len(tors))
  if anchor:anchors.append((k,j,a))
 if anchors:
  new=coords(s,e,t)
  for k,j,a in anchors:e[k,s.position_indices[j]]+=old[k,a]-new[k,a]
 e[:,np.hstack(s.position_indices)]%=1
 return e,t

def heavy_initialise(s,external,internal,path,fraction=.8):
 pool=np.load(path);pp=pool['positions'];ii=pool['indices'];ne=int(len(external)*fraction);fr=coords(s,external[:ne],internal[:ne]);offs=np.cumsum([0]+[len(z.elements_no_H) for z in s.zmatrices]);e=external.copy()
 for k in range(ne):
  pos=pp[np.random.randint(min(len(pp),60))].copy()
  if np.random.rand()<.5:pos=pos[::-1]
  pos*=np.random.choice([-1,1],size=(len(pos),1));pos+=np.random.choice([0,.5],size=(1,3))
  for a,xyz in zip(ii,pos):
   j=np.searchsorted(offs,a,side='right')-1;e[k,s.position_indices[j]]+=xyz-fr[k,a]
 e[:,np.hstack(s.position_indices)]%=1
 return e,internal
