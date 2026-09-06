"""Diagnostic anisotropic Lorentzian broadening, with fixed heavy coordinates.
Only the native ObjCryst profile parameters are fitted. Optional --lebail
alternates with Le Bail intensities and is not a structural solution.
"""
import sys,os,ctypes,json,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst._pyobjcryst import LSQ
from pymatgen.core import Lattice
from obj_model import add_component,export_cif
sid,src,tag=sys.argv[1:4];W='/app/work/'+sid;O=xml_cryst_file_load_all_object(src);p=next(o for o in O if o.GetClassName()=='PowderPattern');c=next(o for o in O if o.GetClassName()=='Crystal');d=p.GetPowderPatternComponent(0);p.GetOption(0).SetChoice(1)
if c.GetNbScatterer()==0:add_component(c,'C','diagnostic_C')
lebail='--lebail' in sys.argv;d.SetExtractionMode(lebail,False);p.Prepare()
if lebail:d.ExtractLeBail(20)
p.FitScaleFactorForRw();print('BEFORE',p.GetRw(),flush=True)
lib=ctypes.CDLL('/app/work/libaniso_bridge.so');lib.bridge_aniso.argtypes=[ctypes.c_void_p];assert lib.bridge_aniso(d.int_ptr())==0
r=d.GetProfile();cp=[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']];L=Lattice.from_parameters(*cp);G=r.GetPar('Y').GetValue()*float(p.GetWavelength())**2/4*L.reciprocal_lattice_crystallographic.metric_tensor;r.GetPar('Y').SetValue(0.)
for nm,ij in zip(['G_HH','G_KK','G_LL','G_HK','G_HL','G_KL'],[(0,0),(1,1),(2,2),(0,1),(0,2),(1,2)]):r.GetPar(nm).SetValue(float(G[ij]))
# In this diagnostic only the diagonal tensor is fitted. Its nonnegative
# entries guarantee nonnegative Lorentzian strain broadening in orthogonal cells.
assert np.max(np.abs(np.array(cp[3:])-90))<1.e-4,'This diagnostic is orthorhombic only'
for nm in ['G_HH','G_KK','G_LL']:r.GetPar(nm).SetMin(0.)
p.Prepare();p.FitScaleFactorForRw();print('ANISO_START',p.GetRw(),flush=True)
lsq=LSQ();lsq.SetRefinedObj(p,0,True,True);lsq.PrepareRefParList(True);ref=lsq.GetCompiledRefinedObj();ref.FixAllPar()
for nm in ['U','V','W','X','G_HH','G_KK','G_LL','Eta0','Eta1','Asym0','Asym1']:
 try:lsq.SetParIsFixed(nm,False)
 except Exception as e:print('PAR',nm,e,flush=True)
for i in range(int(os.getenv('ANISO_CYCLES','6'))):
 if lebail:d.ExtractLeBail(15)
 p.FitScaleFactorForRw()
 try:lsq.SafeRefine(nbCycle=5,useLevenbergMarquardt=True,silent=True)
 except Exception as e:print('REFINE_ERROR',e,flush=True)
 p.Prepare();p.FitScaleFactorForRw();print('CYCLE',i,p.GetRw(),flush=True)
xml_cryst_file_save_global(W+'/'+tag+'.xml');pars={r.GetPar(i).GetName():r.GetPar(i).GetHumanValue() for i in range(r.GetNbPar())};json.dump({'Rw':p.GetRw(),'profile':pars},open(W+'/'+tag+'.json','w'),indent=1);print('FINISHED',p.GetRw(),pars,flush=True)
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
x=np.rad2deg(p.GetPowderPatternX());y=np.array(p.GetPowderPatternObs());yc=np.array(p.GetPowderPatternCalc());fig,ax=plt.subplots(figsize=(14,5));ax.plot(x,y,'k',lw=.6);ax.plot(x,yc,'r',lw=.5);ax.plot(x,y-yc-y.max()*.12,'b',lw=.4);ax.set_title(tag+' Rw '+str(p.GetRw()));fig.tight_layout();fig.savefig(W+'/'+tag+'.png')
