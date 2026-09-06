import os,json,numpy as np,time
import matplotlib
matplotlib.use('Agg')
from pyobjcryst.crystal import Crystal
from pyobjcryst.powderpattern import PowderPattern,ReflectionProfileType,SpaceGroupExplorer
sid='Xf8ac963';w='/app/work/'+sid
sol=json.load(open(w+'/index_ORTHOROMBIC_P_0.json'))[0]
cp=sol['cell'];c=Crystal(*cp[:3],*np.deg2rad(cp[3:]),'P 21 21 21');c.SetName(sid)
wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A'];data=np.loadtxt('/app/data/instances/'+sid+'/pattern.xye');sel=(data[:,0]>1.8)&(data[:,0]<np.rad2deg(2*np.arcsin(wl/4)));data=data[sel];np.savetxt(w+'/fit.xye',data)
p=PowderPattern();p.SetName(sid);p.ImportPowderPattern2ThetaObsSigma(w+'/fit.xye');p.SetWavelength(wl);p.SetMaxSinThetaOvLambda(.25)
d=p.AddPowderPatternDiffraction(c);d.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT,np.deg2rad(.018)**2,0,0,.5,0)
b=p.AddPowderPatternBackground();bx=np.linspace(np.deg2rad(data[0,0]),np.deg2rad(data[-1,0]),25);by=np.interp(np.rad2deg(bx),data[:,0],np.load(w+'/processed.npz')['background'][sel]);b.SetInterpPoints(bx,by)
p.Prepare();print('PREPARED',p.GetRw(),flush=True)
p.quick_fit_profile(pdiff=d,auto_background=False,init_profile=False,plot=False,anisotropic=False,asym=False,verbose=True)
print('PROFILE',p.GetRw(),flush=True); print(c)
p.plot(diff=True,hkl=True);p.figure.savefig(w+'/profile_test.png',dpi=140)
print(p.xml());print(c.xml())
sg=SpaceGroupExplorer(d)
for s in ['P 2 2 2','P 21 21 2','P 21 21 21','P b c a','P b c n','P n a 21']:
 try:
  r=sg.Run(s,False,False,True,False)
  print('SG',s,r.hermann_mauguin,r.Rw,r.GoF,r.nGoF,flush=True)
 except Exception as e:print(e)
open(w+'/profile_test.xml','w').write(p.xml())
