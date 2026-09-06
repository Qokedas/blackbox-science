import ctypes, numpy as np
_lib=ctypes.CDLL('/app/work/libobj_bridge.so')
_lib.bridge_matrix.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_long,ctypes.c_long]
_lib.bridge_setobs.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_long]
_lib.bridge_march.argtypes=[ctypes.c_void_p]+[ctypes.c_double]*5
_lib.bridge_bumpscale.argtypes=[ctypes.c_void_p,ctypes.c_double]
def profile_matrix(p,d,nref=None):
 p.Prepare();d.GetPowderPatternCalc()
 if nref is None:nref=len(d.GetFhklObsSq())
 a=np.zeros((len(p.GetPowderPatternX()),nref),dtype=np.float64)
 ret=_lib.bridge_matrix(d.int_ptr(),a.ctypes.data,*a.shape)
 if ret<0:raise RuntimeError('Profile matrix failed '+str(ret))
 return a
def set_obs(d,values):
 v=np.ascontiguousarray(values,dtype=np.float64);_lib.bridge_setobs(d.int_ptr(),v.ctypes.data,len(v))
def add_march(d,fraction,coeff,h,k,l):
 _lib.bridge_march(d.int_ptr(),float(fraction),float(coeff),float(h),float(k),float(l))
def set_bump_scale(c,scale):
 _lib.bridge_bumpscale(c.int_ptr(),float(scale))

def exact_pawley(p,d,stolmax=None,rcond=1e-4):
 # Exact linear design matrix at fixed profile, lattice, and background.
 # Retain all overlap couplings; truncate only near-null singular directions.
 d.SetExtractionMode(True,False);p.Prepare();p.FitScaleFactorForRw()
 mat=profile_matrix(p,d);f0=np.asarray(d.GetFhklObsSq());x=np.asarray(p.GetPowderPatternX());weight=np.asarray(p.GetLSQWeight(0));obs=np.asarray(p.GetPowderPatternObs());calc=np.asarray(p.GetPowderPatternCalc());compcalc=np.asarray(d.GetPowderPatternCalc());scale=np.dot(calc-p.GetPowderPatternComponent(1).GetPowderPatternCalc(),compcalc)/np.dot(compcalc,compcalc)
 background=calc-compcalc*scale
 n=min(len(weight),len(x));sel=np.arange(len(f0))
 if stolmax is not None:
  stol=np.asarray(d.GetSinThetaOverLambda())[:len(f0)];sel=sel[stol<=stolmax]
  n=min(n,int(np.searchsorted(x,2*np.arcsin(stolmax*p.GetWavelength())+np.deg2rad(p.GetPar('Zero').GetHumanValue()))))
 a=mat[:n,sel]*scale;target=obs[:n]-background[:n]
 excluded=np.setdiff1d(np.arange(len(f0)),sel)
 if len(excluded):target-=mat[:n,excluded]@f0[excluded]*scale
 sw=np.sqrt(weight[:n]);aw=a*sw[:,None];yw=target*sw
 # Scale columns for numerical stability. Use Le Bail distribution in null modes.
 cs=np.linalg.norm(aw,axis=0);cs=np.maximum(cs,np.max(cs)*1e-9);an=aw/cs
 u,sv,vt=np.linalg.svd(an,full_matrices=False);keep=sv>sv[0]*rcond
 corr=(vt[keep].T@((u[:,keep].T@(yw-aw@f0[sel]))/sv[keep]))/cs
 f=f0[sel]+corr
 # Filter near-null modes also from normal matrix, keeping a PSD covariance.
 av=(vt[keep]*sv[keep,None])*cs[None,:];normal=av.T@av
 chi=np.sum((yw-aw@f)**2);var=float(f@normal@f)
 print('EXACT_PAWLEY','nref',len(sel),'rank',int(keep.sum()),'cond',sv[0]/sv[keep][-1], 'chi2',chi,'netRwp',np.sqrt(chi/max(np.dot(yw,yw),1e-30)),flush=True)
 return dict(matrix=a,normal=normal,obs=f,sel=sel,x=x[:n],weights=weight[:n],profile=target,chi2=chi,var=var)
