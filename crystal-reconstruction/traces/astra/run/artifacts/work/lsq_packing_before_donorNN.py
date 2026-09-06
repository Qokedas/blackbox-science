"""Heavy-atom steric lower bounds as genuine ObjCryst least-squares residuals.
Topology-preserving 1-2/1-3/1-4 pairs are excluded; 27 lattice images are
checked for all contacts.  Crystal anti-bump itself is not an LSQ function.
"""
import ctypes,os,numpy as np,gemmi
from rdkit import Chem
from rdkit.Chem import Lipinski
lib=ctypes.CDLL('/app/work/liblsq_packing.so')
lib.packing_attach.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_long]+[ctypes.c_void_p]*6
lib.packing_attach.restype=ctypes.c_void_p
lib.packing_cost.argtypes=[ctypes.c_void_p];lib.packing_cost.restype=ctypes.c_double
lib.packing_detach.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
def attach_packing(p,c,mods,sigma=None):
 sigma=float(os.getenv('PACKING_SIGMA','.01')) if sigma is None else sigma
 els=[];charges=[];carbonyl=[];acceptor0=[];index=[];groups=[];local=[];dm=[];off=0
 for k,md in enumerate(mods):
  m=c.GetScatterer(k);r=Chem.MolFromSmiles(md['smiles']);n=r.GetNumAtoms();acc={a[0] for a in Lipinski._HAcceptors(r)};dm.append(Chem.GetDistanceMatrix(r))
  for i,a in enumerate(r.GetAtoms()):
   els.append(a.GetSymbol());charges.append(a.GetFormalCharge());acceptor0.append(i in acc and a.GetSymbol() in ['N','O'] and a.GetTotalNumHs()==0);carbonyl.append(a.GetSymbol()=='O' and any(b.GetBondTypeAsDouble()==2 and b.GetOtherAtom(a).GetSymbol()=='C' for b in a.GetBonds()));index.append(off+i);groups.append(k);local.append(i)
  off+=len(list(m.GetScatteringComponentList()))
 radii={'C':1.48,'N':1.35,'O':1.28,'F':1.32,'S':1.55,'P':1.52,'Cl':1.58,'Br':1.67,'I':1.78}
 ii=[];jj=[];rots=[];trans=[];limits=[];weights=[];sg=gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName());N=len(index)
 for op in sg.operations():
  R=np.asarray(op.rot)/op.DEN;T=np.asarray(op.tran)/op.DEN;ident=np.allclose(R,np.eye(3)) and np.allclose(T%1,0)
  for i in range(N):
   for j in range(N):
    if ident and (i>=j or (groups[i]==groups[j] and dm[groups[i]][local[i],local[j]]<=3)):continue
    limit=radii.get(els[i],1.4)+radii.get(els[j],1.4)
    if els[i] in ['N','O'] and els[j] in ['N','O']:limit-=.10
    if els[i]==els[j]=='N' and charges[i]>0 and charges[j]>0:limit=max(limit,float(os.getenv('CHARGED_N_MIN','0')))
    if (els[i]=='N' and charges[i]>0 and els[j]=='O') or (els[j]=='N' and charges[j]>0 and els[i]=='O'):limit=max(limit,float(os.getenv('CHARGED_NO_MIN','0')))
    if carbonyl[i] and carbonyl[j]:limit=max(limit,float(os.getenv('CARBONYL_OO_MIN','0')))
    if acceptor0[i] and acceptor0[j]:limit=max(limit,float(os.getenv('ACCEPTOR_NO_MIN','0')))
    ii.append(index[i]);jj.append(index[j]);rots.append(R);trans.append(T);limits.append(limit);weights.append((1. if ident else .5)/sigma**2)
 arrays=[np.ascontiguousarray(ii,dtype=np.int64),np.ascontiguousarray(jj,dtype=np.int64),np.ascontiguousarray(rots,dtype=np.float64),np.ascontiguousarray(trans,dtype=np.float64),np.ascontiguousarray(limits,dtype=np.float64),np.ascontiguousarray(weights,dtype=np.float64)]
 obj=lib.packing_attach(p.int_ptr(),c.int_ptr(),len(ii),*[a.ctypes.data for a in arrays])
 if not obj:raise RuntimeError('Packing attachment failed')
 print('LSQ_PACKING',N,'atoms',len(ii),'terms','sigma',sigma,'cost',lib.packing_cost(obj),flush=True)
 return obj

def cost(obj):return lib.packing_cost(obj)
def detach(p,obj):lib.packing_detach(p.int_ptr(),obj)
