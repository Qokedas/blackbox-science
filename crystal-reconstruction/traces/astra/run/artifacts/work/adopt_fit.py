import sys,os,json,shutil,numpy as np,gemmi
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
sid=sys.argv[1];tag=sys.argv[2];W='/app/work/'+sid
objs=xml_cryst_file_load_all_object(W+'/fit_'+tag+'.xml');c=next(x for x in objs if x.GetClassName()=='Crystal');p=next(x for x in objs if x.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0)
c.SetName(sid);p.SetName(sid)
sg=sys.argv[3] if len(sys.argv)>3 else c.GetSpaceGroup().GetName()
if gemmi.find_spacegroup_by_name(sg).xhm()!=gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName()).xhm():c.ChangeSpaceGroup(sg);d.SetExtractionMode(True,True);p.Prepare();d.ExtractLeBail(30)
d.SetExtractionMode(True,False);p.Prepare();p.FitScaleFactorForRw();rw=p.GetRw();n=len(p.GetLSQWeight(0));factor=max(1.,np.sqrt(p.GetChi2()/n));xx=np.rad2deg(p.GetPowderPatternX())[:n];yy=np.asarray(p.GetPowderPatternObs())[:n];ss=1/np.sqrt(np.maximum(p.GetLSQWeight(0),1e-20))*factor
np.savetxt(W+'/adopted_'+tag+'.xye',np.column_stack([xx,yy,ss]));p.ImportPowderPattern2ThetaObsSigma(W+'/adopted_'+tag+'.xye');p.Prepare();p.FitScaleFactorForRw()
cell={n:float(c.GetPar(n).GetHumanValue()) for n in ['a','b','c','alpha','beta','gamma']};out={'cell':cell,'space_group':sg,'space_group_number':gemmi.find_spacegroup_by_name(sg).number}
json.dump(out,open(W+'/lattice.json','w'),indent=1)
if '--submit' in sys.argv:json.dump(out,open('/app/results/submission/'+sid+'.json','w'),indent=1)
xml_cryst_file_save_global(W+'/base.xml');np.savez_compressed(W+'/lebail.npz',h=d.GetH(),k=d.GetK(),l=d.GetL(),stol=d.GetSinThetaOverLambda(),f2=d.GetFhklObsSq(),x=p.GetPowderPatternX(),obs=p.GetPowderPatternObs(),calc=p.GetPowderPatternCalc())
print('ADOPTED',sid,tag,sg,'Rw',rw,p.GetRw(),'scaled',factor,'cell',cell,flush=True)
