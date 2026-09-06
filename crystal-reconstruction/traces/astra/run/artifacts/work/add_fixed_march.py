"""Create a native ObjCryst model with one fixed March-Dollase term.
Used only for conditional texture tests. Does not write submissions.
"""
import os,sys,shutil
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_bridge import add_march
sid,run,src=sys.argv[1:4];r,h,k,l=map(float,sys.argv[4:8]);W='/app/work/'+sid;R=W+'/search_'+run;os.makedirs(R,exist_ok=True)
objs=xml_cryst_file_load_all_object(src);p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);p.Prepare();p.FitScaleFactorForRw();print('BEFORE',p.GetRw(),flush=True)
add_march(d,1.,r,h,k,l);p.Prepare();p.FitScaleFactorForRw();print('FIXED_MARCH',r,(h,k,l),p.GetRw(),flush=True)
xml_cryst_file_save_global(R+'/best.xml')
if len(sys.argv)>8:shutil.copyfile(sys.argv[8],R+'/model.json')
