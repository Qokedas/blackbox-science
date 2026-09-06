import sys,os,json,shutil
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import export_cif
sid,src,modelp,cellp,tag=sys.argv[1:6];W='/app/work/'+sid;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
O=xml_cryst_file_load_all_object(src);c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');j=json.load(open(cellp))
for k in ['a','b','c','alpha','beta','gamma']:c.GetPar(k).SetHumanValue(float(j['cell'][k]))
p.GetPowderPatternComponent(0).SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();shutil.copyfile(modelp,R+'/model.json');xml_cryst_file_save_global(R+'/best.xml');export_cif(c,R+'/best.cif');print('RESET_CELL',tag,p.GetRw(),flush=True)
