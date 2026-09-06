"""Expand a molecular ObjCryst model into P1 while retaining heavy connectivity.
Creates a diagnostic, not an automatic submission. Every symmetry image is a
whole independent molecule; improper operations also transform restraint targets.
"""
import sys,os,json,numpy as np,gemmi
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif,recenter_molecules
sid,src,model_path,tag=sys.argv[1:5];W='/app/work/'+sid;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
objs=xml_cryst_file_load_all_object(src);c=next(o for o in objs if o.GetClassName()=='Crystal');p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=next(p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternDiffraction')
mods=json.load(open(model_path));sg=gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName());mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())]
mat=np.array([c.FractionalToOrthonormalCoords(*v) for v in np.eye(3)]);inv=np.linalg.inv(mat);images=[]
for op in sg.operations():
 rot=np.array(op.rot,dtype=float)/op.DEN;trans=np.array(op.tran,dtype=float)/op.DEN
 cartrot=inv@rot.T@mat
 for m,md in zip(mols,mods):
  n=Chem.MolFromSmiles(md['smiles']).GetNumHeavyAtoms();sc=list(m.GetScatteringComponentList());f=np.array([[a.X,a.Y,a.Z] for a in sc[:n]])
  target=(f@rot.T+trans)@mat
  ideal=np.array(md.get('restraint_coords',md.get('rdkit_coords',np.zeros((n,3)))))@cartrot
  images.append((md['smiles'],target,ideal))
for m in mols:c.RemoveScatterer(m)
c.ChangeSpaceGroup('P 1');newmods=[]
for i,(smiles,xyz,ideal) in enumerate(images):
 m,md=add_component(c,smiles,'p1_m'+str(i),coords_override=ideal)
 if m.GetClassName()=='Molecule':
  cen=xyz.mean(0);local=xyz-cen
  for j,v in enumerate(local):a=m.GetAtom(j);a.X,a.Y,a.Z=map(float,v)
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*map(float,cen))
 else:m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*map(float,xyz[0]))
 newmods.append(md)
c.GetOption(1).SetChoice(0);d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();recenter_molecules(c)
json.dump(newmods,open(R+'/model.json','w'),indent=1);xml_cryst_file_save_global(R+'/best.xml');export_cif(c,R+'/best.cif')
print('P1_EXPANDED',sid,'molecules',len(newmods),'Rw',p.GetRw(),flush=True)
