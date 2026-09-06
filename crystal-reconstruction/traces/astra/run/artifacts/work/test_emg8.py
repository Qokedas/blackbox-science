import numpy as np,scipy.special as ss,scipy.optimize as so,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
W='/app/work/X8a6f5a8';data=np.loadtxt('/app/data/instances/X8a6f5a8/pattern.xye')
def emg(x,mu,sigma,tau):
 z=(x-mu)/sigma+sigma/tau
 # exp(mu...) * erfc(z/sqrt2), stable log probability.
 return np.exp((x-mu)/tau+.5*(sigma/tau)**2+ss.log_ndtr(-z))/tau
fig,axs=plt.subplots(2,2,figsize=(12,7))
res=[]
for ax,(lo,hi,mu) in zip(axs.ravel(),[(4.8,6.3,5.61),(7.5,8.8,8.25),(17.4,18.55,18.35),(26.1,27.15,26.825)]):
 a=data[(data[:,0]>lo)&(data[:,0]<hi)];x,y,s=a.T
 def fun(p):
  u,logsig,logtau,logarea,b0,b1=p;return emg(x,u,np.exp(logsig),np.exp(logtau))*np.exp(logarea)+b0+b1*(x-mu)
 p=[mu,.0+np.log(.04),np.log(.16),np.log((y.max()-y.min())*.25),y.min(),0]
 bounds=([mu-.10,np.log(.008),np.log(.005),0,0,-5000],[mu+.30,np.log(.20),np.log(2.),20,y.max(),5000])
 fit=so.least_squares(lambda p:(fun(p)-y)/s,p,bounds=bounds,max_nfev=500)
 p=fit.x;print('FIT',mu,'->',p[0], 'sigma,tau',np.exp(p[1:3]),'rw',np.sqrt(np.sum((fun(p)-y)**2)/np.sum(y*y)))
 ax.plot(x,y,'.',ms=2,c='black');ax.plot(x,fun(p),c='red');ax.axvline(p[0],c='blue',lw=.6);ax.set_title('EMG center %.5f sigma %.4f tau %.4f'%(p[0],np.exp(p[1]),np.exp(p[2])))
 res.append(p.tolist())
fig.tight_layout();fig.savefig(W+'/emg_test.png',dpi=130);json.dump(res,open(W+'/emg_test.json','w'),indent=1)
