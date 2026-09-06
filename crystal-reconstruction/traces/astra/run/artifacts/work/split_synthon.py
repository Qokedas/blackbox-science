"""Release an artificial disconnected synthon into independent native fragments.
Preserves exact unwrapped heavy coordinates and the original geometric targets.
"""
import os,sys,json,subprocess,xml.etree.ElementTree as ET,numpy as np
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif
sid,run,tag=sys.argv[1:4];W='/app/work/'+sid;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True);src=W+'/refined_'+run+'.xml';mods=json.load(open(W+'/search_'+run+'/model.json'))
subprocess.run([sys.executable,'/app/work/extract_molecule_coords.py',src,R+'/source_coords.json'],check=True);sc=json.load(open(R+'/source_coords.json'))
tree=ET.parse(src)
for cr in tree.getroot().findall('Crystal'):
 for el in list(cr):
  if el.tag in ['Molecule','Atom','ZScatterer']:cr.remove(el)
tree.write(R+'/empty.xml');objs=xml_cryst_file_load_all_object(R+'/empty.xml');c=next(o for o in objs if o.GetClassName()=='Crystal');p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);newmods=[]
for mi,md in enumerate(mods):
 xyz=np.asarray(sc[mi]['cartesian']);ideal=np.asarray(md.get('restraint_coords',md['rdkit_coords']));off=0
 for sm in md['smiles'].split('.'):
  n=Chem.MolFromSmiles(sm).GetNumAtoms();x=xyz[off:off+n].copy();y=ideal[off:off+n].copy();off+=n;m,nmd=add_component(c,sm,'m'+str(len(newmods)),coords_override=y);ct=x.mean(0)
  for i,v in enumerate(x-ct):a=m.GetAtom(i);a.X,a.Y,a.Z=v
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*ct);newmods.append(nmd)
d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();print('SPLIT_SYNTHON',sid,run,'Rw',p.GetRw(),flush=True)
json.dump(newmods,open(R+'/model.json','w'),indent=1);export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml')
