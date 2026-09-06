import os,sys,time,json,numpy as np,gemmi
from scipy.optimize import differential_evolution,minimize
from scipy.spatial.transform import Rotation
from numba import njit
from pymatgen.core import Lattice
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object
from obj_model import make_rdkit
from obj_bridge import exact_pawley
sid=sys.argv[1];run=sys.argv[2] if len(sys.argv)>2 else 'de1';W='/app/work/'+sid;R=W+'/'+run;os.makedirs(R,exist_ok=True)
base=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--base=')),W+'/base.xml')
O=xml_cryst_file_load_all_object(base);p=next(o for o in O if o.GetClassName()=='PowderPattern');c=next(o for o in O if o.GetClassName()=='Crystal');d=p.GetPowderPatternComponent(0)
stolmax=float(os.environ.get('DE_STOL','.25'));pw=exact_pawley(p,d,stolmax=stolmax,rcond=.001);ii=pw['sel'];hkl=np.array([d.GetH(),d.GetK(),d.GetL()]).T[ii];stol=np.asarray(d.GetSinThetaOverLambda())[ii]
normal=np.ascontiguousarray(pw['normal']*1000/pw['var']);obs=pw['obs'];no=np.ascontiguousarray(normal@obs);oo=float(obs@no)
cp=[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']];lat=Lattice.from_parameters(*cp);linv=np.linalg.inv(lat.matrix);lm=lat.matrix
sg=gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName());sym=np.array([np.array(op.rot)/24 for op in sg.operations()]);trs=np.array([np.array(op.tran)/24 for op in sg.operations()]);
modelpath=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--model=')),'/app/data/instances/'+sid+'/composition.json');comp=json.load(open(modelpath));zp=int(os.environ.get('ZPRIME','1'));els=[];xyz=[];groups=[];models=[]
for iz in range(zp):
 for ic,co in enumerate(comp['components']):
  for cc in range(co['count']):
   r=Chem.MolFromSmiles(co['smiles']);n=r.GetNumAtoms()
   if n==1:xy=np.zeros((1,3))
   elif 'coords' in co:
    xy=np.asarray(co['coords']);cf=Chem.Conformer(n)
    for i,v in enumerate(xy):cf.SetAtomPosition(i,v)
    r.AddConformer(cf)
    if '--hydrogen' in sys.argv:r=Chem.AddHs(r,addCoords=True);xy=r.GetConformer().GetPositions()
   else:r,xy,en=make_rdkit(co['smiles'],seed=1009+ic+iz*71,conf_rank=int(os.environ.get('CONF_RANK','0')),hydrogen='--hydrogen' in sys.argv)
   xy=xy-xy.mean(axis=0);groups.append((len(xyz),len(xyz)+len(xy)));xyz.extend(xy.tolist());els.extend([a.GetSymbol() for a in r.GetAtoms()]);models.append({'smiles':co['smiles'],'coords':xy.tolist(),'heavy':n})
xyz=np.asarray(xyz);groups=np.asarray(groups,dtype=np.int64);nm=len(groups);sf=np.array([[gemmi.Element(el).it92.calculate_sf(float(s*s))*np.exp(-(4. if el=='H' else 3.)*s*s) for el in els] for s in stol]);
# Optional low-dimensional alkane zone-axis search. The dominant transverse
# reflections identify the long molecular axis, leaving only roll and translation.
axisarg=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--axis=')),None)
frames=np.repeat(np.eye(3)[None,:,:],nm,axis=0);axis_tilt=float(os.environ.get('AXIS_TILT','0'))
if axisarg:
 uvw=np.asarray([float(x) for x in axisarg.split(',')]);u=uvw@lm;u/=np.linalg.norm(u);v=np.array([0.,1.,0.]);v-=v@u*u;v/=np.linalg.norm(v);T=np.column_stack([u,v,np.cross(u,v)])
 for j,(a,b) in enumerate(groups):
  if b-a<3:continue
  vh=np.linalg.svd(xyz[a:b]-xyz[a:b].mean(0))[2];C=np.vstack([vh[0],vh[1],np.cross(vh[0],vh[1])]);xyz[a:b]=xyz[a:b]@C.T;frames[j]=T
# Variable maps: one fractional translation per fragment, orientations for non-atomic fragments.
bounds=[];ix=[]
for j,(start,end) in enumerate(groups):
 tr=[];rot=[]
 for ax in range(3):
  if j==0 and (sg.number==1 or (sg.number in [3,4,5] and ax==1)):tr.append(-1)
  else:tr.append(len(bounds));bounds.append((0.,1.))
 for ax in range(3):
  if end-start==1 or (axisarg and ax>0 and axis_tilt==0):rot.append(-1)
  else:rot.append(len(bounds));bounds.append((-axis_tilt,axis_tilt) if axisarg and ax>0 else (-np.pi/2,np.pi/2) if ax==1 else (-np.pi,np.pi))
 ix.append(tr+rot)
ix=np.asarray(ix,dtype=np.int64)
@njit(cache=False)
def coords(x):
 fr=np.zeros_like(xyz)
 for j in range(nm):
  t=np.zeros(3);ang=np.zeros(3)
  for k in range(3):
   if ix[j,k]>=0:t[k]=x[ix[j,k]]
   if ix[j,k+3]>=0:ang[k]=x[ix[j,k+3]]
  ca,cb,cc=np.cos(ang[0]),np.cos(ang[1]),np.cos(ang[2]);sa,sb,sc=np.sin(ang[0]),np.sin(ang[1]),np.sin(ang[2]);rot=np.array([[cb*cc,cc*sa*sb-ca*sc,sa*sc+ca*cc*sb],[cb*sc,ca*cc+sa*sb*sc,ca*sb*sc-cc*sa],[-sb,cb*sa,ca*cb]])
  for i in range(groups[j,0],groups[j,1]):fr[i]=((xyz[i]@rot.T)@frames[j].T)@linv+t
 return fr
hklsym=np.ascontiguousarray(np.einsum('ri,sij->rsj',hkl,sym));phasetr=np.ascontiguousarray(hkl@trs.T*2*np.pi)
@njit(cache=False)
def score(x):
 fr=coords(x);f=np.zeros(len(hkl))
 for h in range(len(hkl)):
  re=0.;im=0.
  for op in range(len(sym)):
   for a in range(len(xyz)):
    pha=2*np.pi*(hklsym[h,op,0]*fr[a,0]+hklsym[h,op,1]*fr[a,1]+hklsym[h,op,2]*fr[a,2])+phasetr[h,op]
    re+=sf[h,a]*np.cos(pha);im+=sf[h,a]*np.sin(pha)
  f[h]=re*re+im*im
 nf=normal@f;ff=np.dot(f,nf);of=np.dot(f,no)
 return oo-max(0.,of)**2/max(ff,1e-30)

def save(x,cost,it):
 fr=coords(x);text='data_solution\n'
 for k,v in zip(['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma'],cp):text+=f'_cell_{k} {v:.9f}\n'
 text+=f"_space_group_name_H-M_alt '{sg.xhm()}'\n_space_group_IT_number {sg.number}\nloop_\n_space_group_symop_id\n_space_group_symop_operation_xyz\n"
 for i,op in enumerate(sg.operations()):text+=f"{i+1} '{op.triplet()}'\n"
 text+='loop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n_atom_site_B_iso_or_equiv\n'
 for i,(el,f) in enumerate(zip(els,fr)):text+=f'{el}{i+1} {el} {f[0]%1:.9f} {f[1]%1:.9f} {f[2]%1:.9f} 1 {4 if el=="H" else 3}\n'
 open(R+'/best.cif','w').write(text);np.save(R+'/best.npy',x);np.save(R+'/best_frac.npy',fr);json.dump({'cost':float(cost),'iteration':it,'elapsed':time.time()-t0},open(R+'/best.json','w'),indent=1)
json.dump(models,open(R+'/model.json','w'),indent=1);json.dump({'base':base,'cell':cp,'sg':sg.xhm(),'groups':groups.tolist(),'ix':ix.tolist()},open(R+'/info.json','w'))
print('DE_SETUP',sid,'atoms',len(xyz),'nref',len(hkl),'ndof',len(bounds),flush=True);t0=time.time();score(np.mean(np.asarray(bounds),axis=1));best=1e10
if os.path.exists(R+'/best.npy'):
 x0=np.load(R+'/best.npy');best=score(x0);print('PREVIOUS',best,flush=True)
seedxml=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--seed-xml=')),None)
xseed=None
if seedxml:
 so=xml_cryst_file_load_all_object(seedxml);sc=next(o for o in so if o.GetClassName()=='Crystal');slat=Lattice.from_parameters(*[sc.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']]);xseed=np.mean(np.asarray(bounds),axis=1)
 for j,grp in enumerate(groups):
  m=sc.GetScatterer(j);cl=m.GetScatteringComponentList();target=np.asarray([[a.X,a.Y,a.Z] for a in cl])@slat.matrix;source=xyz[grp[0]:grp[1]]
  # Both hydrogenated and heavy-only seeds are supported by using the common prefix.
  n=min(len(target),len(source));source=source[:n];target=target[:n];a=source-source.mean(axis=0);b=target-target.mean(axis=0);u,sv,vt=np.linalg.svd(a.T@b);M=u@np.diag([1.,1.,np.linalg.det(u@vt)])@vt;angles=Rotation.from_matrix(frames[j].T@M.T).as_euler('xyz');ctr=(target.mean(axis=0)-source.mean(axis=0)@M)@linv
  for k in range(3):
   if ix[j,k]>=0:xseed[ix[j,k]]=ctr[k]%1
   if ix[j,k+3]>=0:xseed[ix[j,k+3]]=angles[k]
  print('SEED_RMSD',j,float(np.sqrt(np.mean(np.sum((a@M-b)**2,axis=1)))),flush=True)
 print('SEED_COST',score(xseed),xseed,flush=True);rr=minimize(score,xseed,method='Nelder-Mead',options={'maxiter':2500,'xatol':1e-7});xseed=rr.x
 print('SEED_LOCAL',rr.fun,flush=True)
 if rr.fun<best:best=rr.fun;save(rr.x,rr.fun,-1)
for it in range(int(os.environ.get('TRIALS','10'))):
 init='latinhypercube'
 if xseed is not None:
  bnd=np.asarray(bounds);pop=max(5,int(os.environ.get('POPSIZE','18'))*len(bounds));init=np.random.uniform(bnd[:,0],bnd[:,1],size=(pop,len(bounds)))
  for j in range(pop//2):init[j]=np.clip(xseed+np.random.normal(size=len(bounds))*(bnd[:,1]-bnd[:,0])*.10,bnd[:,0],bnd[:,1])
  init[0]=np.clip(xseed,bnd[:,0],bnd[:,1])
 res=differential_evolution(score,bounds,popsize=int(os.environ.get('POPSIZE','18')),maxiter=int(os.environ.get('MAXITER','1600')),tol=1e-7,polish=True,workers=1,init=init)
 print('DE',sid,it,'cost',res.fun,'elapsed',time.time()-t0,flush=True)
 if res.fun<best:best=res.fun;save(res.x,res.fun,it)
 if time.time()-t0>float(os.environ.get('SEARCH_TIME','1000')):break
