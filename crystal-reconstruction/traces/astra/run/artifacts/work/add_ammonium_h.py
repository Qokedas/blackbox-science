"""Rebuild a native model with explicit tetrahedral NH4 groups.
Heavy-atom positions are retained exactly; the added H atoms are a profile-model
correction, not measured hydrogen coordinates. Output is a refinement seed.
"""
import sys,os,json,numpy as np,itertools
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst.molecule import Molecule
from pyobjcryst.scatteringpower import ScatteringPowerAtom
from obj_model import add_component,export_cif
sid,run,tag=sys.argv[1:4];W='/app/work/'+sid;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
O=xml_cryst_file_load_all_object(sys.argv[4] if len(sys.argv)>4 else W+'/refined_'+run+'.xml');c=next(x for x in O if x.GetClassName()=='Crystal');p=next(x for x in O if x.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);mods=json.load(open(W+'/search_'+run+'/model.json'))
old=[]
for i,md in enumerate(mods):
 m=c.GetScatterer(i);n=Chem.MolFromSmiles(md['smiles']).GetNumAtoms();sc=list(m.GetScatteringComponentList());xyz=np.array([c.FractionalToOrthonormalCoords(a.X,a.Y,a.Z) for a in sc[:n]]);old.append((md,xyz,m))
for md,xyz,m in old:c.RemoveScatterer(m)
new=[]
try:hs=c.GetScatteringPower('H')
except:hs=ScatteringPowerAtom('H','H',4.);c.AddScatteringPower(hs)
for im,(md,xyz,prev) in enumerate(old):
 r=Chem.MolFromSmiles(md['smiles']);n=len(xyz);ammonium=n==1 and r.GetAtomWithIdx(0).GetSymbol()=='N' and r.GetAtomWithIdx(0).GetTotalNumHs()==4
 if ammonium:
  try:ns=c.GetScatteringPower('ammonium_N')
  except:ns=ScatteringPowerAtom('ammonium_N','N',3.);c.AddScatteringPower(ns)
  m=Molecule(c,'NH4_'+str(im));ats=[m.AddAtom(0.,0.,0.,ns,'N'+str(im),False)]
  vs=np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]],float)*1.03/np.sqrt(3)
  for ih,v in enumerate(vs):ats.append(m.AddAtom(*v,hs,'H'+str(im)+'_'+str(ih),False))
  for h in ats[1:]:m.AddBond(ats[0],h,1.03,.015,.015,1.,False)
  for h,h2 in itertools.combinations(ats[1:],2):m.AddBondAngle(h,ats[0],h2,np.arccos(-1./3),np.deg2rad(1),np.deg2rad(1),False)
  m.GetOption(0).SetChoice(2);m.GetOption(1).SetChoice(1);m.GetOption(2).SetChoice(1);m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*map(float,xyz[0]));c.AddScatterer(m);nm=dict(md,rdkit_coords=[[0.,0.,0.]])
 else:
  ideal=md.get('restraint_coords',md.get('rdkit_coords',[[0.,0.,0.]]));m,nm=add_component(c,md['smiles'],'m'+str(im),coords_override=ideal)
  if m.GetClassName()=='Molecule':
   ctr=xyz.mean(0)
   for j,v in enumerate(xyz-ctr):a=m.GetAtom(j);a.X,a.Y,a.Z=map(float,v)
   m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*map(float,ctr))
  else:m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*map(float,xyz[0]))
 new.append(nm)
 for j in range(n):
  sc=list(m.GetScatteringComponentList());q=sc[j];a=np.array(c.FractionalToOrthonormalCoords(q.X,q.Y,q.Z));assert np.linalg.norm(a-xyz[j])<.001,(im,j,a,xyz[j])
d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();print('EXPLICIT_AMMONIUM_SEED',p.GetRw(),flush=True)
json.dump(new,open(R+'/model.json','w'),indent=1);xml_cryst_file_save_global(R+'/best.xml');export_cif(c,R+'/best.cif')
