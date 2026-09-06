import sys,os,json,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst.refinableobj import refpartype_scattpow_temperature,refpartype_scatt_occup
from obj_model import add_component,export_cif
sid=sys.argv[1];run=sys.argv[2];W='/app/work/'+sid;G=W+'/gallop_'+run;R=W+'/search_g'+run;os.makedirs(R,exist_ok=True)
objs=xml_cryst_file_load_all_object(W+'/base.xml');c=[o for o in objs if o.GetClassName()=='Crystal'][0];p=[o for o in objs if o.GetClassName()=='PowderPattern'][0];d=p.GetPowderPatternComponent(0)
meta=json.load(open(G+'/model.json'));frac=np.load(G+'/best_frac.npy');offset=0;models=[]
for j,md in enumerate(meta):
 n=len(md['order']);xyz=np.zeros((n,3));f=frac[offset:offset+n];offset+=n
 for i,old in enumerate(md['order']):xyz[old]=c.FractionalToOrthonormalCoords(*map(float,f[i]))
 m,newmd=add_component(c,md['smiles'],'m'+str(j),coords_override=md['rdkit_coords'])
 if m.GetClassName()=='Molecule':
  center=xyz.mean(axis=0);xyz-=center
  for i,v in enumerate(xyz):a=m.GetAtom(i);a.X,a.Y,a.Z=v
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*center)
 else:m.X,m.Y,m.Z=map(float,f[0])
 models.append(newmd)
c.GetOption(1).SetChoice(0);c.SetParIsFixed(refpartype_scattpow_temperature,True);c.SetParIsFixed(refpartype_scatt_occup,True)
d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();print('IMPORTED',sid,run,'Rw',p.GetRw(),'Chi2',p.GetChi2(),flush=True)
json.dump(models,open(R+'/model.json','w'),indent=1);export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');json.dump({'Rw':p.GetRw()},open(R+'/best.json','w'))
