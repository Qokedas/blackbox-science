import os,sys,json,itertools,numpy as np,xml.etree.ElementTree as ET
from rdkit import Chem
from rdkit.Chem import Lipinski
from pymatgen.core import Lattice
from pymatgen.symmetry.groups import SpaceGroup
from gallop.structure import Structure
from gallop.z_matrix import Z_matrix
from pyobjcryst.io import xml_cryst_file_load_all_object
from obj_model import make_rdkit
import gemmi

def make_zmatrix(smiles,path,seed=10,rank=0,rigid=False,coords_override=None):
 if coords_override is None:r,xyz,e=make_rdkit(smiles,seed=seed,nconf=30,conf_rank=rank,hydrogen=False)
 else:r=Chem.MolFromSmiles(smiles);xyz=np.asarray(coords_override);e=0.
 n=len(xyz)
 adj={i:[a.GetIdx() for a in r.GetAtomWithIdx(i).GetNeighbors()] for i in range(n)}
 # Start at a terminal atom where possible; DFS preserves a reference for all rigid branches.
 root=min(range(n),key=lambda i:(len(adj[i]),i));parent={root:None};order=[];children={i:[] for i in range(n)}
 def dfs(i):
  order.append(i)
  for j in sorted(adj[i],key=lambda a:(len(adj[a])==1,a)):
   if j in parent:continue
   parent[j]=i;children[i].append(j);dfs(j)
 dfs(root);idx={j:i for i,j in enumerate(order)}
 flex={frozenset(x) for x in r.GetSubstructMatches(Lipinski.RotatableBondSmarts)}
 # Amide C-N bonds are planar. Other single bonds retain their internal degree of freedom.
 for b in r.GetBonds():
  i,j=b.GetBeginAtomIdx(),b.GetEndAtomIdx();ai=r.GetAtomWithIdx(i);aj=r.GetAtomWithIdx(j)
  amide=(ai.GetAtomicNum()==7 and aj.GetAtomicNum()==6 and any(z.GetBondTypeAsDouble()==2 and z.GetOtherAtom(aj).GetAtomicNum() in [8,16] for z in aj.GetBonds())) or (aj.GetAtomicNum()==7 and ai.GetAtomicNum()==6 and any(z.GetBondTypeAsDouble()==2 and z.GetOtherAtom(ai).GetAtomicNum() in [8,16] for z in ai.GetBonds()))
  if (ai.GetAtomicNum()==7 and ai.GetIsAromatic()) or (aj.GetAtomicNum()==7 and aj.GetIsAromatic()):amide=False
  if amide:flex.discard(frozenset([i,j]))
 if rigid:flex=set()
 lines=['Generated from supplied connectivity and an RDKit conformer','1 1 1 90 90 90',f'{n} 0'];zm=[]
 xyzord=xyz[order]
 # Transform first three atoms to the NERF initial convention using a proper rotation.
 if n>=3:
  ex=xyzord[1]-xyzord[0];ex/=np.linalg.norm(ex);ey=xyzord[2]-xyzord[0];ey-=ey@ex*ex;ey/=np.linalg.norm(ey);ez=np.cross(ex,ey);xyzcanon=(xyzord-xyzord[0])@np.array([ex,ey,ez]).T
 elif n==2:xyzcanon=np.array([[0,0,0],[np.linalg.norm(xyzord[1]-xyzord[0]),0,0]])
 else:xyzcanon=np.zeros((1,3))
 for ii,old in enumerate(order):
  ref=0
  if ii==0:R,ang,phi,b,a,t=0,0,0,0,0,0
  elif ii in [1,2]:
   v=xyzcanon[ii];R=np.linalg.norm(v);ang=np.rad2deg(np.arccos(np.clip(-v[0]/R,-1,1)));phi=0.;b,a,t=1,0,0
  else:
   pp=parent[old];gp=parent[pp]
   if gp is None:
    # At a root branch: use another previously placed neighbour as the angle reference.
    gp=next(o for o in order[:ii] if o!=pp and np.linalg.norm(np.cross(xyz[old]-xyz[pp],xyz[o]-xyz[pp]))>1e-5)
   siblings=children[pp];first=siblings[0]
   if old!=first:tp=first
   else:tp=parent.get(gp)
   if tp is None or tp in [old,pp,gp] or idx.get(tp,ii)>=ii:
    tp=max([o for o in order[:ii] if o not in [pp,gp]],key=lambda o:np.linalg.norm(np.cross(xyz[gp]-xyz[o],xyz[pp]-xyz[gp])))
   C=xyz[pp];B=xyz[gp];A=xyz[tp];bc=C-B;bc/=np.linalg.norm(bc);nv=np.cross(B-A,bc);nv/=np.linalg.norm(nv);nbc=np.cross(nv,bc);v=xyz[old]-C;R=np.linalg.norm(v);ang=np.rad2deg(np.arccos(np.clip(-v@bc/R,-1,1)));phi=np.rad2deg(np.arctan2(v@nv,v@nbc));b,a,t=idx[pp]+1,idx[gp]+1,idx[tp]+1
   if old==first and frozenset([pp,gp]) in flex:ref=1
  el=r.GetAtomWithIdx(old).GetSymbol();lines.append(f'{el} {R:.8f} 0 {ang:.8f} 0 {phi:.8f} {ref} {b} {a} {t} 3.0 1.0 {ii+1} {el}{old+1}')
 open(path,'w').write('\n'.join(lines)+'\n');z=Z_matrix(path)
 dist=np.max(np.abs(np.linalg.norm(xyzcanon[:,None]-xyzcanon[None,:],axis=2)-np.linalg.norm(z.initial_cartesian[:,None]-z.initial_cartesian[None,:],axis=2)))
 print('ZM',smiles,'n',n,'torsions',z.internal_degrees_of_freedom,'max_distance_error',dist,flush=True)
 if dist>.002:raise RuntimeError('Z-matrix failed to reproduce molecular geometry')
 return z,dict(smiles=smiles,elements=[a.GetSymbol() for a in r.GetAtoms()],order=order,rdkit_coords=xyz.tolist(),energy=e)

def prepare(sid,run=1,zprime=1,rigid=False,model_path=None,stolmax=.21):
 W='/app/work/'+sid;G=W+'/gallop_'+str(run);os.makedirs(G,exist_ok=True)
 objs=xml_cryst_file_load_all_object(os.environ.get('BASE_XML',W+'/base.xml'));c=[o for o in objs if o.GetClassName()=='Crystal'][0];p=[o for o in objs if o.GetClassName()=='PowderPattern'][0];d=p.GetPowderPatternComponent(0)
 # An atomless loaded Crystal can leave ObjCryst's internal single-crystal scale NaN.
 # A disposable scatterer stabilizes that cache; it is never included in the GALLOP model.
 if c.GetNbScatterer()==0:
  from obj_model import add_component
  dummy,_=add_component(c,'C','pawley_dummy')
 d.SetExtractionMode(True,False);p.Prepare();d.ExtractLeBail(20);p.Prepare();p.FitScaleFactorForRw()
 cp=[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']];sg=gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName());L=Lattice.from_parameters(*cp);ins=json.load(open('/app/data/instances/'+sid+'/instrument.json'));wl=ins['radiation']['wavelength_A']
 # Read the original Le Bail reflection order before applying a resolution cutoff.
 hkls=np.array([d.GetH(),d.GetK(),d.GetL()]).T.astype(int);stol=np.array(d.GetSinThetaOverLambda());f2=np.array(d.GetFhklObsSq());xx=np.rad2deg(p.GetPowderPatternX());obs=np.array(p.GetPowderPatternObs());wg=np.array(p.GetLSQWeight(0));tt=np.rad2deg(2*np.arcsin(wl*stol));zero=p.GetPar('Zero').GetHumanValue()
 sel=(tt+zero>xx[0]-.02)&(tt+zero<xx[-1])&(stol<=stolmax);hkls=hkls[sel];tt=tt[sel];stol=stol[sel];f2=f2[sel]
 s=Structure(sid,ignore_H_atoms=True);s.lattice=L;s.sg_number=sg.number;s.original_sg_number=sg.number;s.space_group=SpaceGroup(sg.xhm());s.centrosymmetric=sg.is_centrosymmetric();s.affine_matrices=np.array([op.affine_matrix for op in s.space_group.symmetry_ops]);s.wavelength=wl;s.hkl=hkls;s.intensities=f2;s.twotheta=tt;s.dspacing=1/(2*stol);s.data_resolution=float(s.dspacing[-1]);s.source='GSAS';s.PawleyChiSq=1.;s.temperature=ins.get('temperature_K',298.)
 # Exact fixed-profile Pawley covariance from the ObjCryst reflection profiles.
 from obj_bridge import exact_pawley
 pw=exact_pawley(p,d,stolmax=stolmax,rcond=float(os.environ.get('PAWLEY_RCOND','.001')))
 ii=pw['sel'];hkls=np.array([d.GetH(),d.GetK(),d.GetL()]).T.astype(int)[ii];stol=np.asarray(d.GetSinThetaOverLambda())[ii];tt=np.rad2deg(2*np.arcsin(wl*stol));f2=pw['obs'];A=pw['matrix'];normal=pw['normal']
 # Only a global normalization is applied: chi2=1000 is the background-subtracted signal variance.
 normal=normal*((len(hkls)-2)*1000/max(pw['var'],1e-25))
 s.hkl=hkls;s.intensities=f2;s.twotheta=tt;s.dspacing=1/(2*stol);s.data_resolution=float(s.dspacing[-1]);s.inverse_covariance_matrix=normal
 comp=json.load(open(model_path or '/app/data/instances/'+sid+'/composition.json'));meta=[]
 for z in range(zprime):
  for ic,co in enumerate(comp['components']):
   for cc in range(co['count']):
    zm,md=make_zmatrix(co['smiles'],G+f'/m{z}_{ic}_{cc}.zmatrix',seed=1027+run*21+z*11+ic,rank=int(os.environ.get('CONF_RANK',str(run))),rigid=rigid,coords_override=co.get('coords'));s.zmatrices.append(zm);meta.append(md)
 # GALLOP's analytical structure factors assume its standard setting.
 # Retain affine operations but request general expansion for non-standard settings.
 if sg.xhm()!=gemmi.find_spacegroup_by_number(sg.number).xhm():
  s.sg_number=0
  print('GENERIC_SYMMETRY',sg.xhm(),flush=True)
 s.sg_symbol=sg.xhm()
 s.get_total_degrees_of_freedom(verbose=True)
 for obj in [s]+s.zmatrices:
  for key,value in list(obj.__dict__.items()):
   if isinstance(value,np.generic):setattr(obj,key,value.item())
 json.dump(meta,open(G+'/model.json','w'),indent=1);open(G+'/structure.json','w').write(s.to_json());np.savez_compressed(G+'/profile_matrix.npz',matrix=A,hkl=hkls,normal=normal,tt=tt,obs=f2)
 print('PREPARED',sid,'Nref',len(hkls),'PawleyRw',p.GetRw(),'SG',sg.xhm(),flush=True)
 return s,G

if __name__=='__main__':
 sid=sys.argv[1];run=int(sys.argv[2]) if len(sys.argv)>2 else 1;zp=int(sys.argv[3]) if len(sys.argv)>3 else 1;mp=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--model=')),None)
 prepare(sid,run,zp,rigid='--rigid' in sys.argv,model_path=mp,stolmax=float(os.environ.get('GALLOP_STOL','.21')))
