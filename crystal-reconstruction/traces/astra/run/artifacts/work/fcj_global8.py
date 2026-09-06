"""Independent peak centres with one common FCJ axial-divergence parameter.
Native GSAS-II Fortran powder routines are rebuilt for this container's glibc.
This is a peak-shape diagnostic, not a structural fit.
"""
import numpy as np,scipy.optimize as opt,json,time,ctypes,os
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
W='/app/work/X8a6f5a8';raw=np.loadtxt('/app/data/instances/X8a6f5a8/pattern.xye');raw=raw[(raw[:,0]>=5)&(raw[:,0]<=31)];x,y,ss=raw.T;x=np.ascontiguousarray(x);n=len(x)
lib=ctypes.CDLL('/app/work/libfcj.so');lib.fcj.argtypes=[ctypes.c_int,ctypes.c_void_p]+[ctypes.c_double]*4+[ctypes.c_void_p]
ps=json.load(open(W+'/peaks_raw.json'));em=json.load(open(W+'/peaks_emg.json'));ids=[i for i,p in enumerate(ps) if 5.1<p['two_theta']<30.8];N=len(ids);tt=np.array([ps[i]['two_theta'] for i in ids]);area=np.array([em[i]['emg_area'] for i in ids]);mu0=np.array([em[i]['two_theta']-.025 for i in ids]);bx=np.linspace(5,31,18);K=len(bx);bgmat=np.stack([np.interp(x,bx,np.eye(K)[i]) for i in range(K)],axis=1);data=np.load(W+'/processed.npz');b0=np.interp(bx,data['x'],data['background']);bn=5000.;wt=1/ss
p0=np.r_[np.clip(mu0,tt-.12,tt+.20),np.log(np.maximum(area,1)),np.full(N,np.log(9.)),np.full(N,np.log(1.5)),np.log(.08),b0/bn]
lo=np.r_[tt-.12,np.full(N,-5.),np.full(N,np.log(.4)),np.full(N,np.log(.02)),np.log(.005),np.full(K,-.5)]
hi=np.r_[tt+.20,np.full(N,22.),np.full(N,np.log(220)),np.full(N,np.log(45)),np.log(.35),np.full(K,4.)]
if os.path.exists(W+'/fcj_global.npz') and os.getenv('RESUME','0')=='1':p0=np.load(W+'/fcj_global.npz')['parameters']
bpen=np.diff(np.eye(K),n=2,axis=0)*6.;last=None;cached=None;calls=0;t0=time.time()
def calc(p):
 global last,cached,calls
 if last is not None and np.array_equal(last,p):return cached
 I=np.zeros((n,N));J=np.zeros((n,4*N+1+K));A=np.exp(p[N:2*N]);sig=np.exp(p[2*N:3*N]);gam=np.exp(p[3*N:4*N]);shl=np.exp(p[4*N]);J[:,-K:]=bn*bgmat
 for j in range(N):
  a=np.zeros((5,n));lib.fcj(n,x.ctypes.data,float(p[j]),float(sig[j]),float(gam[j]),float(shl),a.ctypes.data);I[:,j]=A[j]*a[0];J[:,j]=A[j]*a[1];J[:,N+j]=I[:,j];J[:,2*N+j]=A[j]*a[2]*sig[j];J[:,3*N+j]=A[j]*a[3]*gam[j];J[:,4*N]+=A[j]*a[4]*shl
 yc=I.sum(1)+bn*(bgmat@p[-K:]);res=np.r_[(yc-y)*wt,bpen@p[-K:]];J=np.vstack([J*wt[:,None],np.pad(bpen,((0,0),(4*N+1,0)))])
 last=p.copy();cached=(res,J);calls+=1
 if calls%10==0:
  print('FCJ',calls,'cost',res@res,'SHL',shl,'time',time.time()-t0,flush=True);np.savez(W+'/fcj_progress.npz',parameters=p,ids=ids,x=x,ycalc=yc)
 return cached
fit=opt.least_squares(lambda p:calc(p)[0],p0,jac=lambda p:calc(p)[1],bounds=(lo,hi),x_scale='jac',max_nfev=int(os.getenv('MAXFEV','90')),ftol=1e-7,xtol=1e-8,verbose=1)
p=fit.x;yc=y+calc(p)[0][:n]/wt;np.savez(W+'/fcj_global.npz',parameters=p,ids=ids,x=x,ycalc=yc);cov=np.linalg.pinv(fit.jac.T@fit.jac,rcond=1e-9);noise=np.sqrt(np.mean(calc(p)[0]**2));err=np.sqrt(np.maximum(cov.diagonal()[:N],0))*noise
for j,i in enumerate(ids):
 ps[i]['raw_two_theta']=ps[i]['two_theta'];ps[i]['two_theta']=float(p[j]);ps[i]['fcj_area']=float(np.exp(p[N+j]));ps[i]['fcj_sigma']=float(np.exp(p[2*N+j]));ps[i]['fcj_gamma']=float(np.exp(p[3*N+j]));ps[i]['fcj_error']=float(err[j]);ps[i]['d']=float(1.54059/(2*np.sin(np.deg2rad(p[j]/2))));print('PEAK',i+1,ps[i]['raw_two_theta'],'->',p[j],'sig',ps[i]['fcj_sigma'],'gam',ps[i]['fcj_gamma'],'area',ps[i]['fcj_area'],'err',err[j],flush=True)
json.dump(ps,open(W+'/peaks_fcj.json','w'),indent=1)
fig,ax=plt.subplots(figsize=(14,5));ax.plot(x,y,'k',lw=.7);ax.plot(x,yc,'r',lw=.7);ax.plot(x,y-yc-2000,'b',lw=.5);fig.tight_layout();fig.savefig(W+'/fcj_global.png',dpi=130);print('DONE',time.time()-t0,'SHL',np.exp(p[4*N]),'Rw',np.sqrt(np.sum((y-yc)**2)/np.sum(y*y)),flush=True)
