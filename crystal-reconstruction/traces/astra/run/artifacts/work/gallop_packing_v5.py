import os,json,itertools,numpy as np,torch
from rdkit import Chem
from gallop import chi2,zm_to_cart,intensities

def enable_packing(s,model_path,coefficient=None):
 """Differentiable minimum-image heavy-atom steric screening in an ASU.
 Excludes fixed-topology 1-2/1-3/1-4 intramolecular contacts. The cutoff is
 deliberately softer than a van der Waals sum, allowing hydrogen bonds.
 """
 mods=json.load(open(model_path));n=sum(len(m['order']) for m in mods);els=[];charges=[];carbonyl=[];exclude=np.eye(n,dtype=bool);off=0
 for m in mods:
  r=Chem.MolFromSmiles(m['smiles']);order=m['order'];N=len(order);dm=Chem.GetDistanceMatrix(r)[np.ix_(order,order)];exclude[off:off+N,off:off+N]=(dm<=3);els.extend([r.GetAtomWithIdx(i).GetSymbol() for i in order]);charges.extend([r.GetAtomWithIdx(i).GetFormalCharge() for i in order]);carbonyl.extend([r.GetAtomWithIdx(i).GetSymbol()=='O' and any(b.GetBondTypeAsDouble()==2 and b.GetOtherAtom(r.GetAtomWithIdx(i)).GetSymbol()=='C' for b in r.GetAtomWithIdx(i).GetBonds()) for i in order]);off+=N
 radii={'C':1.48,'N':1.35,'O':1.28,'F':1.32,'S':1.55,'P':1.52,'Cl':1.58,'Br':1.67,'I':1.78}
 ii=[];jj=[];rr=[];tr=[];lim=[];weights=[];all_r=[];all_t=[]
 for oi,op in enumerate(s.space_group.symmetry_ops):
  rot=op.rotation_matrix;trans=op.translation_vector;all_r.append(rot);all_t.append(trans);ident=np.allclose(rot,np.eye(3)) and np.allclose(trans%1,0)
  for i in range(n):
   for j in range(n):
    if ident and (i>=j or exclude[i,j]):continue
    limit=radii.get(els[i],1.4)+radii.get(els[j],1.4)
    if set([els[i],els[j]])<=set(['N','O']):limit-=.10
    if els[i]==els[j]=='N' and charges[i]>0 and charges[j]>0:limit=max(limit,float(os.getenv('CHARGED_N_MIN','0')))
    if carbonyl[i] and carbonyl[j]:limit=max(limit,float(os.getenv('CARBONYL_OO_MIN','0')))
    ii.append(i);jj.append(oi*n+j);lim.append(limit);weights.append(1 if ident else .5)
 ii=torch.tensor(ii,dtype=torch.long);jj=torch.tensor(jj,dtype=torch.long);rr=torch.tensor(np.array(all_r),dtype=torch.float32);tr=torch.tensor(np.array(all_t),dtype=torch.float32);lim=torch.tensor(lim,dtype=torch.float32);weights=torch.tensor(weights,dtype=torch.float32);lm=torch.tensor(s.lattice.matrix,dtype=torch.float32)
 cf=float(coefficient if coefficient is not None else os.environ.get('BUMP_COEFF','50'))
 exact=os.environ.get('EXACT_BUMP_IMAGES','1' if n<30 and (min(s.lattice.angles)<75 or max(s.lattice.angles)>105) else '0')=='1'
 shifts=torch.tensor(np.array(list(itertools.product([-1,0,1],repeat=3)))@s.lattice.matrix,dtype=torch.float32);shift2=(shifts*shifts).sum(-1)
 diagonal=bool(np.allclose(np.array(all_r),np.array([np.diag(np.diag(r)) for r in all_r])))
 rdiag=torch.diagonal(rr,dim1=1,dim2=2)
 active_only=os.getenv('PACKING_ACTIVE_ONLY','1')=='1'
 def penalty(fr):
  # Distances outside the steric support have identically zero derivatives.
  # Identify their support without building a backward graph, then only retain
  # active contacts in the differentiated expression. This is exactly the
  # same piecewise-quadratic objective, not a neighbour-list approximation.
  if active_only:
   with torch.no_grad():
    if diagonal:full=fr[:,None,:,:]*rdiag[None,:,None,:]+tr[None,:,None,:]
    else:full=torch.einsum('nki,oji->nokj',fr,rr)+tr[None,:,None,:]
    dd=fr[:,ii,:]-full.reshape(len(fr),-1,3)[:,jj,:];rnd=torch.round(dd);cart=(dd-rnd)@lm
    if exact:
     sid=(2*(cart@shifts.T)+shift2).argmin(-1);correction=shifts[sid];cart+=correction
    use=((cart*cart).sum(-1)<lim*lim).nonzero(as_tuple=False)
    ib=use[:,0];ip=use[:,1];ja=jj[ip]%n;jo=jj[ip]//n;imcorr=rnd[ib,ip]
    if exact:cc=correction[ib,ip]
   if len(use)==0:return fr.sum(dim=(1,2))*0
   if diagonal:right=fr[ib,ja]*rdiag[jo]+tr[jo]
   else:right=torch.einsum('ki,kji->kj',fr[ib,ja],rr[jo])+tr[jo]
   cart=(fr[ib,ii[ip]]-right-imcorr)@lm
   if exact:cart=cart+cc
   dist=torch.sqrt((cart*cart).sum(-1)+1e-8)
   terms=cf*(torch.clamp(lim[ip]-dist,min=0)**2)*weights[ip]
   return torch.zeros(len(fr),dtype=fr.dtype,device=fr.device).index_add(0,ib,terms)
  if diagonal:full=fr[:,None,:,:]*rdiag[None,:,None,:]+tr[None,:,None,:]
  else:full=torch.einsum('nki,oji->nokj',fr,rr)+tr[None,:,None,:]
  right=full.reshape(len(fr),-1,3)[:,jj,:]
  delta=fr[:,ii,:]-right;delta=delta-torch.round(delta).detach();cart=delta@lm
  if exact:
   with torch.no_grad():
    sid=(2*(cart.detach()@shifts.T)+shift2).argmin(-1);correction=shifts[sid]
   cart=cart+correction
  dist=torch.sqrt((cart*cart).sum(-1)+1e-8)
  return cf*(torch.clamp(lim-dist,min=0)**2*weights).sum(-1)
 def calc(zm,int_tensors,chisqd_tensors,profile=None):
  fr=zm_to_cart.get_asymmetric_coords(**zm);f=intensities.calculate_intensities(fr,**int_tensors)
  val=chi2.calc_int_chisqd(f,**chisqd_tensors) if profile is None else chi2.calc_prof_chisqd(f,**profile)
  return val+penalty(fr)
 s.packing_penalty=penalty;s.diffraction_get_chi_2=chi2.get_chi_2;chi2.get_chi_2=calc
 print('PACKING_ENABLED',n,'atoms',len(ii),'pair terms','coefficient',cf,'active_only',active_only,flush=True)
 return penalty
