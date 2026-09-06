"""Enumerate 2-D reciprocal nets from early lines, then complete monoclinic b*.
Uses the common-FCJ peak centres, independent of prior candidate metrics.
"""
import os,sys,time,itertools,json,numpy as np,gemmi
from numba import njit
from scipy.optimize import least_squares
from pymatgen.core import Lattice
sid='X8a6f5a8';W='/app/work/'+sid;ps=json.load(open(W+'/peaks_fcj.json'));sel=json.load(open(W+'/peak_select_fcj.json'))['indices'];tt=np.array([ps[i-1]['two_theta'] for i in sel]);wl=1.54059;q=(2*np.sin(np.deg2rad(tt/2))/wl)**2;fac=wl**2/(2*np.sin(np.deg2rad(tt)))*180/np.pi;zero=.009;qq=q-zero/fac;n=len(q);tol=float(os.getenv('TTHERR','.03'))
hl=np.array([[h,l] for h in range(0,9) for l in range(-8,9) if h or l>0],float);T2=np.array([hl[:,0]**2,hl[:,1]**2,2*hl[:,0]*hl[:,1]]).T
@njit
def plane_score(g,z):
 qc=T2@g;di=np.empty(n);ix=np.empty(n,np.int64)
 for i in range(n):
  ds=np.abs((qc-q[i])*fac[i]+z);j=np.argmin(ds);di[i]=(qc[j]-q[i])*fac[i]+z;ix[i]=j
 return di,ix
planes=[];t0=time.time()
# Axial basis vectors may be twice or three times a primitive reciprocal vector.
for i,j in [(0,1),(0,3),(1,3),(0,4),(1,4)]:
 for a,c in itertools.product([1,2],repeat=2):
  A=qq[i]/a**2;C=qq[j]/c**2
  for k in range(2,12):
   if k in [i,j]:continue
   for h,l in itertools.product(range(1,4),range(1,4)):
    D=(qq[k]-A*h*h-C*l*l)/(2*h*l)
    if A*C-D*D<=0 or abs(D)/np.sqrt(A*C)>.87:continue
    g=np.array([A,C,D]);di,ix=plane_score(g,zero);use=np.abs(di)<.045
    if use[:12].sum()<5:continue
    v=np.r_[g,zero]
    for it in range(3):
     use=np.abs(di)<.045
     if sum(use)<6:break
     fit=least_squares(lambda x:(T2[ix[use]]@x[:3]-q[use])*fac[use]+x[3],v,loss='soft_l1',f_scale=.015,max_nfev=60);v=fit.x;di,ix=plane_score(v[:3],v[3])
    if sum(np.abs(di)<.035)<8 or abs(v[3])>.06 or v[0]*v[1]<=v[2]**2:continue
    if any(np.allclose(v[:3],p[:3],rtol=.001,atol=1e-6) for p in planes):continue
    planes.append(v)
print('PLANES',len(planes),'seconds',time.time()-t0,flush=True)
np.save(W+'/fcj_planes.npy',planes)
lo=float(os.getenv('VMIN','1000'));hi=float(os.getenv('VMAX','4100'));outs=[]
for sgname in ['P 1 21 1','C 1 2 1']:
 sg=gemmi.find_spacegroup_by_name(sgname);ops=sg.operations();hk=np.array([[h,k,l] for h in range(0,9) for k in range(0,11) for l in range(-8,9) if (h or k or l>0) and not ops.is_systematically_absent([h,k,l])],float);T=np.array([hk[:,0]**2,hk[:,1]**2,hk[:,2]**2,2*hk[:,0]*hk[:,2]]).T;vf=.5 if sg.centring_type()=='C' else 1
 @njit
 def score(v,screen=False):
  det=v[1]*(v[0]*v[2]-v[3]*v[3])
  if det<=0:return 1e5,np.zeros(n,np.int64),np.zeros(n)
  vol=1/np.sqrt(det);qc=T@v[:4];di=np.empty(n);ix=np.empty(n,np.int64);bad=0
  for i in range(n):
   best=1e5
   for j in range(len(qc)):
    e=(qc[j]-q[i])*fac[i]+v[4]
    if abs(e)<best:best=abs(e);ix[i]=j;di[i]=e
   if i<12 and abs(di[i])>.09:
    bad+=1
    if screen and bad>2:return 1e5,ix,di
  ss=np.log1p((di/tol)**2);ss.sort();val=np.mean(ss[:-1])*vol*vf/1800
  if vol<lo/vf or vol>hi/vf:val+=10
  return val,ix,di
 @njit
 def complete(v):
  rows=np.zeros((40000,6));nc=0;area=v[0]*v[1]-v[2]**2
  if area<=0:return rows[:0]
  qc0=T[:,0]*v[0]+T[:,2]*v[1]+T[:,3]*v[2]
  for i in range(n):
   for j in range(len(qc0)):
    if T[j,1]==0:continue
    B=(q[i]-v[3]/fac[i]-qc0[j])/T[j,1]
    if B<1/40**2 or B>1/3**2:continue
    vol=1/np.sqrt(B*area)
    if vol<lo/vf or vol>hi/vf:continue
    vv=np.array([v[0],B,v[1],v[2],v[3]]);cc,ix,di=score(vv,True)
    if cc<1.25 and nc<len(rows):rows[nc,0]=cc;rows[nc,1:]=vv;nc+=1
  return rows[:nc]
 candidates=[]
 for i,v in enumerate(planes):
  rows=complete(v);rows=rows[np.argsort(rows[:,0])][:20]
  for r in rows:
   if any(np.allclose(r[1:5],z[1:5],rtol=.003,atol=1e-6) for z in candidates):continue
   candidates.append(r)
  if i%20==0:print('COMPLETE',sgname,i,len(candidates),'seconds',time.time()-t0,flush=True)
 for row in sorted(candidates,key=lambda x:x[0])[:150]:
  v=row[1:]
  for it in range(5):
   cc,ix,di=score(v);fit=least_squares(lambda x:(T[ix]@x[:4]-q)*fac+x[4],v,loss='soft_l1',f_scale=.020,max_nfev=75);v=fit.x
  cc,ix,di=score(v)
  G=np.array([[v[0],0,v[3]],[0,v[1],0],[v[3],0,v[2]]])
  if np.linalg.det(G)<=0 or cc>2 or abs(v[4])>.10:continue
  lat=Lattice(np.linalg.cholesky(np.linalg.inv(G)));red=list(lat.get_niggli_reduced_lattice().parameters)
  if any(s['sg']==sgname and np.allclose(s['reduced'][:3],red[:3],rtol=.002) and np.allclose(s['reduced'][3:],red[3:],atol=.3) for s in outs):continue
  outs.append(dict(cell=list(lat.parameters),sg=sgname,system='MONOCLINIC',centering=sg.centring_type(),volume=lat.volume,cost=float(cc),score=float(1/max(cc,1e-10)),zero=float(v[4]),diff=di.tolist(),hkl=hk[ix].astype(int).tolist(),reduced=red))
 outs.sort(key=lambda x:x['cost']);json.dump(outs,open(W+'/index_fcjplanes.json','w'),indent=1)
 for o in outs[:8]:print('BEST',o['cost'],o['sg'],np.round(o['cell'],5),o['zero'],np.round(o['diff'],4),flush=True)
print('DONE',time.time()-t0,flush=True)
