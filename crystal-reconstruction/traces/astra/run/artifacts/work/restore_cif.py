import sys,os,json,numpy as np,gemmi
from rdkit import Chem
from pymatgen.core import Lattice
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import export_cif,recenter_molecules
sid=sys.argv[1];run=sys.argv[2];W='/app/work/'+sid;src=sys.argv[3] if len(sys.argv)>3 else W+'/refined_'+run+'.xml';cif=sys.argv[4] if len(sys.argv)>4 else W+'/refined_'+run+'.cif';out=sys.argv[5] if len(sys.argv)>5 else W+'/restored_'+run+'.xml'
objs=xml_cryst_file_load_all_object(src);c=[x for x in objs if x.GetClassName()=='Crystal'][0];p=[x for x in objs if x.GetClassName()=='PowderPattern'][0]
b=gemmi.cif.read_file(cif).sole_block();rows=b.find(['_atom_site_type_symbol','_atom_site_fract_x','_atom_site_fract_y','_atom_site_fract_z']);frac=np.array([[float(row[j]) for j in range(1,4)] for row in rows]);els=[row[0] for row in rows]
cp=[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']];L=Lattice.from_parameters(*cp);models=json.load(open(W+'/search_'+run+'/model.json'));offset=0
for im,md in enumerate(models):
 m=c.GetScatterer(im);n=m.GetNbAtoms() if m.GetClassName()=='Molecule' else 1;f=frac[offset:offset+n];offset+=n
 if n==1:m.X,m.Y,m.Z=f[0];continue
 r=Chem.MolFromSmiles(md['smiles'])
 if n>r.GetNumAtoms():r=Chem.AddHs(r)
 assert n==r.GetNumAtoms()
 coords=f.copy();seen={0};queue=[0]
 while queue:
  i=queue.pop()
  for a in r.GetAtomWithIdx(i).GetNeighbors():
   j=a.GetIdx()
   if j in seen:continue
   ds,imv=L.get_distance_and_image(coords[i],f[j]);coords[j]=f[j]+imv;seen.add(j);queue.append(j)
 xyz=np.array([c.FractionalToOrthonormalCoords(*v) for v in coords]);center=xyz.mean(0)
 for i,v in enumerate(xyz-center):a=m.GetAtom(i);a.X,a.Y,a.Z=v
 m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*center);m.GetOption(0).SetChoice(2)
p.Prepare();p.FitScaleFactorForRw();print('RESTORED_CIF',sid,p.GetRw(),p.GetChi2(),flush=True)
recenter_molecules(c);xml_cryst_file_save_global(out)
