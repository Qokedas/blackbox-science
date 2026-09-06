import os,sys,time,json,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst.globaloptim import MonteCarlo,AnnealingSchedule
from pyobjcryst.refinableobj import refpartype_scatt_occup,refpartype_scattpow_temperature
from obj_model import add_component,export_cif
sid=sys.argv[1];run=int(sys.argv[2]) if len(sys.argv)>2 else 0;zprime=int(sys.argv[3]) if len(sys.argv)>3 else 1
W='/app/work/'+sid;R=W+'/search_'+str(run);os.makedirs(R,exist_ok=True);seed=int(time.time())%100000+run;np.random.seed(seed)
base_path=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--base=')),W+'/base.xml')
objs=xml_cryst_file_load_all_object(base_path);c=[x for x in objs if x.GetClassName()=='Crystal'][0];p=[x for x in objs if x.GetClassName()=='PowderPattern'][0];d=[p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternDiffraction'][0]
comp=json.load(open('/app/data/instances/'+sid+'/composition.json'))
model_path=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--model=')),W+'/model_smiles.json')
if os.path.exists(model_path):comp=json.load(open(model_path))
models=[]
for z in range(zprime):
 for ic,co in enumerate(comp['components']):
  for j in range(co['count']):
   m,md=add_component(c,co['smiles'],f'm{z}_{ic}_{j}',seed=seed+ic*21+z,conf_rank=run,rigid='--rigid' in sys.argv,hydrogen='--hydrogen' in sys.argv,coords_override=co.get('coords'),unique_sp='--fullbump' in sys.argv);models.append(md)
json.dump(models,open(R+'/model.json','w'),indent=1)
if '--bump' in sys.argv or '--fullbump' in sys.argv:
 from antibump import add_antibump
 add_antibump(c,models,full='--fullbump' in sys.argv,scale=float(os.environ.get('BUMP_SCALE','10')))
c.GetOption(1).SetChoice(0) # no dynamical occupancy correction
c.SetParIsFixed(refpartype_scattpow_temperature,True);c.SetParIsFixed(refpartype_scatt_occup,True)
# Older bases may have disproportionate experimental errors. Rescale by the base Le Bail chi-squared.
if '--rescale' in sys.argv:
 d.SetExtractionMode(True,False);p.Prepare();d.ExtractLeBail(20);p.Prepare();p.FitScaleFactorForRw()
 n=len(p.GetLSQWeight(0));scale=max(1.,np.sqrt(p.GetChi2()/n))
 xx=np.rad2deg(p.GetPowderPatternX())[:n];yy=np.array(p.GetPowderPatternObs())[:n];ss=1/np.sqrt(np.maximum(p.GetLSQWeight(0),1e-20))*scale
 np.savetxt(R+'/scaled.xye',np.column_stack([xx,yy,ss]));p.ImportPowderPattern2ThetaObsSigma(R+'/scaled.xye');p.Prepare()
 print('RESCALED_BASE',scale,p.GetRw(),p.GetChi2(),flush=True)
d.SetExtractionMode(False)
p.SetMaxSinThetaOvLambda(.20 if '--lowres' in sys.argv else .25)
if '--profile' in sys.argv:p.GetOption(0).SetChoice(1)
# Remove the continuous origin freedom from polar groups.
import gemmi
sgnum=gemmi.find_spacegroup_by_name(c.GetSpaceGroup().GetName()).number
if c.GetNbScatterer()>0 and sgnum in [1,3,4,5]:
 origin=c.GetScatterer(0)
 for name in (['x','y','z'] if sgnum==1 else ['y']):
  try:origin.SetParIsFixed(name,True)
  except:pass
p.Prepare();p.FitScaleFactorForRw()
mc=MonteCarlo(sid+'_'+str(run));mc.AddRefinableObj(p);mc.AddRefinableObj(c);mc.SetParIsFixed(refpartype_scatt_occup,True);mc.SetParIsFixed(refpartype_scattpow_temperature,True)
initial=mc.GetLogLikelihood();print('INITIAL',sid,run,'Rw',p.GetRw(),'LLK',initial,'Integrated',p.GetIntegratedChi2(),'DOF',c.GetNbParNotFixed(),flush=True)
mc.SetAlgorithmParallTempering(AnnealingSchedule.EXPONENTIAL,max(100,initial*float(os.environ.get('TEMP_MAX_FRAC','.04'))),max(.005,initial*float(os.environ.get('TEMP_MIN_FRAC','.000005'))),AnnealingSchedule.SMART,float(os.environ.get('MUT_MAX','16')),float(os.environ.get('MUT_MIN','.08')))
if '--lsq' in sys.argv:mc.GetOption(5).SetChoice(int(os.environ.get('MC_LSQ','0')))
best=1e100;t0=time.time();nrun=0
while time.time()-t0<float(os.environ.get("SEARCH_TIME",3600)) and not os.path.exists(R+'/STOP'):
 # Each independent tempering run starts randomised; initial conformer retained in molecule geometry restraints.
 if nrun:mc.RandomizeStartingConfig()
 t1=time.time();mc.Optimize(int(os.environ.get('MC_STEPS','1000000')) if nrun else 100000, max_time=float(os.environ.get('MC_RUN_TIME','600')))
 mc.RestoreBestConfiguration();cost=mc.GetLogLikelihood();rw=p.GetRw()
 print('RUN',nrun,'steps',int(os.environ.get('MC_STEPS','1000000')) if nrun else 100000,'time',time.time()-t1,'total',time.time()-t0,'LLK',cost,'Rw',rw,'Integrated',p.GetIntegratedChi2(),flush=True)
 if cost<best:
  best=cost;export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');json.dump({'llk':cost,'Rw':rw,'elapsed':time.time()-t0,'run':nrun},open(R+'/best.json','w'),indent=1)
 nrun+=1
 if '--test' in sys.argv:break
 if rw<float(os.environ.get('TARGET_RW',.09)):break
print('FINISHED',best,flush=True)
