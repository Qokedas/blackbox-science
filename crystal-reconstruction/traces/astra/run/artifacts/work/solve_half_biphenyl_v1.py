import sys,os,time,json,numpy as np,gemmi
from scipy.optimize import differential_evolution, minimize
from numba import njit
from pyobjcryst.io import xml_cryst_file_load_all_object
from obj_bridge import exact_pawley
from obj_model import make_rdkit
from pymatgen.core import Lattice
sid='X7e382cb';W='/app/work/'+sid
O=xml_cryst_file_load_all_object(W+'/base.xml');p=next(o for o in O if o.GetClassName()=='PowderPattern');c=next(o for o in O if o.GetClassName()=='Crystal');d=p.GetPowderPatternComponent(0)
pw=exact_pawley(p,d,stolmax=.25,rcond=.002);sel=pw['sel'];hkl=np.array([d.GetH(),d.GetK(),d.GetL()]).T[sel];stol=np.asarray(d.GetSinThetaOverLambda())[sel]
cp=[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']];lat=Lattice.from_parameters(*cp);linv=np.linalg.inv(lat.matrix);lm=lat.matrix
normal=pw['normal']*1000/pw['var'];obs=pw['obs'];no=normal@obs;oo=float(obs@no)
r,xyz,en=make_rdkit('O=C([O-])c1ccccc1',seed=143,hydrogen=False)
# Indices 0/1/2 are carboxylate; para carbon 6 carries the bond through inversion.
axis=xyz[6]-(xyz[5]+xyz[7])/2;axis/=np.linalg.norm(axis);center=xyz[6]+axis*.745;xyz=xyz-center
axis=(xyz[1]-xyz[3]);axis/=np.linalg.norm(axis);point=xyz[3].copy()
els=[a.GetSymbol() for a in r.GetAtoms()]+['N'];sf=np.array([[gemmi.Element(el).it92.calculate_sf(float(s*s)) for s in stol] for el in els]).T*2
sf*=np.exp(-3.0*stol[:,None]**2)
@njit(cache=False)
def coords(x):
 ca,cb,cc=np.cos(x[0]),np.cos(x[1]),np.cos(x[2]);sa,sb,sc=np.sin(x[0]),np.sin(x[1]),np.sin(x[2])
 R=np.array([[cb*cc,cc*sa*sb-ca*sc,sa*sc+ca*cc*sb],[cb*sc,ca*cc+sa*sb*sc,ca*sb*sc-cc*sa],[-sb,cb*sa,ca*cb]])
 xy=xyz.copy();ph=x[6];cv=np.cos(ph);sv=np.sin(ph)
 for j in [0,2]:
  v=xy[j]-point;xy[j]=point+v*cv+np.cross(axis,v)*sv+axis*np.dot(axis,v)*(1-cv)
 fr=np.zeros((10,3));fr[:9]=(xy@R.T)@linv;fr[9]=x[3:6]
 return fr
@njit(cache=False)
def score(x):
 fr=coords(x);f=np.zeros(len(hkl))
 for j in range(len(hkl)):
  a=0.
  for i in range(10):a+=sf[j,i]*np.cos(2*np.pi*np.dot(fr[i],hkl[j]))
  f[j]=a*a
 nf=normal@f;s=np.dot(f,no)/np.dot(f,nf);z=obs-s*f;res=np.dot(z,normal@z)
 # N--N and N--organic contacts: remove pathological coincident ammonium sites.
 # For this triclinic cell, enumerate neighbour translations explicitly.
 for typ in range(3):
  ni=1 if typ==2 else 9
  for i in range(ni):
   delta=(2*fr[9] if typ==2 else fr[9]-(fr[i] if typ==0 else -fr[i]));delta-=np.rint(delta)
   best=100.
   for a in range(-1,2):
    for b in range(-1,2):
     for zt in range(-1,2):
      dd=np.array([delta[0]+a,delta[1]+b,delta[2]+zt])@lm;dist=np.dot(dd,dd)
      if dist<best:best=dist
   limit=2.5 if typ==2 else (2.35 if i in [0,2] else 2.60)
   if best<limit*limit:res+=80*(limit-np.sqrt(best))**2
 return res

def save(x,cost,itr):
 frac=coords(x);text='data_solution\n'
 for nm,v in zip(['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma'],cp):text+=f'_cell_{nm} {v:.9f}\n'
 text+="_space_group_name_H-M_alt 'P -1'\n_space_group_IT_number 2\nloop_\n_space_group_symop_id\n_space_group_symop_operation_xyz\n1 'x,y,z'\n2 '-x,-y,-z'\nloop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n_atom_site_B_iso_or_equiv\n"
 for i,(el,f) in enumerate(zip(els,frac)):text+=f'{el}{i+1} {el} {f[0]%1:.9f} {f[1]%1:.9f} {f[2]%1:.9f} 1 3\n'
 open(W+'/half_best.cif','w').write(text);np.save(W+'/half_best.npy',x);json.dump({'cost':float(cost),'iteration':itr},open(W+'/half_best.json','w'),indent=1)

bounds=[(-np.pi,np.pi),(-np.pi/2,np.pi/2),(-np.pi,np.pi),(0,1),(0,1),(0,1),(-np.pi,np.pi)]
best=1e10;t0=time.time();score(np.mean(np.array(bounds),axis=1))
for it in range(int(os.environ.get('TRIALS','8'))):
 res=differential_evolution(score,bounds,popsize=22,maxiter=800,tol=.000001,polish=True,workers=1)
 print('HALF_SOLVE',it,'cost',res.fun,'elapsed',time.time()-t0,'x',res.x,flush=True)
 if res.fun<best:best=res.fun;save(res.x,res.fun,it)
 if time.time()-t0>float(os.environ.get('SEARCH_TIME','600')):break
