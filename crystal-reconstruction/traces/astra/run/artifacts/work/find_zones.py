import os,sys,json,time,numpy as np
from numba import njit
from scipy.optimize import least_squares
sid=sys.argv[1];W='/app/work/'+sid
ps=json.load(open(W+'/peaks_raw.json'));sf=os.getenv('SELECT_FILE',W+'/peak_select_raw.json');select=json.load(open(sf))['indices'] if os.path.exists(sf) else list(range(1,len(ps)+1));select=select[:int(os.getenv('NPEAK','24'))];ps=[ps[i-1] for i in select]
wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A'];tt=np.array([p['two_theta'] for p in ps]);q=(2*np.sin(np.deg2rad(tt/2))/wl)**2;fac=wl*wl/(2*np.sin(np.deg2rad(tt)))*180/np.pi
hk=np.array([[h,k] for h in range(0,19) for k in range(-18,19) if h or k>0],float);T=np.array([hk[:,0]**2,hk[:,1]**2,2*hk[:,0]*hk[:,1]]).T
err=float(os.getenv('TTHERR','.035'));nm=len(tt);amin=float(os.getenv('AREA_MIN','80'));amax=float(os.getenv('AREA_MAX','700'));nlow=min(int(os.getenv('NLOW','14')),len(tt));nh=min(int(os.getenv('NANCHOR','7')),len(tt));vneed=int(os.getenv('NEED','9'))
@njit(cache=False)
def ev(g,z):
 qc=T@g;ix=np.zeros(nm,np.int64);diff=np.zeros(nm);num=0;nlo=0;cost=0.
 for i in range(nm):
  mn=1e20
  for j in range(len(qc)):
   d=abs(qc[j]-q[i]+z/fac[i])
   if d<mn:mn=d;ix[i]=j
  diff[i]=(qc[ix[i]]-q[i])*fac[i]+z
  if abs(diff[i])<err:
   num+=1
   if i<nlow:nlo+=1
  cost+=min((diff[i]/err)**2,1.)
 return num,nlo,cost,ix,diff
@njit(cache=False)
def enum(z):
 out=np.zeros((50000,6));nr=0;qc=q-z/fac
 for i1 in range(nh):
  for i2 in range(i1+1,nh):
   for mult1 in [1,2,3]:
    for mult2 in [1,2,3]:
     a=qc[i1]/(mult1*mult1);b=qc[i2]/(mult2*mult2)
     for i3 in range(min(13,nm)):
      if i3==i1 or i3==i2:continue
      for h in range(1,5):
       for k in range(1,5):
        cross=(qc[i3]-h*h*a-k*k*b)/(2*h*k)
        if abs(cross)/np.sqrt(a*b)>.999:continue
        area=1/np.sqrt(a*b-cross*cross)
        if area<amin or area>amax:continue
        g=np.array([a,b,cross]);num,nlo,cost,ix,dd=ev(g,z)
        if nlo<vneed:continue
        # Reward coverage, but heavily penalize an unnecessarily large net.
        score=nlo+0.3*(num-nlo)-area/1200-cost*.025
        out[nr,0]=score;out[nr,1:4]=g;out[nr,4]=z;out[nr,5]=area;nr+=1
        if nr>=50000:return out[:nr]
 return out[:nr]
t0=time.time();rows=[]
for z in [-.12,-.06,0.,.06,.12]:
 rr=enum(z);rr=rr[np.argsort(-rr[:,0])][:120]
 rows.extend(rr);print('ENUM',sid,z,len(rr),time.time()-t0,flush=True)
rows=sorted(rows,key=lambda r:-r[0]);out=[]
for row in rows:
 x=row[1:5];num,nlo,cost,ix,dd=ev(x[:3],x[3])
 for j in range(4):
  use=abs(dd)<err*1.5
  if use.sum()<4:break
  fit=least_squares(lambda v:(T[ix[use]]@v[:3]-q[use])*fac[use]+v[3],x,loss='soft_l1',f_scale=err*.5,max_nfev=100);x=fit.x;num,nlo,cost,ix,dd=ev(x[:3],x[3])
 G=np.array([[x[0],x[2]],[x[2],x[1]]])
 # Gauss-reduce the reciprocal planar basis; observed peaks need not be near-orthogonal basis vectors.
 for itr in range(30):
  if G[0,0]>G[1,1]:G=G[[1,0]][:,[1,0]]
  m=int(np.round(G[0,1]/G[0,0]));B=np.array([[1.,0.],[-m,1.]])
  if m==0:break
  G=B@G@B.T
 x[:3]=[G[0,0],G[1,1],G[0,1]]
 num,nlo,cost,ix,dd=ev(x[:3],x[3]);det=np.linalg.det(G)
 if det<=0:continue
 area=1/np.sqrt(det);J=np.linalg.inv(G);a=np.sqrt(J[0,0]);b=np.sqrt(J[1,1]);angle=np.degrees(np.arccos(J[0,1]/(a*b)))
 if angle<40 or angle>140 or area>amax or area<amin:continue
 score=nlo+.3*(num-nlo)-area/1200-cost*.025
 v=dict(plane_metric=x[:3].tolist(),zero=float(x[3]),area=float(area),axes=[a,b,angle],nmatch=int(num),nlow=int(nlo),score=float(score),hkl=hk[ix].astype(int).tolist(),diff=dd.tolist(),indices=select)
 if any(np.allclose(v['plane_metric'],o['plane_metric'],rtol=.003,atol=1e-6) for o in out):continue
 out.append(v)
out.sort(key=lambda r:-r['score']);json.dump(out,open(W+'/'+os.getenv('ZONES_FILE','zones.json'),'w'),indent=1)
for o in out[:12]:print('ZONE',o['score'],o['nlow'],o['nmatch'],o['area'],o['axes'],o['zero'],flush=True)
print('DONE',time.time()-t0,flush=True)
