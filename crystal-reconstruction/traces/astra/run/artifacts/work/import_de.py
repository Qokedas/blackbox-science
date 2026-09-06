import sys,os,json,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst.refinableobj import refpartype_scattpow_temperature,refpartype_scatt_occup
from obj_model import add_component,export_cif
sid=sys.argv[1];run=sys.argv[2];W='/app/work/'+sid;G=W+'/'+run;R=W+'/search_'+run;os.makedirs(R,exist_ok=True)
info=json.load(open(G+'/info.json'));objs=xml_cryst_file_load_all_object(info['base']);c=next(o for o in objs if o.GetClassName()=='Crystal');p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0)
for n,v in zip(['a','b','c','alpha','beta','gamma'],info['cell']):c.GetPar(n).SetHumanValue(v)
meta=json.load(open(G+'/model.json'));frac=np.load(G+'/best_frac.npy');models=[]
for j,(md,grp) in enumerate(zip(meta,info['groups'])):
 n=md['heavy'];f=frac[grp[0]:grp[0]+n];xyz=np.array([c.FractionalToOrthonormalCoords(*map(float,v)) for v in f]);m,newmd=add_component(c,md['smiles'],'m'+str(j),coords_override=np.asarray(md['coords'])[:n]);models.append(newmd)
 if m.GetClassName()=='Molecule':
  center=xyz.mean(axis=0);xyz-=center
  for i,v in enumerate(xyz):a=m.GetAtom(i);a.X,a.Y,a.Z=v
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*center)
 else:m.X,m.Y,m.Z=f[0]
c.GetOption(1).SetChoice(0);c.SetParIsFixed(refpartype_scattpow_temperature,True);c.SetParIsFixed(refpartype_scatt_occup,True);d.SetExtractionMode(False);p.GetOption(0).SetChoice(1);p.Prepare();p.FitScaleFactorForRw()
print('IMPORTED_DE',sid,run,'Rw',p.GetRw(),'Chi2',p.GetChi2(),flush=True);json.dump(models,open(R+'/model.json','w'),indent=1);export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');json.dump({'Rw':p.GetRw()},open(R+'/best.json','w'))
