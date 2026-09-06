import os,sys,json,itertools,numpy as np,gemmi,time
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import export_cif
sid=sys.argv[1];src=sys.argv[2];modelp=sys.argv[3];tag=sys.argv[4] if len(sys.argv)>4 else 'methoxy';W='/app/work/'+sid
obs=xml_cryst_file_load_all_object(src);c=next(o for o in obs if o.GetClassName()=='Crystal');p=next(o for o in obs if o.GetClassName()=='PowderPattern');d=next(p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternDiffraction');d.SetExtractionMode(False);md=json.load(open(modelp));mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())];orig=[];moves=[];els=[];exclude=[];offs=[0]
for mi,(m,z) in enumerate(zip(mols,md)):
 r=Chem.MolFromSmiles(z['smiles']);N=r.GetNumAtoms();a=np.array([[m.GetAtom(i).X,m.GetAtom(i).Y,m.GetAtom(i).Z] for i in range(m.GetNbAtoms())]);orig.append(a);rh=Chem.AddHs(r)
 dm=Chem.GetDistanceMatrix(r);exclude.append(dm<=3);els.extend([a.GetSymbol() for a in r.GetAtoms()]);offs.append(offs[-1]+N)
 for i,o,j in r.GetSubstructMatches(Chem.MolFromSmarts('[CH3]-[O;X2]-[c,C]')):
  attached=[i];iname=m.GetAtom(i).GetName()
  for bo in m.GetBondList():
   aa,bb=bo.GetAtom1(),bo.GetAtom2()
   if bb.GetName()==iname:aa,bb=bb,aa
   if aa.GetName()==iname and bb.GetScatteringPower().GetSymbol()=='H':attached.append(next(ii for ii in range(m.GetNbAtoms()) if m.GetAtom(ii).GetName()==bb.GetName()))
  moves.append((mi,i,o,j,attached))
print('MOVES',moves,flush=True)
N=len(els);ex=np.eye(N,dtype=bool)
for i,e in enumerate(exclude):ex[offs[i]:offs[i+1],offs[i]:offs[i+1]]=e
cp=[c.GetPar(x).GetHumanValue() for x in ['a','b','c','alpha','beta','gamma']];from pymatgen.core import Lattice
L=Lattice.from_parameters(*cp);sg=gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName());ops=list(sg.operations());rot=np.array([np.array(o.rot)/o.DEN for o in ops]);trans=np.array([np.array(o.tran)/o.DEN for o in ops]);radii={'C':1.48,'O':1.28,'N':1.35,'Cl':1.58,'Br':1.67};ra=np.array([radii.get(x,1.5) for x in els]);lim=ra[:,None]+ra[None,:]
def packing():
 fc=np.array([[a.X,a.Y,a.Z] for a in c.GetScatteringComponentList() if a.mpScattPow.GetSymbol()!='H']);bump=0;mind=10;worst=None
 for oi,(R,T) in enumerate(zip(rot,trans)):
  delta=fc[:,None,:]-(fc@R.T+T)[None,:,:];delta-=np.round(delta);dist=np.linalg.norm(delta@L.matrix,axis=-1);use=np.ones((N,N),bool)
  if np.allclose(R,np.eye(3)) and np.allclose(T%1,0):use=~ex;use&=np.triu(np.ones_like(use),1)
  pen=np.maximum(lim-dist,0)**2;pen[~use]=0;bump+=pen.sum()*(1 if oi==0 else .5)
  co=dist.copy();co[~use]=100;ix=np.unravel_index(co.argmin(),co.shape)
  if co[ix]<mind:mind=co[ix];worst=[int(ix[0]),int(ix[1]),int(oi),els[ix[0]],els[ix[1]]]
 return bump,mind,worst
p.Prepare();p.FitScaleFactorForRw();print('BASE',p.GetRw(),packing(),flush=True);results=[];best=1e100;t0=time.time();os.makedirs(W+'/search_'+tag,exist_ok=True)
json.dump(md,open(W+'/search_'+tag+'/model.json','w'),indent=1)
for mask in itertools.product([0,1],repeat=len(moves)):
 xyz=[a.copy() for a in orig]
 for bit,(mi,i,o,j,at) in zip(mask,moves):
  if not bit:continue
  axis=xyz[mi][j]-xyz[mi][o];axis/=np.linalg.norm(axis);v=xyz[mi][at]-xyz[mi][o];xyz[mi][at]=xyz[mi][o]+2*(v@axis)[:,None]*axis-v
 for m,a in zip(mols,xyz):
  for i,vec in enumerate(a):at=m.GetAtom(i);at.X,at.Y,at.Z=vec
 p.Prepare();p.FitScaleFactorForRw();rw=p.GetRw();bump,mind,worst=packing();# normalized Rwp-squared plus packing, deliberate chemical selection for weak methyl density
 score=1000*rw**2+float(os.getenv('BUMP_COEFF','3'))*bump
 result=dict(mask=mask,Rw=rw,bump=bump,min_contact=mind,worst=worst,score=score);results.append(result)
 if score<best:
  best=score;print('BEST',result,'sec',time.time()-t0,flush=True);export_cif(c,W+'/search_'+tag+'/best.cif');xml_cryst_file_save_global(W+'/search_'+tag+'/best.xml');json.dump(result,open(W+'/search_'+tag+'/best.json','w'),indent=1)
results.sort(key=lambda v:v['score']);json.dump(results,open(W+'/methoxy_'+tag+'.json','w'),indent=1)
print('DONE',time.time()-t0,results[:5],flush=True)
