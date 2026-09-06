import json,os,glob,warnings,numpy as np,networkx as nx,gemmi,runpy,sys,contextlib,io
from pymatgen.io.cif import CifParser
from rdkit import Chem
warnings.filterwarnings('ignore')
R='/app/results/submission';report=[]
for p in sorted(glob.glob(R+'/*.json')):
 sid=os.path.basename(p)[:-5];j=json.load(open(p));sg=gemmi.find_spacegroup_by_name(j['space_group']);rec={'id':sid,'json_sg':sg.xhm() if sg else None,'json_sg_num':sg.number if sg else None};assert sg and sg.number==j.get('space_group_number',sg.number)
 fn=R+'/'+sid+'.cif'
 if os.path.exists(fn):
  blocks=gemmi.cif.read_file(fn);assert len(blocks)==1;b=blocks.sole_block();g2=gemmi.find_spacegroup_by_name(gemmi.cif.as_string(b.find_value('_space_group_name_H-M_alt')));assert g2
  cp=[float(b.find_value('_cell_'+v)) for v in ['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma']];jp=[j['cell'][k] for k in ['a','b','c','alpha','beta','gamma']];rec['cell_agrees']=bool(np.allclose(cp,jp,atol=.00005));rec['sg_agrees']=g2.number==sg.number
  assert rec['cell_agrees'] and rec['sg_agrees']
  assert all(abs(float(v)-1)<1.e-5 for v in b.find_values('_atom_site_occupancy'))
  s=CifParser(fn).parse_structures(primitive=False)[0];s.remove_species(['H']);rec['nheavy']=len(s);rad=np.array([Chem.GetPeriodicTable().GetRcovalent(x.specie.symbol) for x in s]);D=s.distance_matrix;A=(D>.3)&(D<1.2*(rad[:,None]+rad[None,:]));g=nx.from_numpy_array(A);cs=list(nx.connected_components(g));rec['sizes']=sorted(map(len,cs))
  for i in g:g.nodes[i]['el']=s[i].specie.symbol
  matched=set();ratios=[]
  for co in json.load(open('/app/data/instances/'+sid+'/composition.json'))['components']:
   r=Chem.MolFromSmiles(co['smiles']);rg=nx.Graph();rg.add_nodes_from((a.GetIdx(),{'el':a.GetSymbol()}) for a in r.GetAtoms());rg.add_edges_from((bo.GetBeginAtomIdx(),bo.GetEndAtomIdx()) for bo in r.GetBonds());ms=[i for i,c in enumerate(cs) if nx.is_isomorphic(g.subgraph(c),rg,node_match=lambda a,b:a['el']==b['el'])];matched.update(ms);ratios.append(len(ms)/co['count'])
  rec['graph_ok']=len(matched)==len(cs) and min(ratios)>0 and max(ratios)==min(ratios);rec['Z']=ratios[0];assert rec['graph_ok']
  out=io.StringIO();sys.argv=['/app/work/check_stereo.py',sid,fn]
  with contextlib.redirect_stdout(out):runpy.run_path('/app/work/check_stereo.py',run_name='__main__')
  rec['stereochemistry']=out.getvalue().strip();assert 'OK False' not in rec['stereochemistry'];print(sid,'CIF graph/stereo/cell/SG validated','Nat',len(s),flush=True)
 else:print(sid,'JSON only',sg.xhm(),flush=True)
 report.append(rec)
json.dump(report,open('/app/work/submission_audit.json','w'),indent=1)
print('DONE',len(report),'instances',sum('nheavy' in x for x in report),'CIFs',flush=True)
