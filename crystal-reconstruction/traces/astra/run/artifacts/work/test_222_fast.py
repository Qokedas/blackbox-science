import torch,numpy as np,gemmi,sys
from gallop import intensities
@torch.jit.script
def general_222(fr:torch.Tensor,hkl:torch.Tensor,prefix:torch.Tensor,tr:torch.Tensor,chars:torch.Tensor,masktab:torch.Tensor):
 p=6.283185307179586
 phases=torch.cos(p*(hkl.T@tr.T))
 coef=phases@chars
 mask=masktab[torch.argmax(torch.abs(coef),dim=1)]
 a=p*torch.einsum('i,nj->nij',hkl[0],fr[:,:,0])
 b=p*torch.einsum('i,nj->nij',hkl[1],fr[:,:,1])
 c=p*torch.einsum('i,nj->nij',hkl[2],fr[:,:,2])
 sa,ca=torch.sin(a),torch.cos(a)
 sb,cb=torch.sin(b),torch.cos(b)
 sc,cc=torch.sin(c),torch.cos(c)
 re=(prefix[None,:,:]*torch.where(mask[None,:,0,None],sa,ca)*torch.where(mask[None,:,1,None],sb,cb)*torch.where(mask[None,:,2,None],sc,cc)).sum(2)
 im=(prefix[None,:,:]*torch.where(mask[None,:,0,None],ca,sa)*torch.where(mask[None,:,1,None],cb,sb)*torch.where(mask[None,:,2,None],cc,sc)).sum(2)
 return 16*(re*re+im*im)
def constants(sg):
 ops=list(sg.operations());r=np.asarray([np.asarray(o.rot)/o.DEN for o in ops]);tr=np.asarray([np.asarray(o.tran)/o.DEN for o in ops]);signs=np.diagonal(r,axis1=1,axis2=2);masktab=np.asarray([[0,0,0],[1,1,0],[1,0,1],[0,1,1]],dtype=bool);chars=np.asarray([[np.prod(s[m]) for m in masktab] for s in signs]);return torch.tensor(tr,dtype=torch.float32),torch.tensor(chars,dtype=torch.float32),torch.tensor(masktab)
if __name__=='__main__':
 for name in ['P 2 2 2','P 2 2 21','P 2 21 21','P 21 21 2','P 21 21 21']:
  sg=gemmi.find_spacegroup_by_name(name);tr,ch,mt=constants(sg);h=torch.randint(-10,10,(3,400)).float();fr=torch.rand(5,19,3);pr=torch.rand(400,19);ones=torch.ones(5,19,1);aff=[]
  for op in sg.operations():
   m=np.eye(4);m[:3,:3]=np.asarray(op.rot)/op.DEN;m[:3,3]=np.asarray(op.tran)/op.DEN;aff.append(m)
  aff=torch.tensor(np.asarray(aff),dtype=torch.float32);expanded=intensities.get_symmetry_equivalent_points(fr,ones,aff);ref=intensities.intensities_from_full_cell_contents(expanded,h,pr.repeat(1,4),False);val=general_222(fr,h,pr,tr,ch,mt);err=float((val-ref).abs().max()/ref.max());print(name,err)
  assert err<1e-4
