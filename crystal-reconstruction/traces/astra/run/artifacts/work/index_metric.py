import sys,os,json,time,itertools,numpy as np
from numba import njit
from scipy.optimize import differential_evolution,least_squares
from pymatgen.core import Lattice
sid=sys.argv[1];system=sys.argv[2] if len(sys.argv)>2 else 'MONOCLINIC';center=sys.argv[3] if len(sys.argv)>3 else 'P';W='/app/work/'+sid
wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A'];ps=json.load(open(W+'/'+os.environ.get('PEAK_FILE','peaks_raw.json')))
sp=os.environ.get('SELECT_FILE',W+'/peak_select_raw.json')
if os.path.exists(sp):si=json.load(open(sp));ps=[ps[i-1] for i in si['indices']] if 'indices' in si else [p for p in ps if p['two_theta']>=si.get('min_two_theta',0)]
ps=ps[int(os.environ.get('PEAK_SKIP','0')):][:int(os.environ.get('NPEAK','25'))];tt=np.array([p['two_theta'] for p in ps]);qobs=(2*np.sin(np.deg2rad(tt/2))/wl)**2;fac=wl**2/(2*np.sin(np.deg2rad(tt)))*180/np.pi
import gemmi
sg_filter=gemmi.find_spacegroup_by_name(os.environ['SG_FILTER']).operations() if 'SG_FILTER' in os.environ else None
hkl=[];R=int(os.environ.get('HMAX','10'))
for h in range(0,R+1):
 for k in (range(0,R+1) if system!='TRICLINIC' else range(-R,R+1)):
  for l in (range(0,R+1) if system=='ORTHOROMBIC' else range(-R,R+1)):
   if not(h or k or l):continue
   if h==0 and (k<0 or (k==0 and l<0)):continue
   if system=='MONOCLINIC' and h==0 and l<0:continue
   if sg_filter is not None and sg_filter.is_systematically_absent([h,k,l]):continue
   if center=='C' and (h+k)%2:continue
   if center=='I' and (h+k+l)%2:continue
   if center=='F' and ((h+k)%2 or (h+l)%2):continue
   hkl.append((h,k,l))
hkl=np.array(hkl,dtype=float);terms=np.array([hkl[:,0]**2,hkl[:,1]**2,hkl[:,2]**2,2*hkl[:,1]*hkl[:,2],2*hkl[:,0]*hkl[:,2],2*hkl[:,0]*hkl[:,1]]).T
lo=float(os.environ.get('VMIN','700'));hi=float(os.environ.get('VMAX','3200'));tar=float(os.environ.get('VTARGET',np.sqrt(lo*hi)));err=float(os.environ.get('TTHERR','.025'));nspur=int(os.environ.get('NSPUR','1'));max_time=float(os.environ.get('INDEX_TIME','300'));ndim={'ORTHOROMBIC':4,'MONOCLINIC':5,'TRICLINIC':7}[system];sgn={'ORTHOROMBIC':'P m m m','MONOCLINIC':'P 1 2/m 1','TRICLINIC':'P -1'}[system]
@njit(cache=False)
def metric(x):
 g=np.zeros(6);g[:3]=x[:3]**2
 if ndim==5:g[4]=x[3]*x[0]*x[2]
 if ndim==7:g[3]=x[3]*x[1]*x[2];g[4]=x[4]*x[0]*x[2];g[5]=x[5]*x[0]*x[1]
 return g
@njit(cache=False)
def diffs(x):
 g=metric(x);qc=terms@g;ix=np.zeros(len(tt),np.int64);dif=np.zeros(len(tt))
 for i in range(len(tt)):
  qq=qobs[i]-x[-1]/fac[i];bd=1e10
  for j in range(len(qc)):
   dd=abs(qc[j]-qq)
   if dd<bd:bd=dd;ix[i]=j
  dif[i]=(qc[ix[i]]-qobs[i])*fac[i]+x[-1]
 return dif,ix
@njit(cache=False)
def cost(x):
 g=metric(x);det=g[0]*g[1]*g[2]+2*g[3]*g[4]*g[5]-g[0]*g[3]**2-g[1]*g[4]**2-g[2]*g[5]**2
 if det<=0:return 1000.
 vol=1/np.sqrt(det);dc,ix=diffs(x);sq=np.log1p((dc/err)**2);sq.sort();co=np.mean(sq[:len(sq)-nspur])*vol/tar
 for i in range(len(ix)):
  for j in range(i):
   if ix[i]==ix[j]:co+=.06
 if vol<lo:co+=100*np.log(lo/vol)**2
 if vol>hi:co+=100*np.log(vol/hi)**2
 return co
amin=float(os.environ.get('AMIN','3.5'));amax=float(os.environ.get('AMAX','50'));bounds=[(1/amax,1/amin)]*3
if system=='MONOCLINIC':bounds+=[(0.,.7)]
if system=='TRICLINIC':bounds+=[(-.45,.45)]*3
bounds+=[(-float(os.environ.get('ZEROMAX','.10')),float(os.environ.get('ZEROMAX','.10')))]
if 'BOUNDS_FILE' in os.environ:bounds=json.load(open(os.environ['BOUNDS_FILE']))
print('METRIC_INDEX',sid,system,center,'peaks',tt.tolist(),'bounds',bounds,'volume',lo,hi,flush=True);cost(np.mean(bounds,axis=1));t0=time.time();sol=[];tag=os.environ.get('INDEX_TAG','metric_'+system+'_'+center)
for trial in range(int(os.environ.get('TRIALS','60'))):
 kw={}
 if sol and trial%3:
  ss=sol[0]['parameters'];pop=np.random.uniform(np.array(bounds)[:,0],np.array(bounds)[:,1],size=(max(60,18*ndim),ndim));half=len(pop)//2;pop[:half]=np.clip(np.array(ss)*(1+np.random.normal(size=(half,ndim))*.15),np.array(bounds)[:,0],np.array(bounds)[:,1]);kw['init']=pop
 res=differential_evolution(cost,bounds,popsize=int(os.environ.get('POPSIZE','18')),maxiter=int(os.environ.get('MAXITER','700')),polish=False,tol=.0001,workers=1,**kw);x=res.x
 for j in range(6):
  _,ix=diffs(x);tr=terms[ix]
  re=least_squares(lambda xx:(tr@metric(xx)-qobs)*fac+xx[-1],x,bounds=np.array(bounds).T,loss='soft_l1',f_scale=err,max_nfev=100)
  if cost(re.x)>cost(x)+.05:break
  x=re.x
 g=metric(x);GM=np.array([[g[0],g[5],g[4]],[g[5],g[1],g[3]],[g[4],g[3],g[2]]]);L=Lattice(np.linalg.cholesky(np.linalg.inv(GM)));df,ix=diffs(x);nc=np.sum(terms@g<qobs[-1]);sc=qobs[-1]/(2*max(1e-10,np.mean(abs(df)/fac))*nc);cell=list(L.parameters)
 if system=='ORTHOROMBIC':cell[:3]=sorted(cell[:3]) if center=='P' else cell[:3]
 o=dict(cell=cell,system=system,centering=center,volume=L.volume,score=float(sc),cost=float(cost(x)),mode=21,zero=float(x[-1]),rms=float(np.sqrt(np.mean(df**2))),maxerr=float(max(abs(df))),parameters=x.tolist(),diff=df.tolist(),hkl=hkl[ix].astype(int).tolist())
 if not any(np.allclose(o['cell'][:3],s['cell'][:3],rtol=.003) and np.allclose(o['cell'][3:],s['cell'][3:],atol=.3) for s in sol):sol.append(o)
 sol.sort(key=lambda s:s['cost']);json.dump(sol,open(W+'/index_'+tag+'.json','w'),indent=1)
 print('TRIAL',trial,'sec',time.time()-t0,'cost',o['cost'],'score',sc,'vol',L.volume,'cell',np.round(cell,4),'zero',x[-1],'best',sol[0]['cost'],'diff',np.round(df,4),flush=True)
 if o['maxerr']<.05 and o['cost']<.06 and sc>30:break
 if time.time()-t0>max_time:break
