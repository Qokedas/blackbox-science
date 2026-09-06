"""Diagnostic orthorhombic P 2 21 21 -> P 1 21 1 subgroup expansion.
Keep heavy coordinates exactly, including both independent molecules, and
shift origin by -c/4 to put the b-axis screw in its conventional setting.
"""
import os,sys,json,numpy as np,gemmi
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif,recenter_molecules
sid,src,modelp,tag=sys.argv[1:5];W='/app/work/'+sid;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
O=xml_cryst_file_load_all_object(src);c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);md=json.load(open(modelp));assert gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName()).xhm()=='P 2 21 21'
mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())];M=np.array([c.FractionalToOrthonormalCoords(*v) for v in np.eye(3)]);inv=np.linalg.inv(M);images=[]
for rot in [np.eye(3),np.diag([1.,-1.,-1.])]:
 for m,mo in zip(mols,md):
  n=Chem.MolFromSmiles(mo['smiles']).GetNumHeavyAtoms();sc=list(m.GetScatteringComponentList())[:n];fc=np.array([[a.X,a.Y,a.Z] for a in sc]);dest=(fc@rot.T+np.array([0.,0.,-.25]))@M;ideal=np.array(mo.get('restraint_coords',mo.get('rdkit_coords',np.zeros((n,3)))))@(inv@rot.T@M);images.append((mo['smiles'],dest,ideal))
for m in mols:c.RemoveScatterer(m)
c.ChangeSpaceGroup('P 1 21 1');new=[]
for i,(smiles,dest,ideal) in enumerate(images):
 m,mo=add_component(c,smiles,'sub_m'+str(i),coords_override=ideal.copy());ctr=dest.mean(0)
 if m.GetClassName()=='Molecule':
  for j,v in enumerate(dest-ctr):a=m.GetAtom(j);a.X,a.Y,a.Z=map(float,v)
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.
 m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*ctr);new.append(mo)
 actual=np.array([c.FractionalToOrthonormalCoords(a.X,a.Y,a.Z) for a in list(m.GetScatteringComponentList())[:len(dest)]]);assert np.max(np.abs(((actual-dest)@inv+.5)%1-.5))<1e-6
c.GetOption(1).SetChoice(0);d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();recenter_molecules(c);json.dump(new,open(R+'/model.json','w'),indent=1);xml_cryst_file_save_global(R+'/best.xml');export_cif(c,R+'/best.cif');print('SUBGROUP',sid,'heavy-only initial Rw',p.GetRw(),flush=True)
