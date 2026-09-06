import sys,json,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object
from obj_model import add_component
sid=sys.argv[1];O=xml_cryst_file_load_all_object('/app/work/'+sid+'/base.xml');p=next(o for o in O if o.GetClassName()=='PowderPattern');c=next(o for o in O if o.GetClassName()=='Crystal');d=p.GetPowderPatternComponent(0)
if c.GetNbScatterer()==0:dummy,_=add_component(c,'C','audit_dummy')
d.SetExtractionMode(True,False);p.Prepare();p.FitScaleFactorForRw();print('AUDIT',sid,'Rw',p.GetRw(),'chi2',p.GetChi2(),flush=True)
