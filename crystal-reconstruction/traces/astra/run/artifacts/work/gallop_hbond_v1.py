"""Optional soft donor/acceptor proximity prior for ionic and H-bonded solids.
This does not prescribe a particular intermolecular synthon: each donor may
choose any chemically possible acceptor, including a distant topological
intramolecular acceptor. Steric lower bounds are supplied separately.
"""
import os,json,itertools,numpy as np,torch
from rdkit import Chem
from rdkit.Chem import Lipinski
from gallop import chi2,zm_to_cart

def enable_hbonds(s,model_path,coefficient=None):
 mods=json.load(open(model_path));donors=[];donor_counts={};acceptors=[];groups=[];ids=[];dm=[];off=0;els=[]
 for k,m in enumerate(mods):
  r=Chem.MolFromSmiles(m['smiles']);order=m['order'];inv={j:i for i,j in enumerate(order)};dm.append(Chem.GetDistanceMatrix(r))
  for a in Lipinski._HDonors(r):
   ix=off+inv[a[0]];donors.append(ix);atom=r.GetAtomWithIdx(a[0]);donor_counts[ix]=min(3,atom.GetTotalNumHs()) if os.getenv('HBOND_MULTIPLE','0')=='1' else 1
  for a in Lipinski._HAcceptors(r):acceptors.append(off+inv[a[0]])
  for a in r.GetAtoms():
   if a.GetSymbol() in ['Cl','Br'] and a.GetFormalCharge()<0:acceptors.append(off+inv[a.GetIdx()])
  groups.extend([k]*len(order));ids.extend(order);els.extend([r.GetAtomWithIdx(i).GetSymbol() for i in order]);off+=len(order)
 if not donors or not acceptors:return
 LM=torch.tensor(s.lattice.matrix,dtype=torch.float32);shifts=torch.tensor(np.array(list(itertools.product([-1,0,1],repeat=3)))@s.lattice.matrix,dtype=torch.float32);ss=(shifts*shifts).sum(-1)
 tensors=[]
 for i in donors:
  jj=[];rt=[];tr=[];target=[]
  for op in s.space_group.symmetry_ops:
   R=op.rotation_matrix;T=op.translation_vector;ident=np.allclose(R,np.eye(3)) and np.allclose(T%1,0)
   for j in acceptors:
    if ident and groups[i]==groups[j] and dm[groups[i]][ids[i],ids[j]]<=3:continue
    jj.append(j);rt.append(R);tr.append(T);target.append(3.25 if els[j] in ['Cl','Br'] else 3.05)
  tensors.append((i,torch.tensor(jj,dtype=torch.long),torch.tensor(np.array(rt),dtype=torch.float32),torch.tensor(np.array(tr),dtype=torch.float32),torch.tensor(target,dtype=torch.float32)))
 cf=float(coefficient if coefficient is not None else os.getenv('HBOND_COEFF','20'))
 def penalty(fr):
  val=torch.zeros(len(fr),device=fr.device)
  for i,jj,rr,tt,target in tensors:
   right=torch.einsum('nki,kji->nkj',fr[:,jj,:],rr)+tt;dd=fr[:,i,None]-right;dd=dd-torch.round(dd).detach();cart=dd@LM
   with torch.no_grad():corr=shifts[(2*(cart.detach()@shifts.T)+ss).argmin(-1)]
   dist=torch.sqrt(((cart+corr)**2).sum(-1)+1e-8);near=torch.topk(dist-target,k=min(donor_counts[i],len(jj)),dim=-1,largest=False).values;val+=(torch.clamp(near,min=0)**2).sum(-1)
  return cf*val
 old=chi2.get_chi_2
 def calc(zm,int_tensors,chisqd_tensors,profile=None):
  fr=zm_to_cart.get_asymmetric_coords(**zm)
  return old(zm,int_tensors,chisqd_tensors,profile=profile)+penalty(fr)
 chi2.get_chi_2=calc;s.hbond_penalty=penalty
 print('HBOND_PRIOR',len(donors),'donors',len(acceptors),'acceptors','coefficient',cf,flush=True)
 return penalty
