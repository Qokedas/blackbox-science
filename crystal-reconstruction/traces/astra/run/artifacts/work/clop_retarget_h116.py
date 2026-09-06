import os,json,numpy as np
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
W='/app/work/X3f4781b';out=W+'/search_chemH116';os.makedirs(out,exist_ok=True)
md=json.load(open(W+'/search_tight115/model.json'));obs=xml_cryst_file_load_all_object(W+'/refined_tight115.xml');c=next(o for o in obs if o.GetClassName()=='Crystal');n=0
for i,rec in enumerate(md):
 m=c.GetScatterer(i)
 if m.GetClassName()!='Molecule':continue
 r=Chem.AddHs(Chem.MolFromSmiles(rec['smiles']))
 assert m.GetNbAtoms()==r.GetNumAtoms()
 lookup={m.GetAtom(j).GetName():j for j in range(m.GetNbAtoms())}
 for an in m.GetBondAngleList():
  ats=[an.GetAtom1(),an.GetAtom2(),an.GetAtom3()]
  if not any(a.GetScatteringPower().GetSymbol()=='H' for a in ats):continue
  mid=lookup[ats[1].GetName()];ra=r.GetAtomWithIdx(mid);hyb=ra.GetHybridization()
  if hyb==Chem.HybridizationType.SP3:target=np.deg2rad(109.4712206345)
  else:continue
  if abs(an.GetAngle0()-target)>.02: print([a.GetName() for a in ats],np.rad2deg(an.GetAngle0()),'->',np.rad2deg(target))
  an.SetAngle0(target);an.SetAngleSigma(np.deg2rad(2.));an.SetAngleDelta(np.deg2rad(2.));n+=1
json.dump(md,open(out+'/model.json','w'));xml_cryst_file_save_global(out+'/best.xml');print('RETARGETED',n)
