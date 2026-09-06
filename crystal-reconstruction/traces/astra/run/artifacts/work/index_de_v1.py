import os,sys,time,json,numpy as np
from scipy.optimize import differential_evolution,least_squares
from numba import njit
from pymatgen.core import Lattice
sid=sys.argv[1];W='/app/work/'+sid
ins=json.load(open('/app/data/instances/'+sid+'/instrument.json'));wl=ins['radiation']['wavelength_A'];pf=os.environ.get('PEAK_FILE','peaks_raw.json');peaks=json.load(open(W+'/'+pf))
sf=W+('/peak_select_raw.json' if pf!='peaks.json' else '/peak_select.json')
if os.path.exists(sf):
 si=json.load(open(sf));peaks=[peaks[i-1] for i in si['indices']] if 'indices' in si else [p for p in peaks if p['two_theta']>=si.get('min_two_theta',0)]
peaks=peaks[int(os.environ.get('PEAK_SKIP','0')):][:int(os.environ.get('NPEAK','24'))];tt=np.array([p['two_theta'] for p in peaks]);qobs=(2*np.sin(np.deg2rad(tt/2))/wl)**2
fac=wl**2/(2*np.sin(np.deg2rad(tt)))*180/np.pi
hkl=np.array([(h,k,l) for h in range(0,4) for k in range(-5,6) for l in range(-8,9) if h>0 or (h==0 and k>0) or(h==k==0 and l>0)],dtype=np.float64)
terms=np.array([hkl[:,0]**2,hkl[:,1]**2,hkl[:,2]**2,2*hkl[:,1]*hkl[:,2],2*hkl[:,0]*hkl[:,2],2*hkl[:,0]*hkl[:,1]]).T
nspur=int(os.environ.get('NSPUR','1'));err=float(os.environ.get('TTHERR','.035'))
@njit(cache=False)
def getg(x):
 a,b,c=x[:3];al,be,ga=x[3:6];return np.array([a*a,b*b,c*c,b*c*al,a*c*be,a*b*ga])
@njit(cache=False)
def cost(x):
 g=getg(x);zero=x[6] if len(x)>6 else 0.
 sq=np.zeros(len(qobs));used=np.zeros(len(qobs),dtype=np.int64)
 for i in range(len(qobs)):
  best=1e10;bj=-1;obs=qobs[i]-zero/fac[i]
  for j in range(len(terms)):
   q=0.
   for k in range(6):q+=terms[j,k]*g[k]
   d=abs(q-obs)
   if d<best:best=d;bj=j
  sq[i]=np.log1p((best*fac[i]/err)**2);used[i]=bj
 sq.sort();res=np.mean(sq[:len(sq)-nspur])
 # A mild penalty avoids indexing two well-resolved lines with the same hkl.
 for i in range(len(used)):
  for j in range(i):
   if used[i]==used[j]:res+=.03
 return res
@njit(cache=False)
def assignments(x):
 g=getg(x);zero=x[6] if len(x)>6 else 0.;idx=np.zeros(len(qobs),dtype=np.int64)
 for i in range(len(qobs)):
  best=1e10
  for j in range(len(terms)):
   q=0.
   for k in range(6):q+=terms[j,k]*g[k]
   dd=abs(q-qobs[i]+zero/fac[i])
   if dd<best:best=dd;idx[i]=j
 return idx
bounds=[(1/7.,1/4.3),(1/14.0,1/10.5),(1/24.0,1/19.0),(-.3,.3),(-.3,.3),(-.3,.3),(-.05,.05)]
if '--fixed-c' in sys.argv:bounds[2]=(np.sqrt(qobs[0])*.995,np.sqrt(qobs[0])*1.005)
if 'BROAD' in os.environ:bounds=[(1/11.,1/5.),(1/18.,1/8.),(1/27.,1/12.),(-.5,.5),(-.5,.5),(-.5,.5),(-.08,.08)]
if 'BOUNDS_FILE' in os.environ:bounds=json.load(open(os.environ['BOUNDS_FILE']))
print('INDEX_DE',sid,tt.tolist(),'bounds',bounds,flush=True);cost(np.mean(np.array(bounds),axis=1));sol=[];t0=time.time();tag=os.environ.get('INDEX_TAG','de')
for it in range(int(os.environ.get('TRIALS','40'))):
 res=differential_evolution(cost,bounds,popsize=int(os.environ.get('POPSIZE','18')),maxiter=int(os.environ.get('MAXITER','1000')),tol=.0001,polish=False,workers=1)
 xx=res.x
 for i in range(10):
  idx=assignments(xx);tr=terms[idx]
  def fun(x):return (tr@getg(x)-qobs)*fac+x[6]
  re=least_squares(fun,xx,bounds=np.array(bounds).T,loss='soft_l1',f_scale=err,max_nfev=200)
  if cost(re.x)>cost(xx)+.03:break
  xx=re.x
 g=getg(xx);G=np.array([[g[0],g[5],g[4]],[g[5],g[1],g[3]],[g[4],g[3],g[2]]]);Gi=np.linalg.inv(G);L=Lattice(np.linalg.cholesky(Gi));cp=L.parameters
 idx=assignments(xx);diff=((terms[idx]@g-qobs)*fac+xx[6]);ncal=np.sum((terms@g)<=qobs[-1]);score=qobs[-1]/(2*max(np.mean(np.abs(diff)/fac),1e-10)*max(ncal,1))
 s=dict(cell=list(cp),volume=L.volume,score=float(score),system='TRICLINIC',centering='P',mode=9,cost=float(cost(xx)),zero=float(xx[6]),maxerr=float(np.max(np.abs(diff))),rms=float(np.sqrt(np.mean(diff**2))))
 if not any(np.allclose(s['cell'][:3],p['cell'][:3],rtol=.001) and np.allclose(s['cell'][3:],p['cell'][3:],atol=.15) for p in sol):sol.append(s)
 sol.sort(key=lambda z:z['cost']);json.dump(sol,open(W+'/index_'+tag+'.json','w'),indent=1)
 print('TRIAL',it,'elapsed',time.time()-t0,'cost',s['cost'],'M',score,'cell',np.round(cp,4),'zero',xx[6],'diff',np.round(diff,4),'bestcost',sol[0]['cost'],flush=True)
 if np.max(np.abs(diff))<.035 and s['cost']<.08:break
 if time.time()-t0>float(os.environ.get('INDEX_TIME','900')):break
