"""Enumerate unspecified tertiary ammonium nitrogen configurations.
Reflect N and its one H through the plane of its three heavy neighbours.
This preserves all N-X distances and angles at N, but changes the configuration
at N; adjacent bond angles relax in a subsequent restrained refinement.
Only SMILES-unspecified N centres are moved. These are search hypotheses.
"""
import sys,os,json,numpy as np,itertools
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import export_cif
sid,src,modelp,tag=sys.argv[1:5];W='/app/work/'+sid;O=xml_cryst_file_load_all_object(src);c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);mods=json.load(open(modelp));mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())];orig=[];pos=[];anchors=[];moves=[]
for mi,(m,md) in enumerate(zip(mols,mods)):
 pos.append([m.X,m.Y,m.Z])
 if m.GetClassName()!='Molecule':orig.append(None);anchors.append(None);continue
 r=Chem.MolFromSmiles(md['smiles']);N=r.GetNumAtoms();xyz=np.array([[m.GetAtom(i).X,m.GetAtom(i).Y,m.GetAtom(i).Z] for i in range(m.GetNbAtoms())]);orig.append(xyz);a=m.GetScatteringComponentList()[0];anchors.append(np.array([a.X,a.Y,a.Z]));nam={m.GetAtom(i).GetName():i for i in range(m.GetNbAtoms())};bonds=[(nam[b.GetAtom1().GetName()],nam[b.GetAtom2().GetName()]) for b in m.GetBondList()]
 for a in r.GetAtoms():
  i=a.GetIdx();nb=[n.GetIdx() for n in a.GetNeighbors() if n.GetAtomicNum()>1]
  if a.GetSymbol()!='N' or a.GetFormalCharge()<=0 or len(nb)!=3 or a.GetTotalNumHs()!=1 or a.GetChiralTag()!=Chem.ChiralType.CHI_UNSPECIFIED:continue
  h=[y if x==i else x for x,y in bonds if (x==i and y>=N) or (y==i and x>=N)];moves.append((mi,i,nb,[i]+h))
print('N_INVERSION_MOVES',moves,flush=True);results=[]
for bits in itertools.product([0,1],repeat=len(moves)):
 xyz=[None if a is None else a.copy() for a in orig]
 for b,(mi,i,nb,moved) in zip(bits,moves):
  if not b:continue
  z=xyz[mi];u=z[nb];normal=np.cross(u[1]-u[0],u[2]-u[0]);normal/=np.linalg.norm(normal);dist=(z[moved]-u[0])@normal;z[moved]-=2*dist[:,None]*normal
 for mi,m in enumerate(mols):
  if xyz[mi] is None:continue
  m.X,m.Y,m.Z=pos[mi]
  for i,v in enumerate(xyz[mi]):a=m.GetAtom(i);a.X,a.Y,a.Z=map(float,v)
  a=m.GetScatteringComponentList()[0];df=anchors[mi]-np.array([a.X,a.Y,a.Z]);m.X+=df[0];m.Y+=df[1];m.Z+=df[2]
 d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();name=tag+'m'+''.join(map(str,bits));R=W+'/search_'+name;os.makedirs(R,exist_ok=True);json.dump(mods,open(R+'/model.json','w'),indent=1);export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');rec={'tag':name,'mask':bits,'Rw':p.GetRw()};results.append(rec);print(rec,flush=True)
json.dump(results,open(W+'/'+tag+'_choices.json','w'),indent=1)
