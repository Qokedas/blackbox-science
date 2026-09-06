import sys,os,json,time,numpy as np,gemmi
from scipy.optimize import least_squares
from pymatgen.core import Lattice
from numba import njit
sid=sys.argv[1];W='/app/work/'+sid;idx=int(sys.argv[2]) if len(sys.argv)>2 else 0
start=json.load(open(os.getenv('START_CELLS',W+'/candidates_metric.json')))[idx];L=Lattice.from_parameters(*start['cell']);G=L.reciprocal_lattice_crystallographic.metric_tensor
ps=json.load(open(W+'/'+os.getenv('PEAK_FILE','peaks_raw.json')));select=json.load(open(os.getenv('SELECT_FILE',W+'/peak_select_raw.json')))['indices'];ps=[ps[i-1] for i in select];tt=np.array([p['two_theta'] for p in ps]);wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A'];q=(2*np.sin(np.deg2rad(tt/2))/wl)**2;fac=wl*wl/(2*np.sin(np.deg2rad(tt)))*180/np.pi
n=len(q);hl=np.array([[h,l] for h in range(0,10) for l in range(-12,13) if h or l>0],float);T0=np.array([hl[:,0]**2,hl[:,1]**2,2*hl[:,0]*hl[:,1]]).T
x=np.array([G[0,0],G[2,2],G[0,2],start.get('zero',0.)]);fixed_ids=[int(i) for i in os.getenv('PLANE_IDS','').split(',') if i]
for it in range(5):
 dif=(T0@x[:3]-q[:,None])*fac[:,None]+x[3];ix=np.argmin(abs(dif),axis=1);di=dif[np.arange(n),ix];use=np.array([i in fixed_ids for i in select]) if fixed_ids else abs(di)<float(os.getenv('PLANE_ERR','.05'))
 fit=least_squares(lambda v:(T0[ix[use]]@v[:3]-q[use])*fac[use]+v[3],x,loss='soft_l1',f_scale=.015);x=fit.x
print('PLANE',idx,x.tolist(),'USE',[s for s,u in zip(select,use) if u],flush=True)
print('DIFFS',np.round((T0@x[:3]-q[:,None])[np.arange(n),ix]*fac+x[3],4),flush=True)
lo=float(os.getenv('VMIN','1100'));hi=float(os.getenv('VMAX','8000'));tar=float(os.getenv('VTARGET','2800'));err=float(os.getenv('TTHERR','.035'));nspur=int(os.getenv('NSPUR','0'));out=[]
for sgname in os.getenv('SG_NAMES','P 1 21 1;C 1 2 1').split(';'):
 sg=gemmi.find_spacegroup_by_name(sgname);ops=sg.operations();vfac=.5 if sg.centring_type()=='C' else 1.;hkl=np.array([[h,k,l] for h in range(0,12) for k in range(0,17) for l in range(-12,13) if (h or k or l>0) and not ops.is_systematically_absent([h,k,l])],float);T=np.array([hkl[:,0]**2,hkl[:,1]**2,hkl[:,2]**2,2*hkl[:,0]*hkl[:,2]]).T
 @njit(cache=False)
 def score(v):
  qc=T@v[:4];df=np.zeros(n);ii=np.zeros(n,np.int64)
  for i in range(n):
   bd=1e20
   for j in range(len(qc)):
    d=abs((qc[j]-q[i])*fac[i]+v[4])
    if d<bd:bd=d;ii[i]=j
   df[i]=(qc[ii[i]]-q[i])*fac[i]+v[4]
  det=v[1]*(v[0]*v[2]-v[3]*v[3])
  if det<=0:return 1e5,ii,df
  vol=1/np.sqrt(det);ss=np.log1p((df/err)**2);ss.sort();cost=np.mean(ss[:n-nspur])*vol/tar*vfac
  if vol<lo or vol>hi:cost+=10
  return cost,ii,df
 for hmult in [1,2]:
  xx=x.copy();xx[0]/=hmult**2;xx[2]/=hmult
  AC=np.array([xx[0],xx[1],xx[2]]);pterms=T[:,[0,2,3]]@AC
  bs=[]
  for qq,fa in zip(q,fac):
   vals=(qq-xx[3]/fa-pterms)/(T[:,1]+1e-20);bs.extend(vals[(T[:,1]>0)&(vals>1/40**2)&(vals<1/3.0**2)])
  bs=np.unique(np.round(bs,8));rows=[]
  for bb in bs:
   v=np.array([xx[0],bb,xx[1],xx[2],xx[3]]);cost,ii,di=score(v)
   if cost<2.:rows.append((cost,v))
  rows.sort(key=lambda z:z[0]);print('ENUM',sgname,hmult,len(bs),len(rows),flush=True)
  for c0,v in rows[:80]:
   for it in range(4):
    cc,ii,di=score(v);v=least_squares(lambda vv:(T[ii]@vv[:4]-q)*fac+vv[4],v,loss='soft_l1',f_scale=err,max_nfev=80).x
   co,ii,di=score(v);g=v[:4];GM=np.array([[g[0],0,g[3]],[0,g[1],0],[g[3],0,g[2]]])
   if np.linalg.det(GM)<=0:continue
   lat=Lattice(np.linalg.cholesky(np.linalg.inv(GM)));re=list(lat.get_niggli_reduced_lattice().parameters)
   if lat.volume<lo or lat.volume>hi:continue
   if any(s['sg']==sgname and np.allclose(re[:3],s['reduced'][:3],rtol=.003) and np.allclose(re[3:],s['reduced'][3:],atol=.3) for s in out):continue
   out.append(dict(cell=list(lat.parameters),system='MONOCLINIC',centering=sg.centring_type(),sg=sgname,score=1/max(co,1e-12),cost=co,volume=lat.volume,zero=float(v[4]),diff=di.tolist(),hkl=hkl[ii].astype(int).tolist(),reduced=re,plane_index=idx,hmult=hmult,mode=32))
  out.sort(key=lambda s:s['cost']);json.dump(out,open(W+'/index_'+os.getenv('INDEX_TAG','axis'+str(idx))+'.json','w'),indent=1)
for o in out[:12]:print('BEST',o['cost'],o['sg'],np.round(o['cell'],5),o['zero'],np.round(o['diff'],4),flush=True)
