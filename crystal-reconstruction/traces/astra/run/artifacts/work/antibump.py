import numpy as np,itertools,io,re
from rdkit import Chem

def add_antibump(c,models,full=False,scale=10.):
 types=[];pt=Chem.GetPeriodicTable()
 for ic,md in enumerate(models):
  m=c.GetScatterer(ic);r=Chem.MolFromSmiles(md['smiles'])
  if m.GetClassName()=='Atom':types.append((m.GetScatteringPower(),ic,0,None));continue
  if m.GetNbAtoms()>r.GetNumAtoms():r=Chem.AddHs(r)
  mat=Chem.GetDistanceMatrix(r)
  for ia in range(m.GetNbAtoms()):
   a=m.GetAtom(ia);sp=a.GetScatteringPower()
   if sp.GetSymbol()!='H':types.append((sp,ic,ia,mat))
 for i,(s,ic,ia,dm) in enumerate(types):
  for t,jc,ja,dmat in types[i:]:
   e1=s.GetSymbol();e2=t.GetSymbol()
   if e1=='H' or e2=='H':continue
   r0=pt.GetRvdw(e1)+pt.GetRvdw(e2)-.7
   r0=max(2.35,r0)
   if full and ic==jc and dm is not None and ia!=ja:
    if dm[ia,ja]<=2:
     xyz=np.array(models[ic]['rdkit_coords']);r0=min(r0,np.linalg.norm(xyz[ia]-xyz[ja])*.86)
   elif not full:
    if not (s.GetName().startswith('ion_') or t.GetName().startswith('ion_')):continue
   c.SetBumpMergeDistance(s,t,float(r0),False)
 # Safely adjust the existing object through a compiled C++ bridge, without XMLInput.
 from obj_bridge import set_bump_scale
 set_bump_scale(c,scale)
 print('ANTIBUMP',len(c.GetBumpMergeParList()),'Scale',scale,'Initial cost',c.GetBumpMergeCost(),flush=True)
