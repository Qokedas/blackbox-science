"""Generate the two axial/equatorial choices for each monosubstituted chair.
A 180-degree rotation about the bisector of the two ring bonds at the attachment
atom exchanges the two neighbouring C sites while turning over the remote ring.
The substituent and attachment atom remain fixed. This is only a search move.
"""
import sys,os,json,numpy as np,itertools
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import export_cif
sid,src,modelp,tag=sys.argv[1:5];W='/app/work/'+sid;O=xml_cryst_file_load_all_object(src);c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);mods=json.load(open(modelp));moves=[];orig=[];mols=[];originalpos=[];anchors=[]
for mi,md in enumerate(mods):
 m=c.GetScatterer(mi);mols.append(m);originalpos.append([m.X,m.Y,m.Z])
 if m.GetClassName()!='Molecule':orig.append(None);anchors.append(None);continue
 r=Chem.MolFromSmiles(md['smiles']);N=r.GetNumAtoms();coords=np.array([[m.GetAtom(i).X,m.GetAtom(i).Y,m.GetAtom(i).Z] for i in range(m.GetNbAtoms())]);orig.append(coords);rh=Chem.AddHs(r)
 nameindex={m.GetAtom(i).GetName():i for i in range(m.GetNbAtoms())};bonds=[]
 for bo in m.GetBondList():bonds.append((nameindex[bo.GetAtom1().GetName()],nameindex[bo.GetAtom2().GetName()]))
 for ring in r.GetRingInfo().AtomRings():
  rs=set(ring)
  if len(rs)!=6 or any(r.GetAtomWithIdx(i).GetIsAromatic() for i in rs):continue
  external=[(i,a.GetIdx()) for i in rs for a in r.GetAtomWithIdx(i).GetNeighbors() if a.GetIdx() not in rs]
  if len(external)!=1:continue
  center,parent=external[0]
  if r.GetAtomWithIdx(center).GetChiralTag()!=Chem.ChiralType.CHI_UNSPECIFIED:continue
  nb=[a.GetIdx() for a in r.GetAtomWithIdx(center).GetNeighbors() if a.GetIdx() in rs]
  moved=rs-{center}
  for i,j in bonds:
   if i in moved and j>=N:moved.add(j)
   if j in moved and i>=N:moved.add(i)
  moves.append((mi,center,nb,sorted(moved)))
 a=m.GetScatteringComponentList()[0];anchors.append(np.array([a.X,a.Y,a.Z]))
print('CHAIR_MOVES',moves,flush=True)
res=[]
for mask in itertools.product([0,1],repeat=len(moves)):
 xyz=[None if a is None else a.copy() for a in orig]
 for bit,(mi,center,nb,moved) in zip(mask,moves):
  if not bit:continue
  aa=xyz[mi];v=aa[nb]-aa[center];v/=np.linalg.norm(v,axis=1,keepdims=True);axis=v.sum(0);axis/=np.linalg.norm(axis);z=aa[moved]-aa[center];aa[moved]=aa[center]+2*(z@axis)[:,None]*axis-z
 for mi,m in enumerate(mols):
  if xyz[mi] is None:continue
  m.X,m.Y,m.Z=map(float,originalpos[mi])
  for i,v in enumerate(xyz[mi]):a=m.GetAtom(i);a.X,a.Y,a.Z=map(float,v)
  a=m.GetScatteringComponentList()[0];df=anchors[mi]-np.array([a.X,a.Y,a.Z]);m.X+=df[0];m.Y+=df[1];m.Z+=df[2]
 d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();name=tag+'m'+''.join(map(str,mask));R=W+'/search_'+name;os.makedirs(R,exist_ok=True);json.dump(mods,open(R+'/model.json','w'),indent=1);export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');res.append({'tag':name,'mask':mask,'Rw':p.GetRw()});print(res[-1],flush=True)
json.dump(res,open(W+'/'+tag+'_choices.json','w'),indent=1)
