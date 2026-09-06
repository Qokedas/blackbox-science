import numpy as np,itertools,os,json
from rdkit import Chem
from rdkit.Chem import AllChem,rdMolTransforms,Lipinski
from pyobjcryst.molecule import Molecule
from pyobjcryst.atom import Atom
from pyobjcryst.scatteringpower import ScatteringPowerAtom
from pyobjcryst.refinableobj import refpartype_scatt_occup,refpartype_scattpow_temperature
import gemmi

def export_cif(c,path):
 cp=[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']]
 sgname=c.GetSpaceGroup().GetName();sg=gemmi.find_spacegroup_by_name(sgname)
 if sg is None: raise Exception(sgname)
 text='data_solution\n'
 for name,v in zip(['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma'],cp):text+=f'_cell_{name} {v:.8f}\n'
 text+=f"_space_group_name_H-M_alt '{sg.xhm()}'\n_space_group_IT_number {sg.number}\nloop_\n_space_group_symop_id\n_space_group_symop_operation_xyz\n"
 for i,op in enumerate(sg.operations()):text+=f"{i+1} '{op.triplet()}'\n"
 text+='loop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n_atom_site_B_iso_or_equiv\n'
 for i,a in enumerate(c.GetScatteringComponentList()):
  if a.mpScattPow is None:continue
  el=a.mpScattPow.GetSymbol();text+=f'{el}{i+1} {el} {a.X%1:.8f} {a.Y%1:.8f} {a.Z%1:.8f} 1.0 {a.mpScattPow.GetBiso():.4f}\n'
 open(path,'w').write(text)

def make_rdkit(smiles,seed=10,nconf=30,conf_rank=0,hydrogen=False):
 r=Chem.AddHs(Chem.MolFromSmiles(smiles));ps=AllChem.ETKDGv3();ps.randomSeed=seed;ps.numThreads=1;ps.pruneRmsThresh=.25
 ids=list(AllChem.EmbedMultipleConfs(r,numConfs=nconf,params=ps))
 if not ids:
  ps.useRandomCoords=True;ids=list(AllChem.EmbedMultipleConfs(r,numConfs=nconf,params=ps))
 try:
  es=AllChem.MMFFOptimizeMoleculeConfs(r,numThreads=1,maxIters=600)
 except Exception:
  es=AllChem.UFFOptimizeMoleculeConfs(r,numThreads=1,maxIters=600)
 ranked=sorted(range(len(ids)),key=lambda i:es[i][1]);ci=ids[ranked[conf_rank%len(ranked)]]
 c=r.GetConformer(ci);coords=c.GetPositions();els=[a.GetSymbol() for a in r.GetAtoms()]
 if not hydrogen:
  keep=[i for i,x in enumerate(els) if x!='H'];coords=coords[keep];r=Chem.RemoveHs(r);els=[a.GetSymbol() for a in r.GetAtoms()]
 # use the selected coordinates, indexed independently of RDKit conformer indices
 return r,coords,es[ranked[conf_rank%len(ranked)]][1]

def add_component(c,smiles,name,seed=10,conf_rank=0,rigid=False,hydrogen=False):
 base=Chem.MolFromSmiles(smiles)
 if base.GetNumHeavyAtoms()==1:
  atom=base.GetAtomWithIdx(0);el=atom.GetSymbol()
  try:sp=c.GetScatteringPower(el)
  except Exception:sp=ScatteringPowerAtom(el,el,3.0);c.AddScatteringPower(sp)
  a=Atom(*np.random.random(3),name,sp,1.0);c.AddScatterer(a);a.SetParIsFixed(refpartype_scatt_occup,True)
  return a,{'elements':[el],'smiles':smiles}
 r,coords,e=make_rdkit(smiles,seed=seed,conf_rank=conf_rank,hydrogen=hydrogen);coords-=coords.mean(axis=0)
 m=Molecule(c,name);ats=[];els=[]
 for i,(at,xyz) in enumerate(zip(r.GetAtoms(),coords)):
  el=at.GetSymbol();els.append(el)
  try:sp=c.GetScatteringPower(el)
  except Exception:sp=ScatteringPowerAtom(el,el,3.0 if el!='H' else 4.0);c.AddScatteringPower(sp)
  ats.append(m.AddAtom(*xyz,sp,name+'_'+el+str(i+1),False))
 for bo in r.GetBonds():
  i,j=bo.GetBeginAtomIdx(),bo.GetEndAtomIdx();dist=np.linalg.norm(coords[i]-coords[j]);m.AddBond(ats[i],ats[j],dist,.02,.025,bo.GetBondTypeAsDouble(),False)
 for a in r.GetAtoms():
  j=a.GetIdx()
  for i,k in itertools.combinations([a.GetIdx() for a in a.GetNeighbors()],2):
   d1=coords[i]-coords[j];d2=coords[k]-coords[j];ang=np.arccos(np.clip(d1@d2/np.linalg.norm(d1)/np.linalg.norm(d2),-1,1));m.AddBondAngle(ats[i],ats[j],ats[k],ang,np.deg2rad(1.5),np.deg2rad(2),False)
 # Freeze each ring system, preserving the embedded chair/fused-ring conformations.
 rings=[set(x) for x in r.GetRingInfo().AtomRings()]
 merged=[]
 while rings:
  s=rings.pop();flag=True
  while flag:
   flag=False
   for t in rings[:]:
    if s&t:s|=t;rings.remove(t);flag=True
  merged.append(s)
 for ring in merged:
  # Add directly attached terminal atoms and hydrogens to aromatic or saturated ring geometry.
  extended=set(ring)
  for i in ring:
   for n in r.GetAtomWithIdx(i).GetNeighbors():
    j=n.GetIdx()
    if n.GetDegree()==1:extended.add(j)
  m.AddRigidGroup([ats[i] for i in sorted(extended)],False)
 # Planarity about multiple and amide bonds, based on the input conformer.
 cf=Chem.Conformer(r.GetNumAtoms())
 for i,v in enumerate(coords):cf.SetAtomPosition(i,v)
 for bo in r.GetBonds():
  i,j=bo.GetBeginAtomIdx(),bo.GetEndAtomIdx()
  ai=r.GetAtomWithIdx(i);aj=r.GetAtomWithIdx(j)
  amide=(ai.GetAtomicNum()==7 and aj.GetAtomicNum()==6 and any(b.GetBondTypeAsDouble()==2 and b.GetOtherAtom(aj).GetAtomicNum() in [8,16] for b in aj.GetBonds())) or (aj.GetAtomicNum()==7 and ai.GetAtomicNum()==6 and any(b.GetBondTypeAsDouble()==2 and b.GetOtherAtom(ai).GetAtomicNum() in [8,16] for b in ai.GetBonds()))
  if bo.IsInRing():continue
  if bo.GetBondTypeAsDouble()>1.1 or amide:
   ni=[a.GetIdx() for a in ai.GetNeighbors() if a.GetIdx()!=j];nj=[a.GetIdx() for a in aj.GetNeighbors() if a.GetIdx()!=i]
   if ni and nj:
    k,l=ni[0],nj[0];angle=rdMolTransforms.GetDihedralRad(cf,k,i,j,l);m.AddDihedralAngle(ats[k],ats[i],ats[j],ats[l],angle,np.deg2rad(3),np.deg2rad(6),False)
 m.GetOption(0).SetChoice(1 if rigid else 2)
 m.GetOption(1).SetChoice(1) # never invert supplied stereochemistry
 m.GetOption(2).SetChoice(1)
 m.X,m.Y,m.Z=np.random.random(3)
 q=np.random.normal(size=4);q/=np.linalg.norm(q);m.Q0,m.Q1,m.Q2,m.Q3=q
 m.SetParIsFixed(refpartype_scatt_occup,True);c.AddScatterer(m)
 return m,{'smiles':smiles,'elements':els,'rdkit_coords':coords.tolist(),'energy':e}
