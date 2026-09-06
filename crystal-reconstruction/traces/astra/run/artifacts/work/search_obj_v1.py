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
   m,md=add_component(c,co['smiles'],f'm{z}_{ic}_{j}',seed=seed+ic*21+z,conf_rank=run,rigid='--rigid' in sys.argv,hydrogen='--hydrogen' in sys.argv);models.append(md)
json.dump(models,open(R+'/model.json','w'),indent=1)
c.GetOption(1).SetChoice(0) # no dynamical occupancy correction
c.SetParIsFixed(refpartype_scattpow_temperature,True);c.SetParIsFixed(refpartype_scatt_occup,True)
d.SetExtractionMode(False)
p.SetMaxSinThetaOvLambda(.20 if '--lowres' in sys.argv else .25)
p.Prepare();p.FitScaleFactorForRw()
mc=MonteCarlo(sid+'_'+str(run));mc.AddRefinableObj(p);mc.AddRefinableObj(c);mc.SetParIsFixed(refpartype_scatt_occup,True);mc.SetParIsFixed(refpartype_scattpow_temperature,True)
initial=mc.GetLogLikelihood();print('INITIAL',sid,run,'Rw',p.GetRw(),'LLK',initial,'Integrated',p.GetIntegratedChi2(),'DOF',c.GetNbParNotFixed(),flush=True)
mc.SetAlgorithmParallTempering(AnnealingSchedule.EXPONENTIAL,max(100,initial*.04),max(.005,initial*.000005),AnnealingSchedule.SMART,16,.08)
best=1e100;t0=time.time();nrun=0
while time.time()-t0<float(os.environ.get("SEARCH_TIME",3600)) and not os.path.exists(R+'/STOP'):
 # Each independent tempering run starts randomised; initial conformer retained in molecule geometry restraints.
 if nrun:mc.RandomizeStartingConfig()
 t1=time.time();mc.Optimize(1000000 if nrun else 100000, max_time=600)
 mc.RestoreBestConfiguration();cost=mc.GetLogLikelihood();rw=p.GetRw()
 print('RUN',nrun,'steps',1000000 if nrun else 100000,'time',time.time()-t1,'total',time.time()-t0,'LLK',cost,'Rw',rw,'Integrated',p.GetIntegratedChi2(),flush=True)
 if cost<best:
  best=cost;export_cif(c,R+'/best.cif');xml_cryst_file_save_global(R+'/best.xml');json.dump({'llk':cost,'Rw':rw,'elapsed':time.time()-t0,'run':nrun},open(R+'/best.json','w'),indent=1)
 nrun+=1
 if '--test' in sys.argv:break
 if rw<float(os.environ.get('TARGET_RW',.09)):break
print('FINISHED',best,flush=True)
