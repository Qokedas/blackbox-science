import os,sys,json,time,numpy as np
from scipy.optimize import least_squares
from numba import njit
from pymatgen.core import Lattice
sid=sys.argv[1];W='/app/work/'+sid;tag=sys.argv[2] if len(sys.argv)>2 else '0';start=json.load(open(W+'/fit_'+tag+'.json'));L=Lattice.from_parameters(*start['cell']);G=L.reciprocal_lattice_crystallographic.metric_tensor;wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A'];ps=json.load(open(W+'/peaks_raw.json'));selection=json.load(open(os.environ.get('SELECT_FILE',W+'/peak_select_ext.json')))['indices'];pp=[ps[i-1] for i in selection];tt=np.array([p['two_theta'] for p in pp]);qobs=(2*np.sin(np.deg2rad(tt/2))/wl)**2;fac=wl*wl/(2*np.sin(np.deg2rad(tt)))*180/np.pi
kl=np.array([[k,l] for k in range(-8,9) for l in range(-12,13) if k or l],dtype=float);kt=np.array([kl[:,0]**2,kl[:,1]**2,2*kl[:,0]*kl[:,1]]).T
v=np.array([G[1,1],G[2,2],G[1,2],start.get('p_pars',{}).get('Zero',0)])
# Low-angle lines below the first possible h != 0 reflection determine the 2D reciprocal net.
ttmax=float(os.environ.get('PLANE_MAX','17.65'))
low=tt<ttmax
for it in range(5):
 q=kt@v[:3];idx=np.argmin(abs(q[None,:]-(qobs-v[3]/fac)[:,None]),axis=1);err=(q[idx]-qobs)*fac+v[3];sel=low&(abs(err)<float(os.environ.get('PLANE_ERR','.10')))
 if sel.sum()<5:raise Exception('not enough 2D matches')
 v=least_squares(lambda x:(kt[idx[sel]]@x[:3]-qobs[sel])*fac[sel]+x[3],v,loss='soft_l1',f_scale=.015,max_nfev=100).x
q=kt@v[:3];idx=np.argmin(abs(q[None,:]-(qobs-v[3]/fac)[:,None]),axis=1);err=(q[idx]-qobs)*fac+v[3]
need=np.where((abs(err)>.055)&(~low))[0]
print('PLANE',sid,'g22,g33,g23,zero',v.tolist(),'nlow',sum(sel),flush=True)
for i,(t,ee) in enumerate(zip(tt,err)):print('LINE',selection[i],round(t,5),'0kl',kl[idx[i]],'err',round(ee,5),'NEW' if i in need else '',flush=True)
# Peak ids can be specified manually when a weak impurity lies outside the 2D net.
if 'H1_IDS' in os.environ:need=np.array([selection.index(int(s)) for s in os.environ['H1_IDS'].split(',')],int)
if len(need)<3:raise Exception('not enough out-of-plane lines')
qcor=qobs-v[3]/fac;ks=np.array([[k,l] for k in range(-5,6) for l in range(-9,10) if k or l],dtype=float)
hkl=np.array([[h,k,l] for h in range(0,4) for k in range(-8,9) for l in range(-12,13) if h or k or l],dtype=float);terms=np.array([hkl[:,0]**2,hkl[:,1]**2,hkl[:,2]**2,2*hkl[:,1]*hkl[:,2],2*hkl[:,0]*hkl[:,2],2*hkl[:,0]*hkl[:,1]]).T
nspur=int(os.environ.get('NSPUR','1'));vmin=float(os.environ.get('VMIN','1000'));vmax=float(os.environ.get('VMAX','1800'));targetv=float(os.environ.get('VTARGET','1300'));etol=.04
@njit(cache=False)
def evaluate(g):
 sq=np.zeros(len(qobs));vol=1/np.sqrt(g[0]*g[1]*g[2]+2*g[3]*g[4]*g[5]-g[0]*g[3]*g[3]-g[1]*g[4]*g[4]-g[2]*g[5]*g[5]);idx=np.zeros(len(qobs),np.int64)
 qc=terms@g
 for i in range(len(qobs)):
  best=1e20;bj=0
  for j in range(len(qc)):
   delta=abs(qc[j]-qcor[i])
   if delta<best:best=delta;bj=j
  sq[i]=np.log1p((best*fac[i]/etol)**2);idx[i]=bj
 sq.sort();res=np.mean(sq[:len(sq)-nspur])*vol/targetv
 return res,idx
@njit(cache=False)
def enumerate_solutions(i1,i2,i3):
 out=np.zeros((len(ks)*len(ks),7));nout=0;g=np.array([qcor[i1],v[0],v[1],v[2],0.,0.]);area=g[1]*g[2]-g[3]*g[3]
 for a in range(len(ks)):
  k,l=ks[a];rhs2=qcor[i2]-g[0]-g[1]*k*k-g[2]*l*l-2*g[3]*k*l
  for b in range(len(ks)):
   m,n=ks[b];det=k*n-m*l
   if abs(det)<.1:continue
   rhs3=qcor[i3]-g[0]-g[1]*m*m-g[2]*n*n-2*g[3]*m*n
   g[5]=(rhs2*n-rhs3*l)/(2*det);g[4]=(rhs3*k-rhs2*m)/(2*det)
   dg=g[0]*area+2*g[3]*g[4]*g[5]-g[1]*g[4]*g[4]-g[2]*g[5]*g[5]
   if dg<=0:continue
   vol=1/np.sqrt(dg)
   if vol<vmin or vol>vmax:continue
   # Reduce equivalent h=1 origins: the reciprocal (100) line should not be much longer than others.
   cost,idx=evaluate(g)
   if cost>.6:continue
   out[nout,0]=cost;out[nout,1:]=g;nout+=1
 return out[:nout]
t0=time.time();out=[]
# The first extra line is taken as (100); two others span the metric cross terms.
for i2,i3 in [(need[1],need[2]),(need[1],need[3]) if len(need)>3 else (need[1],need[2])]:
 rows=enumerate_solutions(need[0],i2,i3);rows=rows[np.argsort(rows[:,0])][:80];print('ENUM',sid,'anchors',tt[[need[0],i2,i3]],'nsolutions',len(rows),'seconds',time.time()-t0,flush=True)
 for row in rows:
  g=row[1:];cost,idx=evaluate(g);x=np.r_[g,v[3]]
  for it in range(3):
   tr=terms[idx]
   re=least_squares(lambda xx:(tr@xx[:6]-qobs)*fac+xx[6],x,loss='soft_l1',f_scale=.02,max_nfev=100);x=re.x
   qc=terms@x[:6];idx=np.argmin(abs(qc[None,:]-(qobs-x[6]/fac)[:,None]),axis=1)
  g=x[:6];gm=np.array([[g[0],g[5],g[4]],[g[5],g[1],g[3]],[g[4],g[3],g[2]]])
  if np.linalg.det(gm)<=0:continue
  cell=Lattice(np.linalg.cholesky(np.linalg.inv(gm))).get_niggli_reduced_lattice();di=(terms[idx]@g-qobs)*fac+x[6];sq=np.sort(np.log1p((di/etol)**2));cost=np.mean(sq[:len(sq)-nspur])*cell.volume/targetv
  ncal=np.sum((terms@g)<qobs[-1]);score=qobs[-1]/(2*np.mean(abs(di)/fac)*ncal)
  if any(np.allclose(cell.parameters[:3],s['cell'][:3],rtol=.002) and np.allclose(cell.parameters[3:],s['cell'][3:],atol=.3) for s in out):continue
  ss=dict(cell=list(cell.parameters),volume=cell.volume,score=float(score),system='TRICLINIC',centering='P',sg='P -1',mode=12,cost=float(cost),zero=float(x[6]),rms=float(np.sqrt(np.mean(di**2))),maxerr=float(max(abs(di))),source='2d_completion');out.append(ss)
 out.sort(key=lambda s:s['cost']);json.dump(out,open(W+'/index_'+os.environ.get('INDEX_TAG','2d')+'.json','w'),indent=1)
for s in out[:15]:print('SOLUTION',s,flush=True)
