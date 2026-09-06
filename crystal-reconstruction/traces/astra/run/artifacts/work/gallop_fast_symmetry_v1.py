"""Analytical structure factors for two otherwise generic settings.
Algebraically identical to explicit symmetry expansion. Checked at random
fractional coordinates before being installed; no crystallographic approximation.
"""
import numpy as np,torch,gemmi
from gallop import intensities,chi2,zm_to_cart

@torch.jit.script
def monoclinic_centred_inversion(fr:torch.Tensor,hkl:torch.Tensor,prefix:torch.Tensor,t:torch.Tensor):
 p=6.283185307179586
 halfshift=(hkl*t[:,None]).sum(0)/2
 xz=p*(torch.einsum('i,nj->nij',hkl[0],fr[:,:,0])+torch.einsum('i,nj->nij',hkl[2],fr[:,:,2])+halfshift[None,:,None])
 y=p*(torch.einsum('i,nj->nij',hkl[1],fr[:,:,1])-halfshift[None,:,None])
 amp=4*torch.cos(xz)*torch.cos(y)
 return (amp*prefix[None,:,:]).sum(2)**2

@torch.jit.script
def orthorhombic_2221(fr:torch.Tensor,hkl:torch.Tensor,prefix:torch.Tensor):
 p=6.283185307179586
 a=p*torch.einsum('i,nj->nij',hkl[0],fr[:,:,0])
 b=p*(torch.einsum('i,nj->nij',hkl[1],fr[:,:,1])+hkl[2][None,:,None]/4)
 c=p*(torch.einsum('i,nj->nij',hkl[2],fr[:,:,2])-hkl[2][None,:,None]/4)
 re=(4*torch.cos(a)*torch.cos(b)*torch.cos(c)*prefix[None,:,:]).sum(2)
 im=(-4*torch.sin(a)*torch.sin(b)*torch.sin(c)*prefix[None,:,:]).sum(2)
 return re**2+im**2

def enable_fast_symmetry(s):
 sg=gemmi.find_spacegroup_by_name(s.space_group.symbol);kind=None;tr=None
 if sg.number==14 and sg.xhm()!=gemmi.find_spacegroup_by_number(14).xhm():
  for op in sg.operations():
   r=np.array(op.rot)/op.DEN;t=np.array(op.tran)/op.DEN
   if np.allclose(r,np.diag([-1,1,-1])):tr=torch.tensor(t,dtype=torch.float32)
  inversion=any(np.allclose(np.array(op.rot)/op.DEN,-np.eye(3)) and np.allclose((np.array(op.tran)/op.DEN)%1,0) for op in sg.operations())
  if inversion and tr is not None:kind='mono14'
 if sg.xhm()=='P 2 2 21':kind='2221'
 if kind is None:return False
 old=intensities.calculate_intensities
 def fun(asymmetric_frac_coords,hkl,intensity_calc_prefix_fs,intensity_calc_prefix_fs_asymmetric,nsamples_ones,affine_matrices,centrosymmetric,space_group_number):
  if kind=='mono14':return monoclinic_centred_inversion(asymmetric_frac_coords,hkl,intensity_calc_prefix_fs_asymmetric,tr)
  return orthorhombic_2221(asymmetric_frac_coords,hkl,intensity_calc_prefix_fs_asymmetric)
 # Independent random geometry test against explicit symmetry expansion.
 h=torch.tensor(np.asarray(s.hkl[:min(250,len(s.hkl))]).T,dtype=torch.float32);fr=torch.rand(3,9,3);ones=torch.ones(3,9,1);aff=torch.tensor(np.asarray(s.affine_matrices),dtype=torch.float32);pr=torch.rand(h.shape[1],9);fullpr=pr.repeat(1,len(sg.operations()))
 expanded=intensities.get_symmetry_equivalent_points(fr,ones,aff);ref=intensities.intensities_from_full_cell_contents(expanded,h,fullpr,sg.is_centrosymmetric());val=fun(fr,h,fullpr,pr,ones,aff,sg.is_centrosymmetric(),s.sg_number)
 err=float((val-ref).abs().max()/ref.max())
 if err>1e-4:raise RuntimeError('Fast-symmetry validation failed '+str(err))
 intensities.calculate_intensities=fun
 # The unmodified GALLOP chi2 function is TorchScript and binds its own copy of
 # the old intensity function. Supply an equivalent Python dispatch as well.
 def calc(zm,int_tensors,chisqd_tensors,profile=None):
  fr=zm_to_cart.get_asymmetric_coords(**zm);f=fun(fr,**int_tensors)
  return chi2.calc_int_chisqd(f,**chisqd_tensors) if profile is None else chi2.calc_prof_chisqd(f,**profile)
 chi2.get_chi_2=calc
 print('FAST_SYMMETRY',sg.xhm(),kind,'max_relative_error',err,flush=True)
 return True
