import numpy as np,scipy.special as sp,scipy.optimize as opt,json,os,time
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
W='/app/work/X8a6f5a8';raw=np.loadtxt('/app/data/instances/X8a6f5a8/pattern.xye');raw=raw[(raw[:,0]>=5)&(raw[:,0]<=31)];x,y,ss=raw.T
ps=json.load(open(W+'/peaks_raw.json'));ids=[i for i,p in enumerate(ps) if 5.1<p['two_theta']<30.8];ps0=[ps[i] for i in ids];N=len(ps0);tt=np.array([p['two_theta'] for p in ps0]);height=np.array([p['height'] for p in ps0]);
bx=np.linspace(5,31,18);K=len(bx);bgmat=np.stack([np.interp(x,bx,np.eye(K)[i]) for i in range(K)],axis=1);data=np.load(W+'/processed.npz');b0=np.interp(bx,data['x'],data['background']);bn=5000.;wt=1/ss
p0=np.r_[tt+.045,np.log(np.maximum(height*.32,1)),np.log(.035+.0008*tt),np.log(np.full(N,.20)),b0/bn]
lo=np.r_[tt-.13,np.full(N,-5.),np.full(N,np.log(.008)),np.full(N,np.log(.018)),np.full(K,-.5)]
hi=np.r_[tt+.25,np.full(N,22.),np.full(N,np.log(.14)),np.full(N,np.log(.75)),np.full(K,4.)]
t0=time.time();calls=0
# Mild smoothness of the background; peaks carry all high-frequency signal.
bpen=np.diff(np.eye(K),n=2,axis=0)*6.
def profile(p,jac=False):
 mu=p[:N];A=np.exp(p[N:2*N]);sig=np.exp(p[2*N:3*N]);tau=np.exp(p[3*N:4*N]);d=x[:,None]-mu;z=d/sig+sig/tau;logcdf=sp.log_ndtr(-z);I=np.exp(d/tau+.5*(sig/tau)**2+logcdf)/tau*A
 yc=I.sum(1)+bn*(bgmat@p[4*N:]);res=np.r_[(yc-y)*wt,bpen@p[4*N:]]
 if not jac:return res
 rat=np.exp(-.5*z*z-.5*np.log(2*np.pi)-logcdf)
 mupart=I*(-1/tau+rat/sig)
 sigpart=I*(sig*sig/(tau*tau)+rat*(d/sig-sig/tau))
 taupart=I*(-d/tau-sig*sig/(tau*tau)+rat*sig/tau-1)
 J=np.hstack([mupart,I,sigpart,taupart,bn*bgmat])*wt[:,None]
 J=np.vstack([J,np.pad(bpen,((0,0),(4*N,0)))])
 return J
fit=opt.least_squares(profile,p0,jac=lambda p:profile(p,True),bounds=(lo,hi),x_scale='jac',max_nfev=160,ftol=1e-7,xtol=1e-8,verbose=1)
p=fit.x;np.savez(W+'/emg_global.npz',parameters=p,ids=ids,x=x,ycalc=y+profile(p)[:len(x)]/wt);cov=np.linalg.pinv(fit.jac.T@fit.jac,rcond=1e-9);noise=np.sqrt(np.mean(profile(p)**2));err=np.sqrt(np.maximum(cov.diagonal()[:N],0))*noise
for j,i in enumerate(ids):
 ps[i]['raw_two_theta']=ps[i]['two_theta'];ps[i]['two_theta']=float(p[j]);ps[i]['emg_area']=float(np.exp(p[N+j]));ps[i]['emg_sigma']=float(np.exp(p[2*N+j]));ps[i]['emg_tau']=float(np.exp(p[3*N+j]));ps[i]['emg_error']=float(err[j]);ps[i]['d']=float(1.54059/(2*np.sin(np.deg2rad(p[j]/2))))
 print('PEAK',i+1,ps[i]['raw_two_theta'],'->',p[j],'sig',ps[i]['emg_sigma'],'tau',ps[i]['emg_tau'],'area',ps[i]['emg_area'],'err',err[j],flush=True)
json.dump(ps,open(W+'/peaks_emg.json','w'),indent=1)
fig,ax=plt.subplots(figsize=(14,5));yc=y+profile(p)[:len(x)]/wt;ax.plot(x,y,'k',lw=.7);ax.plot(x,yc,'r',lw=.7);ax.plot(x,y-yc-2000,'b',lw=.5);fig.tight_layout();fig.savefig(W+'/emg_global.png',dpi=130);print('DONE',time.time()-t0,'Rw',np.sqrt(np.sum((y-yc)**2)/np.sum(y*y)),flush=True)
