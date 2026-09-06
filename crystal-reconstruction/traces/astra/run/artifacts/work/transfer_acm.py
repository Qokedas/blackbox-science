"""An isostructural starting hypothesis for the two acemetacin/lactam cells.
No solution claim: preserve the acid pose and align only the lactam O=C-N group.
"""
import sys,os,json,subprocess,numpy as np,xml.etree.ElementTree as ET
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,make_rdkit,export_cif
from rdkit import Chem
source,target,run,tag=sys.argv[1:5];S='/app/work/'+source;W='/app/work/'+target;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
src=S+'/refined_'+run+'.xml';mods=json.load(open(S+'/search_'+run+'/model.json'))
subprocess.run([sys.executable,'/app/work/extract_molecule_coords.py',src,R+'/source_coords.json'],check=True);sc=json.load(open(R+'/source_coords.json'))
# The source may have a joined acid-lactam synthon. Split by supplied atom counts.
comp0=json.load(open('/app/data/instances/'+source+'/composition.json'))['components'];counts=[Chem.MolFromSmiles(x['smiles']).GetNumAtoms() for x in comp0]
if len(sc)==1:
 a=sc[0];sc=[];off=0
 for n in counts:
  sc.append({k:v[off:off+n] for k,v in a.items() if k in ['cartesian','fractional','elements']});off+=n
objs=xml_cryst_file_load_all_object(os.getenv('TRANSFER_BASE',W+'/base.xml'));c=next(o for o in objs if o.GetClassName()=='Crystal');p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0)
for m in [c.GetScatterer(i) for i in range(c.GetNbScatterer())]:c.RemoveScatterer(m)
comp=json.load(open('/app/data/instances/'+target+'/composition.json'))['components'];newmods=[]
for i,cm in enumerate(comp):
 oldN=counts[i];oldxyz=np.asarray(sc[i]['cartesian'])[:oldN];oldfrac=np.asarray(sc[i]['fractional'])[:oldN];ct=oldxyz.mean(0);dest=np.asarray(c.FractionalToOrthonormalCoords(*oldfrac.mean(0)))
 if i==0:
  assert cm['smiles']==comp0[0]['smiles'];ideal=np.asarray(mods[0].get('restraint_coords',mods[0]['rdkit_coords']))[:oldN];xyz=oldxyz-ct+dest
 else:
  q,ideal,_=make_rdkit(cm['smiles'],seed=233,nconf=40,conf_rank=int(os.getenv('CONF_RANK','0')));r=Chem.MolFromSmiles(comp0[i]['smiles']);pat=Chem.MolFromSmarts('[OX1]=[CX3][NX3]');i0=r.GetSubstructMatch(pat);i1=q.GetSubstructMatch(pat)
  X=ideal[list(i1)];Y=oldxyz[list(i0)];U,sv,Vt=np.linalg.svd((X-X.mean(0)).T@(Y-Y.mean(0)));D=np.eye(3);D[-1,-1]=np.linalg.det(U@Vt);rot=U@D@Vt;xyz=(ideal-X.mean(0))@rot+Y.mean(0)-ct+dest
 m,md=add_component(c,cm['smiles'],'m'+str(i),coords_override=ideal.copy());ctr=xyz.mean(0)
 for j,v in enumerate(xyz-ctr):a=m.GetAtom(j);a.X,a.Y,a.Z=v
 m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*ctr);newmods.append(md)
d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();print('TRANSFER',source,target,'Rw',p.GetRw(),flush=True)
json.dump(newmods,open(R+'/model.json','w'),indent=1);export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml')
