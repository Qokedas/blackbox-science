import sys,os,time,json,itertools,numpy as np
import matplotlib
matplotlib.use('Agg')
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst._pyobjcryst import LSQ
from pyobjcryst.scatteringpower import ScatteringPowerAtom
from pyobjcryst.refinableobj import *
from obj_model import export_cif,recenter_molecules,add_aromatic_planarity
sid=sys.argv[1];run=sys.argv[2] if len(sys.argv)>2 else '1';W='/app/work/'+sid
src=W+'/search_'+run+'/best.xml' if len(sys.argv)<4 else sys.argv[3]
objs=xml_cryst_file_load_all_object(src);c=[o for o in objs if o.GetClassName()=='Crystal'][0];p=[o for o in objs if o.GetClassName()=='PowderPattern'][0]
d=[p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternDiffraction'][0]
mods=json.load(open(W+'/search_'+run+'/model.json'));mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())]
p.Prepare()
print('START',p.GetRw(),p.GetChi2(),flush=True)
# Add geometrically generated hydrogens to the molecular model, keeping all heavy-atom positions unchanged.
if '--noH' not in sys.argv:
 try:hs=c.GetScatteringPower('H')
 except:hs=ScatteringPowerAtom('H','H',4.0);c.AddScatteringPower(hs)
 for m,md in zip(mols,mods):
  if m.GetClassName()!='Molecule':continue
  r=Chem.MolFromSmiles(md['smiles']);n=r.GetNumAtoms()
  ac=m.GetScatteringComponentList()[0];old_xyz=np.array([ac.X,ac.Y,ac.Z])
  if m.GetNbAtoms()!=n:continue
  cf=Chem.Conformer(n)
  for i in range(n):
   a=m.GetAtom(i);cf.SetAtomPosition(i,(a.X,a.Y,a.Z))
  r.AddConformer(cf);rh=Chem.AddHs(r,addCoords=True);xyz=rh.GetConformer().GetPositions()
  for i in range(n,rh.GetNumAtoms()):
   h=m.AddAtom(*xyz[i],hs,m.GetName()+'_H'+str(i+1),False)
   j=rh.GetAtomWithIdx(i).GetNeighbors()[0].GetIdx();parent=m.GetAtom(j);bl=float(np.linalg.norm(xyz[i]-xyz[j]));m.AddBond(parent,h,bl,.02,.015,1,False)
   for nb in rh.GetAtomWithIdx(j).GetNeighbors():
    k=nb.GetIdx()
    if k==i or k>=i:continue
    v1=xyz[i]-xyz[j];v2=xyz[k]-xyz[j];ang=np.arccos(np.clip(v1@v2/np.linalg.norm(v1)/np.linalg.norm(v2),-1,1));m.AddBondAngle(h,parent,m.GetAtom(k),ang,np.deg2rad(2),np.deg2rad(2),False)
   for rg in range(m.GetNbRigidGroups()):
    group=m.GetRigidGroupList()[rg]
    if parent in group:group.add(h)
   # Aromatic atoms and nitrile terminal atoms require no additional torsions.
  ac=m.GetScatteringComponentList()[0];new_xyz=np.array([ac.X,ac.Y,ac.Z]);delta=old_xyz-new_xyz
  m.X+=delta[0];m.Y+=delta[1];m.Z+=delta[2]
 c.SetParIsFixed(refpartype_scattpow_temperature,True)
# Optional extension to higher-angle observations for a final coordinate refinement.
new_stol=next((float(a.split('=',1)[1]) for a in sys.argv if a.startswith('--stol=')),None)
if new_stol is not None:
 ins=json.load(open('/app/data/instances/'+sid+'/instrument.json'));wl=ins['radiation']['wavelength_A'];raw=np.loadtxt('/app/data/instances/'+sid+'/pattern.xye')
 lo=np.rad2deg(p.GetPowderPatternX()[0]);hi=np.rad2deg(2*np.arcsin(new_stol*wl));raw=raw[(raw[:,0]>=lo)&(raw[:,0]<hi)]
 nbin=max(1,int(np.ceil(len(raw)/12000)))
 if nbin>1:
  n=len(raw)//nbin*nbin;raw=np.column_stack([raw[:n,0].reshape(-1,nbin).mean(1),raw[:n,1].reshape(-1,nbin).mean(1),np.sqrt((raw[:n,2]**2).reshape(-1,nbin).sum(1))/nbin])
 data0=np.load(W+'/processed.npz');b=[p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternBackground'][0]
 bx0=np.array(b.GetInterpPointsX());by0=np.array(b.GetInterpPointsY());step=np.median(np.diff(bx0));extra=np.arange(bx0[-1]+step,np.deg2rad(raw[-1,0])+step,step)
 byextra=np.interp(np.rad2deg(extra),data0['x'],data0['background']);b.SetInterpPoints(np.r_[bx0,extra],np.r_[by0,byextra])
 np.savetxt(W+'/extended_'+run+'.xye',raw);p.ImportPowderPattern2ThetaObsSigma(W+'/extended_'+run+'.xye');p.SetMaxSinThetaOvLambda(new_stol);p.Prepare()
 print('EXTENDED',new_stol,len(raw),'Rw',p.GetRw(),flush=True)
p.GetOption(0).SetChoice(1) # use the point-by-point profile for Rietveld refinement
p.Prepare();p.FitScaleFactorForRw()
print('WITH_H',p.GetRw(),p.GetChi2(),flush=True)
if '--scale' in sys.argv:
 wgt=np.array(p.GetLSQWeight(0));xx=np.rad2deg(p.GetPowderPatternX());yy=np.array(p.GetPowderPatternObs())
 n=min(len(xx),len(wgt));scale=np.sqrt(max(1.,p.GetChi2()/n))
 ss=1/np.sqrt(np.maximum(wgt[:n],1e-20))*scale
 np.savetxt(W+'/scaled_refine.xye',np.column_stack([xx[:n],yy[:n],ss]));p.ImportPowderPattern2ThetaObsSigma(W+'/scaled_refine.xye');p.Prepare()
 print('SCALED_SIGMA',scale,p.GetChi2(),flush=True)

if '--tight' in sys.argv:
 for m in mols:
  if m.GetClassName()!='Molecule':continue
  for bo in m.GetBondList():
   if bo.GetAtom1().GetScatteringPower().GetSymbol()!='H' and bo.GetAtom2().GetScatteringPower().GetSymbol()!='H':bo.SetLengthSigma(.006);bo.SetLengthDelta(.008)
  for an in m.GetBondAngleList():
   if all(a.GetScatteringPower().GetSymbol()!='H' for a in [an.GetAtom1(),an.GetAtom2(),an.GetAtom3()]):an.SetAngleSigma(np.deg2rad(.8));an.SetAngleDelta(np.deg2rad(1.))
 print('TIGHT_RESTRAINTS',flush=True)
if '--keep-rigid' not in sys.argv:
 for m in mols:
  if m.GetClassName()=='Molecule':
   for rg in list(m.GetRigidGroupList()):m.RemoveRigidGroup(rg)
 print('FLEXIBLE_RINGS',flush=True)
if '--no-planarity' not in sys.argv:
 nplan=0
 for m,md in zip(mols,mods):
  if m.GetClassName()=='Molecule':nplan+=add_aromatic_planarity(m,md['smiles'],md.get('rdkit_coords'))
 print('AROMATIC_PLANARITY',nplan,flush=True)
packing_restraint=None
if '--no-packing' not in sys.argv:
 import lsq_packing
 packing_restraint=lsq_packing.attach_packing(p,c,mods)
lsq=LSQ();lsq.SetRefinedObj(p,0,True,True);lsq.PrepareRefParList(True);ref=lsq.GetCompiledRefinedObj();ref.FixAllPar()
if new_stol is not None:
 lsq.SetParIsFixed(refpartype_scattdata_background,False)
 for i in range(2):
  try:lsq.SafeRefine(nbCycle=5,useLevenbergMarquardt=True,silent=True)
  except:break
  p.FitScaleFactorForRw()
 print('EXTENDED_BACKGROUND',p.GetRw(),flush=True)
lsq.SetParIsFixed(refpartype_scatt_transl,False);lsq.SetParIsFixed(refpartype_scatt_orient,False)
# Begin with positions and orientations only, then allow restrained intramolecular relaxation.
for stage in range(4):
 if stage==1:
  lsq.SetParIsFixed(refpartype_scatt_conform,False)
 if stage==2 and '--fixB' not in sys.argv:
  lsq.SetParIsFixed(refpartype_scattpow_temperature,False)
  # H displacement parameters have limited information; keep at chemically reasonable bounds.
  for i in range(len(c.GetScatteringPowerRegistry())):
   sp=c.GetScatteringPowerRegistry().GetObj(i);sp.SetLimitsAbsolute('Biso',.3,10.)
 if stage==3:
  for n in ['a','b','c','alpha','beta','gamma','Zero','U','V','W','Eta0','Eta1']:
   try:lsq.SetParIsFixed(n,False)
   except:pass
 for j in range(3):
  try:lsq.SafeRefine(nbCycle=10,useLevenbergMarquardt=True,silent=True)
  except Exception as e:print('REFINE_ERROR',e,flush=True);break
  recenter_molecules(c);p.FitScaleFactorForRw();print('CYCLE',stage,j,'Rw',p.GetRw(),'chi2',p.GetChi2(),'geom',sum(m.GetLogLikelihood() for m in mols),'LSQ',lsq.ChiSquare(),flush=True)
 if packing_restraint is not None:print('PACKING_STAGE',stage,lsq_packing.cost(packing_restraint),flush=True)
 export_cif(c,W+'/refine_'+run+'_stage'+str(stage)+'.cif')
 xml_cryst_file_save_global(W+'/refine_'+run+'_stage'+str(stage)+'.xml')
# Final pattern and parameters
export_cif(c,W+'/refined_'+run+'.cif');xml_cryst_file_save_global(W+'/refined_'+run+'.xml')
json.dump({'Rw':p.GetRw(),'chi2':p.GetChi2()},open(W+'/refined_'+run+'.json','w'),indent=1)
import matplotlib.pyplot as plt
x=np.rad2deg(p.GetPowderPatternX());y=p.GetPowderPatternObs();yc=p.GetPowderPatternCalc();fig,ax=plt.subplots(figsize=(14,6));ax.plot(x,y,'k',lw=.6,label='Observed');ax.plot(x,yc,'r',lw=.6,label='Rietveld');ax.plot(x,y-yc-y.max()*.13,'b',lw=.4,label='Difference');ax.legend();ax.set_title(sid+' Rwp %.4f'%p.GetRw());fig.tight_layout();fig.savefig(W+'/refined_'+run+'.png',dpi=130)
print('FINISHED',sid,p.GetRw(),flush=True)

if packing_restraint is not None:lsq_packing.detach(p,packing_restraint)
