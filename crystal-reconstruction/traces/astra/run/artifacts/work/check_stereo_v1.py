import sys,json,numpy as np,networkx as nx
from pymatgen.io.cif import CifParser
from rdkit import Chem
sid=sys.argv[1];fn=sys.argv[2] if len(sys.argv)>2 else '/app/results/submission/'+sid+'.cif'
s=CifParser(fn).parse_structures(primitive=False)[0];s.remove_species(['H']);rad=np.array([Chem.GetPeriodicTable().GetRcovalent(x.specie.symbol) for x in s]);D=s.distance_matrix;A=(D>.3)&(D<1.2*(rad[:,None]+rad[None,:]));g=nx.from_numpy_array(A)
for i in g:g.nodes[i]['el']=s[i].specie.symbol
comps=list(nx.connected_components(g));cell=s.lattice
for md in json.load(open('/app/data/instances/'+sid+'/composition.json'))['components']:
 r=Chem.MolFromSmiles(md['smiles']);Chem.AssignStereochemistry(r,cleanIt=True,force=True);expected={a.GetIdx():a.GetProp('_CIPCode') for a in r.GetAtoms() if a.HasProp('_CIPCode')}
 if not expected:continue
 rg=nx.Graph();rg.add_nodes_from((a.GetIdx(),{'el':a.GetSymbol()}) for a in r.GetAtoms());rg.add_edges_from((b.GetBeginAtomIdx(),b.GetEndAtomIdx()) for b in r.GetBonds())
 for co in comps:
  mt=nx.isomorphism.GraphMatcher(rg,g.subgraph(co),node_match=lambda x,y:x['el']==y['el'])
  if not mt.is_isomorphic():continue
  mp=next(mt.isomorphisms_iter());root=mp[0];f={root:s[root].frac_coords.copy()}
  for a,b in nx.bfs_edges(g.subgraph(co),root):
   dist,img=cell.get_distance_and_image(s[a].frac_coords,s[b].frac_coords);f[b]=f[a]+s[b].frac_coords+img-s[a].frac_coords
  rr=Chem.Mol(r);cf=Chem.Conformer(r.GetNumAtoms());rr.RemoveAllConformers()
  for a in rr.GetAtoms():a.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
  for i in range(rr.GetNumAtoms()):cf.SetAtomPosition(i,f[mp[i]]@cell.matrix)
  rr.AddConformer(cf);Chem.AssignStereochemistryFrom3D(rr,replaceExistingTags=True);Chem.AssignStereochemistry(rr,cleanIt=True,force=True)
  got={i:rr.GetAtomWithIdx(i).GetProp('_CIPCode') if rr.GetAtomWithIdx(i).HasProp('_CIPCode') else None for i in expected}
  print(sid,'root',root,'expected',expected,'actual',got,'OK',expected==got)
