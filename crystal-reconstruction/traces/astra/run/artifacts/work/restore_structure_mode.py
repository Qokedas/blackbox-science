import sys,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
f=sys.argv[1];objs=xml_cryst_file_load_all_object(f);p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();print('RESTORED_STRUCTURAL_MODE',f,p.GetRw(),flush=True)
xml_cryst_file_save_global(f)
