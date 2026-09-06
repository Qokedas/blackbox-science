import sys,os,time,json,numpy as np,torch,gemmi
from gallop.structure import Structure
from gallop.optim import local
from gallop.optim.swarm import Swarm
from gallop import tensor_prep,zm_to_cart,chi2
from gallop_prepare import prepare
from gallop_io import load_structure
sid=sys.argv[1];run=int(sys.argv[2]) if len(sys.argv)>2 else 1;zp=int(sys.argv[3]) if len(sys.argv)>3 else 1
W='/app/work/'+sid;G=W+'/gallop_'+str(run);torch.set_num_threads(int(os.environ.get('TORCH_THREADS',1)));torch.set_num_interop_threads(1)
if os.path.exists('/app/work/gallop_config.json'):
 for key,val in json.load(open('/app/work/gallop_config.json')).get(sid+':'+str(run),{}).items():os.environ.setdefault(key,str(val))
if not os.path.exists(G+'/structure.json') or '--prepare' in sys.argv:
 mp=next((v.split('=',1)[1] for v in sys.argv if v.startswith('--model=')),None);s,G=prepare(sid,run,zp,rigid='--rigid' in sys.argv,model_path=mp,stolmax=float(os.environ.get('GALLOP_STOL','.21')))
else:s=load_structure(G+'/structure.json')
if '--hscatter' in sys.argv:
 from hydrogen_prefix import enable_hydrogen_prefix
 enable_hydrogen_prefix(s,G+'/model.json')
if '--packing' in sys.argv:
 from gallop_packing import enable_packing
 enable_packing(s,G+'/model.json')
if float(os.getenv('HBOND_COEFF','0'))>0:
 from gallop_hbond import enable_hbonds
 enable_hbonds(s,G+'/model.json')
np.random.seed((int(time.time())+run)%1000000);NP=int(os.environ.get('PARTICLES','128'));IT=int(os.environ.get('ITERATIONS','450'));ns=max(1,NP//32);max_time=float(os.environ.get('SEARCH_TIME',1800));best=1e100;elite_e=None;elite_i=None;t0=time.time();i=0

def save_result(result,i):
 global best,elite_e,elite_i
 mn=float(result['chi_2'].min());ix=int(result['chi_2'].argmin())
 if mn>=best:return
 best=float(mn);elite_e=result['external'][ix].copy();elite_i=result['internal'][ix].copy()
 np.savez_compressed(G+'/best.npz',external=result['external'][ix:ix+1],internal=result['internal'][ix:ix+1],chi2=mn)
 t=tensor_prep.get_all_required_tensors(s,external=result['external'][ix:ix+1],internal=result['internal'][ix:ix+1],requires_grad=False,device=torch.device('cpu'),verbose=False)
 with torch.no_grad():frac=zm_to_cart.get_asymmetric_coords(**t['zm']).detach().numpy()[0]
 np.save(G+'/best_frac.npy',frac)
 sg=gemmi.find_spacegroup_by_name(s.space_group.symbol);text='data_solution\n'
 for name,v in zip(['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma'],s.lattice.parameters):text+=f'_cell_{name} {v:.9f}\n'
 text+=f"_space_group_name_H-M_alt '{sg.xhm()}'\n_space_group_IT_number {sg.number}\nloop_\n_space_group_symop_id\n_space_group_symop_operation_xyz\n"
 for j,op in enumerate(sg.operations()):text+=f"{j+1} '{op.triplet()}'\n"
 text+='loop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n'
 els=[el for z in s.zmatrices for el in z.elements_no_H]
 for j,(el,v) in enumerate(zip(els,frac)):text+=f'{el}{j+1} {el} {v[0]%1:.9f} {v[1]%1:.9f} {v[2]%1:.9f} 1\n'
 open(G+'/best.cif','w').write(text);json.dump({'chi2':float(mn),'Rint':float(np.sqrt(mn/1000)),'iteration':i,'elapsed':time.time()-t0},open(G+'/best.json','w'),indent=1)

while time.time()-t0<max_time and not os.path.exists(G+'/STOP'):
 if i%12==0:
  swarm=Swarm(s,n_particles=NP,n_swarms=ns,global_update=True,global_update_freq=5);ext,intr=swarm.get_initial_positions()
  if 'HEAVY_POOL' in os.environ:
   from gallop_moves import heavy_initialise
   ext,intr=heavy_initialise(s,ext,intr,os.environ['HEAVY_POOL'])
  # Optional warm-start around a chemically sensible best particle.
  if 'START_NPZ' in os.environ:
   warm=np.load(os.environ['START_NPZ']);nn=NP//2;ext[:nn]=warm['external'][0]+np.random.normal(size=ext[:nn].shape)*float(os.environ.get('START_JITTER','.15'));intr[:nn]=warm['internal'][0]+np.random.normal(size=intr[:nn].shape)*float(os.environ.get('START_TOR_JITTER','.4'))
 # Retain a small elite cloud across PSO and reset boundaries.
 if elite_e is not None:
  ne=max(1,int(NP*float(os.environ.get('ELITE_FRAC','.10'))));ext[:ne]=elite_e+np.random.normal(size=ext[:ne].shape)*float(os.environ.get('ELITE_JITTER','.045'));intr[:ne]=elite_i+np.random.normal(size=intr[:ne].shape)*float(os.environ.get('ELITE_TOR_JITTER','.12'));ext[0]=elite_e;intr[0]=elite_i
  nm=max(0,int(NP*float(os.environ.get('MACRO_ELITE_FRAC','.20'))))
  if nm:
   from gallop_moves import macro_mutations
   me,mi=macro_mutations(s,elite_e,elite_i,nm);ext[ne:ne+nm]=me;intr[ne:ne+nm]=mi
 ti=time.time()
 nref=min(len(s.hkl),int(os.environ.get('START_REFL',str(len(s.hkl))))+int(os.environ.get('RAMP_REF_STEP','40'))*(i//int(os.environ.get('RAMP_REF_EVERY','12'))))
 result=local.minimise(s,external=ext,internal=intr,n_reflections=nref,n_iterations=IT,n_cooldown=IT//4,learning_rate=.04,device=torch.device('cpu'),loss='sum',use_progress_bar=False,save_CIF=False,run=i,verbose=False,check_min=25)
 if nref<len(s.hkl):
  ft=tensor_prep.get_all_required_tensors(s,external=result['external'],internal=result['internal'],requires_grad=False,device=torch.device('cpu'),verbose=False)
  with torch.no_grad():full_chi=chi2.get_chi_2(ft['zm'],ft['int_tensors'],ft['chisqd_tensors']).numpy()
  result['low_chi_2']=result['chi_2'].copy();result['chi_2']=full_chi
 print('GALLOP',i,'Nref',nref,'seconds',time.time()-ti,'best',result['chi_2'].min(),'q25',np.quantile(result['chi_2'],.25),'median',np.median(result['chi_2']),'total',time.time()-t0,flush=True)
 save_result(result,i)
 if 'low_chi_2' in result:result['chi_2']=result['low_chi_2']
 ext,intr=swarm.update_position(result=result,verbose=False)
 np.savez_compressed(G+'/last_population.npz',external=result['external'],internal=result['internal'],chi2=result['chi_2'])
 i+=1
 if '--test' in sys.argv or best<float(os.environ.get('TARGET_CHI','2.0')):break
print('FINISHED',sid,best,flush=True)
