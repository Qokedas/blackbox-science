"""Conditional one-axis March-Dollase test against the exact native profile matrix.
No intensity extraction; only a scale is fitted at each trial texture coefficient.
"""
import os,sys,json,itertools,numpy as np
from scipy.optimize import minimize_scalar
from pymatgen.core import Lattice
from pyobjcryst.io import xml_cryst_file_load_all_object
from obj_bridge import profile_matrix
src,out=sys.argv[1:3];objs=xml_cryst_file_load_all_object(src);p=next(o for o in objs if o.GetClassName()=='PowderPattern');c=next(o for o in objs if o.GetClassName()=='Crystal');d=p.GetPowderPatternComponent(0);p.Prepare();p.FitScaleFactorForRw();f=np.asarray(d.GetFhklCalcSq());M=profile_matrix(p,d,len(f));cp=np.asarray(d.GetPowderPatternCalc());print('MATRIX_ERROR',np.linalg.norm(M@f-cp)/np.linalg.norm(cp),flush=True)
x=np.asarray(p.GetPowderPatternX());w=np.asarray(p.GetLSQWeight(0));obs=np.asarray(p.GetPowderPatternObs());calc=np.asarray(p.GetPowderPatternCalc());bg=np.asarray(p.GetPowderPatternComponent(1).GetPowderPatternCalc());scale=np.dot(calc-bg,cp)/np.dot(cp,cp);bg=calc-scale*cp
n=min(len(w),len(obs));w=w[:n];A=M[:n]*np.sqrt(w)[:,None];t=(obs-bg)[:n]*np.sqrt(w);normal=A.T@A;rhs=A.T@t;tt=t@t;denom=obs[:n]@(w*obs[:n]);nf=len(f)
hkl=np.asarray([d.GetH(),d.GetK(),d.GetL()]).T[:nf];lat=Lattice.from_parameters(*[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']]);B=lat.reciprocal_lattice_crystallographic.matrix;g=hkl@B;gn=np.linalg.norm(g,axis=1)
def chi(v):return float(tt-max(v@rhs,0)**2/max(v@normal@v,1e-30))
baseline=chi(f);res=[]
for axis in itertools.product(range(-1,2),repeat=3):
 if not any(axis) or next(v for v in axis if v)!=1:continue
 u=np.asarray(axis)@B;co=((g@u)/(gn*np.linalg.norm(u)))**2
 def fun(lr):
  r=np.exp(lr);md=(r*r*co+(1-co)/r)**-1.5;return chi(f*md)
 fit=minimize_scalar(fun,bounds=(np.log(.4),np.log(2.5)),method='bounded');res.append(dict(axis=axis,MD=float(np.exp(fit.x)),chi2=float(fit.fun),Rw=float(np.sqrt(max(0,fit.fun)/denom))))
res.sort(key=lambda x:x['chi2']);print('BASELINE',p.GetRw(),np.sqrt(baseline/denom),baseline,flush=True)
for r in res[:5]:print(r,flush=True)
json.dump(dict(baseline_Rw=float(p.GetRw()),baseline_chi2=baseline,scan=res),open(out,'w'),indent=1)
