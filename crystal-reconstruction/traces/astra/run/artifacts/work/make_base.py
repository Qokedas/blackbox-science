import os,sys,json,numpy as np
import matplotlib
matplotlib.use('Agg')
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst.powderpattern import PowderPattern,wrap_boost_powderpattern
from pyobjcryst.crystal import Crystal
from pyobjcryst._pyobjcryst import LSQ
sid=sys.argv[1];tag=sys.argv[2];sg=sys.argv[3];W='/app/work/'+sid
startxml=W+('/pre_scan_' if os.path.exists(W+'/pre_scan_'+tag+'.xml') else '/fit_')+tag+'.xml'
objs=xml_cryst_file_load_all_object(startxml);c=[x for x in objs if x.GetClassName()=='Crystal'][0];p=[x for x in objs if x.GetClassName()=='PowderPattern'][0]
import pyobjcryst.powderpattern as ppmod
from types import MethodType
ppmod.MethodType=MethodType
wrap_boost_powderpattern(p)
c.ChangeSpaceGroup(sg);c.SetName(sid);p.SetName(sid);d=p.get_crystalline_components()[0]
d.SetExtractionMode(True,True);d.ExtractLeBail(10)
p.quick_fit_profile(pdiff=d,init_profile=False,auto_background=False,plot=False,asym=True,verbose=False)
print('BEFORE_EXTRACTION',p.GetRw(),flush=True)
p.FitScaleFactorForRw()
print('BASE',sid,sg,'Rw',p.GetRw(),'chi2',p.GetChi2(),flush=True)
cell={n:float(c.GetPar(n).GetHumanValue()) for n in ['a','b','c','alpha','beta','gamma']}
import gemmi
out={'cell':cell,'space_group':sg,'space_group_number':gemmi.find_spacegroup_by_name(sg).number}
json.dump(out,open(W+'/lattice.json','w'),indent=1)
# This is a supported lattice hypothesis, updated if later solution tests reject it.
os.makedirs('/app/results/submission',exist_ok=True)
if '--submit' in sys.argv:json.dump(out,open('/app/results/submission/'+sid+'.json','w'),indent=1)
xml_cryst_file_save_global(W+'/base.xml')
np.savez_compressed(W+'/lebail.npz',h=d.GetH(),k=d.GetK(),l=d.GetL(),stol=d.GetSinThetaOverLambda(),f2=d.GetFhklObsSq(),x=p.GetPowderPatternX(),obs=p.GetPowderPatternObs(),calc=p.GetPowderPatternCalc())
p.plot(diff=True,hkl=False);p._plot_fig.savefig(W+'/base.png',dpi=140)
