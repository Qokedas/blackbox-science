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
  # Bond-order-blind C6 graphs cannot distinguish phenyl and cyclohexyl.
  # Select the isomorphism whose observed bond lengths best respect the
  # supplied aromaticity/multiple bonds before assigning stereochemistry.
  def map_cost(mp):
   ans=0.
   for bo in r.GetBonds():
    i,j=bo.GetBeginAtomIdx(),bo.GetEndAtomIdx();es={r.GetAtomWithIdx(i).GetSymbol(),r.GetAtomWithIdx(j).GetSymbol()};bd=bo.GetBondTypeAsDouble()
    target=1.40 if bo.GetIsAromatic() and es=={'C'} else 1.35 if bo.GetIsAromatic() else 1.23 if bd==2 and 'O' in es else 1.29 if bd==2 and 'N' in es else 1.34 if bd==2 else 1.52 if es=={'C'} else 1.43 if 'O' in es else 1.46 if 'N' in es else 1.75 if 'Cl' in es else 1.90 if 'Br' in es else 1.77 if 'S' in es else 1.5
    ans+=(D[mp[i],mp[j]]-target)**2
   return ans
  mp=min(mt.isomorphisms_iter(),key=map_cost);root=mp[0];f={root:s[root].frac_coords.copy()}
  for a,b in nx.bfs_edges(g.subgraph(co),root):
   dist,img=cell.get_distance_and_image(s[a].frac_coords,s[b].frac_coords);f[b]=f[a]+s[b].frac_coords+img-s[a].frac_coords
  rr=Chem.Mol(r);cf=Chem.Conformer(r.GetNumAtoms());rr.RemoveAllConformers()
  for a in rr.GetAtoms():a.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
  for i in range(rr.GetNumAtoms()):cf.SetAtomPosition(i,f[mp[i]]@cell.matrix)
  rr.AddConformer(cf);Chem.AssignStereochemistryFrom3D(rr,replaceExistingTags=True);Chem.AssignStereochemistry(rr,cleanIt=True,force=True)
  got={i:rr.GetAtomWithIdx(i).GetProp('_CIPCode') if rr.GetAtomWithIdx(i).HasProp('_CIPCode') else None for i in expected}
  print(sid,'root',root,'expected',expected,'actual',got,'OK',expected==got)
