"""Submit one existing native-refined hypothesis for each requested missing CIF.
Keep only candidates whose heavy graph, specified stereochemistry and indexed
space-group type are valid. Back up the indexed JSON before changing it.
No claim that a validation alone establishes convergence.
"""
import sys,os,glob,json,subprocess,shutil,gemmi,numpy as np
from pymatgen.core import Lattice
R='/app/results/submission'
for sid in sys.argv[1:]:
 if os.path.exists(R+'/'+sid+'.cif'):print('ALREADY',sid,flush=True);continue
 W='/app/work/'+sid;j=json.load(open(R+'/'+sid+'.json'));sg=gemmi.find_spacegroup_by_name(j['space_group']);lp=Lattice.from_parameters(*[j['cell'][k] for k in ['a','b','c','alpha','beta','gamma']]).get_niggli_reduced_lattice();ans=[]
 for f in glob.glob(W+'/refined_*.json'):
  try:
   q=json.load(open(f));cf=f[:-5]+'.cif';rw=q.get('Rw');b=gemmi.cif.read_file(cf).sole_block();sg2=gemmi.find_spacegroup_by_name(gemmi.cif.as_string(b.find_value('_space_group_name_H-M_alt')))
   if rw is None or sg2.number!=sg.number:continue
   cp=[float(b.find_value('_cell_'+v)) for v in ['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma']];lc=Lattice.from_parameters(*cp).get_niggli_reduced_lattice();a=np.array(lp.parameters);z=np.array(lc.parameters)
   if max(abs(z[:3]/a[:3]-1))>.005 or max(abs(z[3:]-a[3:]))>.5:continue
   ans.append((rw,cf))
  except Exception:continue
 for rw,cf in sorted(ans):
  v=subprocess.run(['python','/app/work/submit.py',sid,cf,'--check'],capture_output=True,text=True)
  if v.returncode:print('GRAPH_REJECT',sid,cf,flush=True);continue
  st=subprocess.run(['python','/app/work/check_stereo.py',sid,cf],capture_output=True,text=True)
  if st.returncode or 'OK False' in st.stdout:print('STEREO_REJECT',sid,cf,flush=True);continue
  shutil.copyfile(R+'/'+sid+'.json',W+'/submission_before_fallback.json');subprocess.run(['python','/app/work/submit.py',sid,cf],check=True);print('HYPOTHESIS_ADDED',sid,cf,'Rwp',rw,flush=True);break
 else:print('NO_VALID_HYPOTHESIS',sid,flush=True)
