"""Rietveld test of two inversion-centred biphenyl dicarboxylates.
Each internally centrosymmetric FULL molecule is used at molecular occupancy
1/2 in the calculation (its inversion duplicate gives unit physical occupancy).
The final CIF contains exactly one fully occupied site per inversion orbit.
Molecular geometry and special-position centres remain fixed during this test.
"""
import os,sys,json,numpy as np,gemmi,itertools,types
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst._pyobjcryst import LSQ
from pyobjcryst.refinableobj import *
from obj_model import recenter_molecules
from rdkit import Chem
W='/app/work/X7e382cb';tag='special104';R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
O=xml_cryst_file_load_all_object(W+'/refined_ionHtc103.xml');c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);md=json.load(open(W+'/search_ionHtc103/model.json'));mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())];M=np.array([c.FractionalToOrthonormalCoords(*v) for v in np.eye(3)]);inv=np.linalg.inv(M);F=[np.array([[a.X,a.Y,a.Z] for a in m.GetScatteringComponentList()]) for m in mols]
perm=np.array([12,11,13,10,14,15,7,6,16,17,3,1,0,2,4,5,8,9]);keep=np.where(np.arange(18)<perm)[0]
for j in range(2):
 m=mols[j];n=m.GetNbAtoms();pm=np.r_[perm,np.arange(18,n)];idx={m.GetAtom(i).GetName():i for i in range(n)};nb={i:[] for i in range(n)}
 for bo in m.GetBondList():
  a,b=[idx[x.GetName()] for x in [bo.GetAtom1(),bo.GetAtom2()]];nb[a].append(b);nb[b].append(a)
 for i in range(18,n):
  parent=nb[i][0];pm[i]=next(k for k in nb[perm[parent]] if k>=18)
 assert all(pm[pm[i]]==i for i in range(n));xyz=F[j]@M;loc=(xyz-xyz[pm])/2
 for i,v in enumerate(loc):a=m.GetAtom(i);a.X,a.Y,a.Z=map(float,v)
 m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=([0.,0.,0.] if j==0 else [0.,.5,.5]);m.SetOccupancy(.5)
 for rg in list(m.GetRigidGroupList()):m.RemoveRigidGroup(rg)
for ii,jj in [(2,3),(4,5)]:
 target=(F[ii][0]-F[jj][0]+np.round(F[ii][0]+F[jj][0]))/2;m=mols[ii];old=F[ii][0];delta=target-old;m.X+=delta[0];m.Y+=delta[1];m.Z+=delta[2]
for j in [3,5]:c.RemoveScatterer(mols[j])
mols=[mols[i] for i in [0,1,2,4]];md=[md[i] for i in [0,1,2,4]];c.ChangeSpaceGroup('P -1');c.GetOption(1).SetChoice(0);d.SetExtractionMode(False);p.GetOption(0).SetChoice(1);p.Prepare();p.FitScaleFactorForRw();print('PROJECTED_RWP',p.GetRw(),flush=True)
# Avoid counting a covalent neighbour twice under the exact internal inversion.
text=open('/app/work/lsq_packing.py').read();text=text.replace("    limit=radii.get(els[i],1.4)+radii.get(els[j],1.4)","    if not ident and groups[i]==groups[j] and groups[i]<2 and dm[groups[i]][local[i],special_perm[local[j]]]<=3:continue\n    limit=radii.get(els[i],1.4)+radii.get(els[j],1.4)")
pack=types.ModuleType('special_packing');pack.__dict__['special_perm']=perm;exec(compile(text,'special_packing','exec'),pack.__dict__);pr=pack.attach_packing(p,c,md,sigma=.012)
# Restore meaningful error scale for rigid-body fit.
w=np.array(p.GetLSQWeight(0));xx=np.rad2deg(p.GetPowderPatternX());yy=np.array(p.GetPowderPatternObs());n=min(len(xx),len(w));ss=np.sqrt(max(1.,p.GetChi2()/n))/np.sqrt(np.maximum(w[:n],1e-20));np.savetxt(W+'/special104.xye',np.column_stack([xx[:n],yy[:n],ss]));p.ImportPowderPattern2ThetaObsSigma(W+'/special104.xye');p.Prepare()
lsq=LSQ();lsq.SetRefinedObj(p,0,True,True);lsq.PrepareRefParList(True);ref=lsq.GetCompiledRefinedObj();ref.FixAllPar();lsq.SetParIsFixed(refpartype_scattdata_background,False);lsq.SetParIsFixed(refpartype_scatt_orient,False);lsq.SetParIsFixed(refpartype_scatt_transl,False)
for m in mols[:2]:
 for ip in range(3):lsq.SetParIsFixed(m.GetPar(ip),True)
centres=np.array([[m.X,m.Y,m.Z] for m in mols[:2]])
def save():
 recenter_molecules(c);cp=[c.GetPar(k).GetHumanValue() for k in ['a','b','c','alpha','beta','gamma']];text='data_solution\n'
 for k,v in zip(['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma'],cp):text+=f'_cell_{k} {v:.9f}\n'
 text+="_space_group_name_H-M_alt 'P -1'\n_space_group_IT_number 2\nloop_\n_space_group_symop_id\n_space_group_symop_operation_xyz\n1 'x,y,z'\n2 '-x,-y,-z'\nloop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n_atom_site_B_iso_or_equiv\n";ii=0
 for j,m in enumerate(mols):
  sc=list(m.GetScatteringComponentList());ids=keep if j<2 else [0]
  for i in ids:
   a=sc[i];el=a.mpScattPow.GetSymbol();ii+=1;text+=f'{el}{ii} {el} {a.X%1:.9f} {a.Y%1:.9f} {a.Z%1:.9f} 1.0 {a.mpScattPow.GetBiso():.5f}\n'
 open(W+'/refined_'+tag+'.cif','w').write(text);xml_cryst_file_save_global(W+'/refined_'+tag+'.xml');json.dump(dict(Rw=p.GetRw(),chi2=p.GetChi2(),packing=pack.cost(pr),special_positions=True),open(W+'/refined_'+tag+'.json','w'),indent=1)
save()
for stage in range(3):
 if stage==1:
  lsq.SetParIsFixed(refpartype_scattpow_temperature,False)
  for i in range(len(c.GetScatteringPowerRegistry())):c.GetScatteringPowerRegistry().GetObj(i).SetLimitsAbsolute('Biso',.3,10.)
 if stage==2:
  for k in ['a','b','c','alpha','beta','gamma','Zero','U','V','W','Eta0','Eta1']:
   try:lsq.SetParIsFixed(k,False)
   except:pass
 for it in range(4):
  lsq.SafeRefine(nbCycle=10,useLevenbergMarquardt=True,silent=True);p.FitScaleFactorForRw();assert np.max(np.abs((np.array([[m.X,m.Y,m.Z] for m in mols[:2]])-centres+.5)%1-.5))<1e-6
  print('CYCLE',stage,it,'Rw',p.GetRw(),'packing',pack.cost(pr),flush=True);save()
json.dump(md,open(R+'/model.json','w'),indent=1);pack.detach(p,pr);print('FINISHED',p.GetRw(),flush=True)
