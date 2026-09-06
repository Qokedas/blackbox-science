"""Replace one fragment by alternative chemically generated conformers.
The chosen anchor atoms are least-squares aligned to the native seed; all other
fragments' heavy-atom coordinates are preserved exactly. Search hypotheses only.
"""
import os,sys,json,numpy as np,itertools
from rdkit import Chem
from rdkit.Chem import AllChem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif
sid,src,modelp,tag=sys.argv[1:5];fi=int(sys.argv[5]);anchors=list(map(int,sys.argv[6].split(','))) if len(sys.argv)>6 else None;maxkeep=int(os.getenv('MAX_CONFORMERS','12'));W='/app/work/'+sid
O=xml_cryst_file_load_all_object(src);c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=next(p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternDiffraction');mods=json.load(open(modelp));old=[]
for i,md in enumerate(mods):
 m=c.GetScatterer(i);n=Chem.MolFromSmiles(md['smiles']).GetNumAtoms();sc=list(m.GetScatteringComponentList())[:n];old.append(np.array([c.FractionalToOrthonormalCoords(a.X,a.Y,a.Z) for a in sc]))
r0=Chem.MolFromSmiles(mods[fi]['smiles']);n=r0.GetNumAtoms();r=Chem.AddHs(r0)
if anchors is None:anchors=list(r0.GetSubstructMatch(Chem.MolFromSmarts('[OX1]=[CX3][NX3]')))
assert len(anchors)>=3
ps=AllChem.ETKDGv3();ps.randomSeed=89743;ps.numThreads=1;ps.pruneRmsThresh=.15
ids=list(AllChem.EmbedMultipleConfs(r,numConfs=200,params=ps));es=AllChem.MMFFOptimizeMoleculeConfs(r,numThreads=1,maxIters=700);ix=sorted(range(len(ids)),key=lambda i:es[i][1]);candidates=[];Y=old[fi][anchors]
for i in ix:
 if es[i][1]>es[ix[0]][1]+15:continue
 base=np.array(r.GetConformer(ids[i]).GetPositions())[:n]
 for reflect in [False,True]:
  if reflect and any(a.GetChiralTag()!=Chem.ChiralType.CHI_UNSPECIFIED for a in r0.GetAtoms()):continue
  xyz=base.copy()
  if reflect:xyz[:,2]*=-1
  X=xyz[anchors];U,sv,Vt=np.linalg.svd((X-X.mean(0)).T@(Y-Y.mean(0)));D=np.eye(3);D[-1,-1]=np.linalg.det(U@Vt);rot=U@D@Vt;dest=(xyz-X.mean(0))@rot+Y.mean(0)
  if any(np.sqrt(np.mean((dest-a['dest'])**2)*3)<.15 for a in candidates):continue
  candidates.append({'xyz':xyz,'dest':dest,'energy':es[i][1],'index':i,'reflected':reflect})
  if len(candidates)>=maxkeep:break
 if len(candidates)>=maxkeep:break
print('CONFORMERS',len(ids),'distinct',len(candidates),'anchors',anchors,flush=True);results=[]
for k,cc in enumerate(candidates):
 for m in [c.GetScatterer(j) for j in range(c.GetNbScatterer())]:c.RemoveScatterer(m)
 newmods=[]
 for j,md in enumerate(mods):
  dest=cc['dest'] if j==fi else old[j];ideal=cc['xyz'] if j==fi else np.array(md.get('restraint_coords',md.get('rdkit_coords',dest)))
  m,mo=add_component(c,md['smiles'],'m'+str(j),coords_override=ideal.copy());ctr=dest.mean(0)
  if m.GetClassName()=='Molecule':
   for ii,v in enumerate(dest-ctr):a=m.GetAtom(ii);a.X,a.Y,a.Z=map(float,v)
   m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.
  m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*ctr);newmods.append(mo)
  actual=np.array([c.FractionalToOrthonormalCoords(a.X,a.Y,a.Z) for a in list(m.GetScatteringComponentList())[:len(dest)]])
  assert np.max(np.abs((np.array([c.OrthonormalToFractionalCoords(*v) for v in actual-dest])+.5)%1-.5))<1.e-6,'World coordinates changed'
 d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();name=tag+'c'+str(k);R=W+'/search_'+name;os.makedirs(R,exist_ok=True);json.dump(newmods,open(R+'/model.json','w'),indent=1);export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');a={'tag':name,'energy':float(cc['energy']),'index':int(cc['index']),'reflected':cc['reflected'],'Rw':p.GetRw()};results.append(a);print(a,flush=True)
json.dump(results,open(W+'/'+tag+'_choices.json','w'),indent=1)
