"""Optional loose positional prior for an independently fitted heavy substructure.
All P-1 orbit, permutation and half-origin alternatives are retained.  This is
an exploratory conditional search; the prior must be removed in final refinement.
"""
import os,itertools,numpy as np,torch
from gallop import chi2,zm_to_cart

def enable_heavy_anchor(s,path):
 p=np.load(path);r=p['positions'][0];idx=p['indices'];assert len(idx)==2 and s.original_sg_number==2
 cases=[]
 for perm in [(0,1),(1,0)]:
  for signs in itertools.product([-1,1],repeat=2):
   for shift in itertools.product([0,.5],repeat=3):
    cases.append((r[list(perm)]*np.array(signs)[:,None]+shift)%1)
 target=torch.tensor(np.array(cases),dtype=torch.float32);idx=torch.tensor(idx,dtype=torch.long);LM=torch.tensor(s.lattice.matrix,dtype=torch.float32)
 shifts=torch.tensor(np.array(list(itertools.product([-1,0,1],repeat=3)))@s.lattice.matrix,dtype=torch.float32);ss=(shifts*shifts).sum(-1)
 coef=float(os.getenv('HEAVY_ANCHOR_COEFF','30'));tol=float(os.getenv('HEAVY_ANCHOR_TOL','.35'))
 def penalty(fr):
  delta=fr[:,None,idx,:]-target[None,:,:,:];delta-=torch.round(delta).detach();cart=delta@LM
  with torch.no_grad():corr=shifts[(2*(cart.detach()@shifts.T)+ss).argmin(-1)]
  dist=torch.sqrt(((cart+corr)**2).sum(-1)+1e-8);val=(torch.clamp(dist-tol,min=0)**2).sum(-1)
  return coef*val.min(-1).values
 old=chi2.get_chi_2
 def calc(zm,int_tensors,chisqd_tensors,profile=None):
  fr=zm_to_cart.get_asymmetric_coords(**zm)
  return old(zm,int_tensors,chisqd_tensors,profile=profile)+penalty(fr)
 chi2.get_chi_2=calc;s.heavy_anchor_penalty=penalty
 print('HEAVY_ANCHOR',len(idx),'coef',coef,'tolerance_A',tol,flush=True)
 return penalty
