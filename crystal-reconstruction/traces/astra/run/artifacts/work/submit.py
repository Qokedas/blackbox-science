import os,sys,json,shutil,numpy as np,networkx as nx,gemmi
from pymatgen.io.cif import CifParser
from rdkit import Chem
sid=sys.argv[1];f=sys.argv[2]
s=CifParser(f).parse_structures(primitive=False)[0];s.remove_species(['H']);r=np.array([Chem.GetPeriodicTable().GetRcovalent(x.specie.symbol) for x in s]);D=s.distance_matrix;A=(D>.3)&(D<(r[:,None]+r[None,:])*1.2);g=nx.from_numpy_array(A);cs=list(nx.connected_components(g));print(sid,'Nat',len(s),'molecule sizes',[len(c) for c in cs])
for i in g:g.nodes[i]['el']=s[i].specie.symbol
matched=set();ratios=[]
for comp in json.load(open('/app/data/instances/'+sid+'/composition.json'))['components']:
 rm=Chem.MolFromSmiles(comp['smiles']);rg=nx.Graph();rg.add_nodes_from((a.GetIdx(),{'el':a.GetSymbol()}) for a in rm.GetAtoms());rg.add_edges_from((b.GetBeginAtomIdx(),b.GetEndAtomIdx()) for b in rm.GetBonds());matches=[j for j,co in enumerate(cs) if nx.is_isomorphic(g.subgraph(co),rg,node_match=lambda a,b:a['el']==b['el'])];matched|=set(matches);ratios.append(len(matches)/comp['count']);print('  component',comp['smiles'],'matches',len(matches))
valid=len(matched)==len(cs) and min(ratios)>0 and max(ratios)==min(ratios)
if not valid:raise Exception('Connectivity validation failed')
print('  bond range',np.min(D[A]),np.max(D[A]) if A.any() else None)
print('  min intermolecular distance',min((D[i,j] for ii,co in enumerate(cs) for co2 in cs[ii+1:] for i in co for j in co2),default=0))
if '--check' in sys.argv:sys.exit(0)
b=gemmi.cif.read_file(f).sole_block();keys=['a','b','c','alpha','beta','gamma'];ct=['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma'];out={'cell':{k:float(b.find_value('_cell_'+v)) for k,v in zip(keys,ct)},'space_group':gemmi.cif.as_string(b.find_value('_space_group_name_H-M_alt')),'space_group_number':int(b.find_value('_space_group_IT_number'))}
shutil.copyfile(f,'/app/results/submission/'+sid+'.cif');json.dump(out,open('/app/results/submission/'+sid+'.json','w'),indent=1)
print('SUBMITTED',sid)
