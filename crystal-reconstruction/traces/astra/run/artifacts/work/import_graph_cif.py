"""Build whole independent P1 fragments from the perceived heavy graph of a CIF.
For diagnostic Rietveld refinements; the CIF supplies the candidate, not evidence.
"""
import os,sys,json,numpy as np,networkx as nx
from pymatgen.io.cif import CifParser
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif
sid,fn,tag=sys.argv[1:4];W='/app/work/'+sid;R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
s=CifParser(fn).parse_structures(primitive=False)[0];s.remove_species(['H']);rad=np.array([Chem.GetPeriodicTable().GetRcovalent(x.specie.symbol) for x in s]);D=s.distance_matrix;A=(D>.3)&(D<1.2*(rad[:,None]+rad[None,:]));g=nx.from_numpy_array(A)
for i in g:g.nodes[i]['el']=s[i].specie.symbol
components=json.load(open('/app/data/instances/'+sid+'/composition.json'))['components'];templates=[]
for comp in components:
 r=Chem.MolFromSmiles(comp['smiles']);rg=nx.Graph();rg.add_nodes_from((a.GetIdx(),{'el':a.GetSymbol()}) for a in r.GetAtoms());rg.add_edges_from((b.GetBeginAtomIdx(),b.GetEndAtomIdx()) for b in r.GetBonds());templates.append((comp['smiles'],r,rg))
fragments=[]
for co in nx.connected_components(g):
 for sm,r,rg in templates:
  matcher=nx.isomorphism.GraphMatcher(rg,g.subgraph(co),node_match=lambda a,b:a['el']==b['el'])
  if not matcher.is_isomorphic():continue
  mp=next(matcher.isomorphisms_iter());fr=np.array([s[mp[i]].frac_coords for i in range(r.GetNumAtoms())]);seen={0};queue=[0]
  while queue:
   i=queue.pop()
   for a in r.GetAtomWithIdx(i).GetNeighbors():
    j=a.GetIdx()
    if j in seen:continue
    im=s.lattice.get_distance_and_image(fr[i],fr[j])[1];fr[j]+=im;seen.add(j);queue.append(j)
  fragments.append((sm,fr));break
 else:raise ValueError('Unmatched connected component')
O=xml_cryst_file_load_all_object(W+'/base.xml');c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0)
for m in [c.GetScatterer(i) for i in range(c.GetNbScatterer())]:c.RemoveScatterer(m)
c.ChangeSpaceGroup('P 1')
for k,v in zip(['a','b','c','alpha','beta','gamma'],s.lattice.parameters):c.GetPar(k).SetHumanValue(float(v))
M=np.array([c.FractionalToOrthonormalCoords(*v) for v in np.eye(3)]);mods=[]
for j,(sm,fr) in enumerate(fragments):
 xyz=fr@M;m,md=add_component(c,sm,'cif_m'+str(j),coords_override=xyz.copy());ctr=xyz.mean(0)
 if m.GetClassName()=='Molecule':
  for i,v in enumerate(xyz-ctr):a=m.GetAtom(i);a.X,a.Y,a.Z=map(float,v)
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.
 m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*ctr);mods.append(md)
 actual=np.array([[a.X,a.Y,a.Z] for a in list(m.GetScatteringComponentList())]);assert np.max(np.abs((actual-fr+.5)%1-.5))<1e-6
c.GetOption(1).SetChoice(0);d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();json.dump(mods,open(R+'/model.json','w'),indent=1);xml_cryst_file_save_global(R+'/best.xml');export_cif(c,R+'/best.cif');print('GRAPH_IMPORTED',sid,tag,len(mods),'Rw',p.GetRw(),flush=True)
