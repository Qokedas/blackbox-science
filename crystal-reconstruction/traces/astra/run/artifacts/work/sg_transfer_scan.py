"""Diagnostic transfer of a complete molecular model to another SG of same lattice.
Search the relative origin of the unchanged independent fragments on a quarter grid.
No lattice or output is automatically submitted.
"""
import os,sys,json,itertools,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import export_cif
import lsq_packing
sid,src,modelp,sg,tag=sys.argv[1:6];W='/app/work/'+sid;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
O=xml_cryst_file_load_all_object(src);c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=next(p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternDiffraction');md=json.load(open(modelp))
mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())];pos=np.array([[m.X,m.Y,m.Z] for m in mols]);c.ChangeSpaceGroup(sg);d.SetExtractionMode(False);p.Prepare();pack=lsq_packing.attach_packing(p,c,md);rows=[];best=1e30
for t in itertools.product([0.,.25,.5,.75],repeat=3):
 for m,v in zip(mols,pos+np.array(t)):m.X,m.Y,m.Z=map(float,v)
 p.Prepare();p.FitScaleFactorForRw();pe=lsq_packing.cost(pack);score=p.GetChi2()+pe;row={'shift':t,'Rw':p.GetRw(),'chi2':p.GetChi2(),'packing':pe,'score':score};rows.append(row)
 if score<best:
  best=score;export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');json.dump(md,open(R+'/model.json','w'),indent=1);json.dump(row,open(R+'/best.json','w'),indent=1);print('BEST',row,flush=True)
json.dump(sorted(rows,key=lambda x:x['score']),open(W+'/'+tag+'_scan.json','w'),indent=1);lsq_packing.detach(p,pack)
