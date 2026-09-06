import sys,json,os,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component
import pyobjcryst.powderpattern as pp
from types import MethodType
pp.MethodType=MethodType
from pyobjcryst.powderpattern import PowderPattern, wrap_boost_powderpattern
sid,src,tag=sys.argv[1:4];W='/app/work/'+sid
objs=xml_cryst_file_load_all_object(src);p=next(o for o in objs if o.GetClassName()=='PowderPattern');c=next(o for o in objs if o.GetClassName()=='Crystal');wrap_boost_powderpattern(p);d=p.GetPowderPatternComponent(0)
if c.GetNbScatterer()==0:add_component(c,'C','dummy')
d.SetExtractionMode(True,False);p.Prepare();d.ExtractLeBail(20);p.FitScaleFactorForRw();print('ORIGINAL',p.GetRw(),flush=True)
p.SetWavelength(1.5418 if os.getenv('MONO') else 'Cu');p.Prepare();d.ExtractLeBail(30);p.FitScaleFactorForRw();print('DOUBLETFIXED',p.GetRw(),flush=True)
p.quick_fit_profile(pdiff=d,auto_background=False,init_profile=False,plot=False,asym=True,verbose=False);p.FitScaleFactorForRw();print('DOUBLETFIT',p.GetRw(),flush=True)
xml_cryst_file_save_global(W+'/'+tag+'.xml');cp={n:c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']};json.dump({'cell':cp,'Rw':p.GetRw()},open(W+'/'+tag+'.json','w'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.figure(figsize=(14,5));xx=np.rad2deg(p.GetPowderPatternX());yy=np.array(p.GetPowderPatternObs());cc=np.array(p.GetPowderPatternCalc());plt.plot(xx,yy,'k',lw=.7);plt.plot(xx,cc,'r',lw=.5);plt.plot(xx,yy-cc-yy.max()*.1,'b',lw=.4);plt.title(tag+' '+str(p.GetRw()));plt.savefig(W+'/'+tag+'.png')
