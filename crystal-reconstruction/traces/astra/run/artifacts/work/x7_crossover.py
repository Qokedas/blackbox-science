"""Graph-preserving crossover of two independently refined P-1 search basins.
A new search seed, never an automatic final structure.
"""
import os,sys,json,numpy as np,networkx as nx,itertools,gemmi
from rdkit import Chem
from pymatgen.core import Lattice
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif
W='/app/work/X7e382cb';f=float(sys.argv[1]) if len(sys.argv)>1 else .5;tag=sys.argv[2] if len(sys.argv)>2 else 'cross107';R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
A=xml_cryst_file_load_all_object(W+'/refined_ionH88.xml');ca=next(o for o in A if o.GetClassName()=='Crystal');pa=next(o for o in A if o.GetClassName()=='PowderPattern');ma=json.load(open(W+'/search_ionH88/model.json'))
Fa=[np.array([[a.X,a.Y,a.Z] for a in list(ca.GetScatterer(i).GetScatteringComponentList())[:Chem.MolFromSmiles(m['smiles']).GetNumAtoms()]]) for i,m in enumerate(ma)]
block=gemmi.cif.read_file(W+'/refined_fixed105.cif').sole_block();rows=block.find(['_atom_site_type_symbol','_atom_site_fract_x','_atom_site_fract_y','_atom_site_fract_z']);bf=np.array([[float(row[i]) for i in [1,2,3]] for row in rows if row[0]!='H']);Fb=[bf[:18],bf[18:19],bf[19:20]]
cell=json.load(open(W+'/submission_before_fallback.json'))['cell']
for k,v in cell.items():ca.GetPar(k).SetHumanValue(v)
L=Lattice.from_parameters(*[cell[k] for k in ['a','b','c','alpha','beta','gamma']]);M=np.array([ca.FractionalToOrthonormalCoords(*v) for v in np.eye(3)]);shift=np.array([.5,.5,0.]);sm=ma[0]['smiles'];r=Chem.MolFromSmiles(sm);g=nx.Graph();g.add_nodes_from((a.GetIdx(),{'el':a.GetSymbol()}) for a in r.GetAtoms());g.add_edges_from((b.GetBeginAtomIdx(),b.GetEndAtomIdx()) for b in r.GetBonds());ans=[]
for mp in nx.isomorphism.GraphMatcher(g,g,node_match=lambda a,b:a['el']==b['el']).isomorphisms_iter():
 q=np.array([mp[i] for i in range(18)])
 for sign in [1,-1]:
  tt=sign*Fb[0][q]+shift;tt=np.array([b+L.get_distance_and_image(a,b)[1] for a,b in zip(Fa[0],tt)]);err=np.linalg.norm((tt-Fa[0])@M,axis=1);ans.append((np.mean(err**2),tt,sign,q))
best=min(ans,key=lambda x:x[0]);target=[best[1]];print('ANION_RMS',np.sqrt(best[0]),'sign',best[2],'perm',best[3],flush=True)
ans=[]
for pp in [(1,2),(2,1)]:
 for signs in itertools.product([1,-1],repeat=2):
  ts=[];cost=0
  for i,j,sign in zip([1,2],pp,signs):
   b=sign*Fb[j][0]+shift;dd,im=L.get_distance_and_image(Fa[i][0],b);ts.append((b+im)[None]);cost+=dd**2
  ans.append((cost,ts))
best=min(ans,key=lambda x:x[0]);target+=best[1];print('IONS_RMS',np.sqrt(best[0]/2),flush=True)
for m in [ca.GetScatterer(i) for i in range(ca.GetNbScatterer())]:ca.RemoveScatterer(m)
mods=[]
for i,(a,b,md) in enumerate(zip(Fa,target,ma)):
 fr=(1-f)*a+f*b;ideal=np.array(md.get('restraint_coords',md.get('rdkit_coords',np.zeros((1,3)))));m,mo=add_component(ca,md['smiles'],'cross_m'+str(i),coords_override=ideal.copy());xyz=fr@M;ctr=xyz.mean(0)
 if m.GetClassName()=='Molecule':
  for j,v in enumerate(xyz-ctr):at=m.GetAtom(j);at.X,at.Y,at.Z=map(float,v)
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.
 m.X,m.Y,m.Z=ca.OrthonormalToFractionalCoords(*ctr);mods.append(mo)
ca.GetOption(1).SetChoice(0);pa.GetPowderPatternComponent(0).SetExtractionMode(False);pa.Prepare();pa.FitScaleFactorForRw();json.dump(mods,open(R+'/model.json','w'),indent=1);export_cif(ca,R+'/best.cif')
# Avoid exporting the second diagnostic crystal/pattern into the restart XML.
from xml.etree import ElementTree as ET
xml_cryst_file_save_global(R+'/all.xml');tree=ET.parse(R+'/all.xml');root=tree.getroot()
for kind in ['Crystal','PowderPattern']:
 xs=root.findall(kind)
 for el in xs[1:]:root.remove(el)
tree.write(R+'/best.xml',encoding='utf-8');print('CROSSOVER',f,pa.GetRw(),flush=True)
