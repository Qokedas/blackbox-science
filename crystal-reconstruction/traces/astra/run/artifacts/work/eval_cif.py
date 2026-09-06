import os,sys,json,numpy as np,gemmi
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from pyobjcryst.scatteringpower import ScatteringPowerAtom
from pyobjcryst.atom import Atom
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
sid=sys.argv[1];src=sys.argv[2];W='/app/work/'+sid;tag=sys.argv[3] if len(sys.argv)>3 else 'eval'
base=next((x.split('=',1)[1] for x in sys.argv if x.startswith('--base=')),W+'/base.xml')
O=xml_cryst_file_load_all_object(base);p=next(o for o in O if o.GetClassName()=='PowderPattern');c=next(o for o in O if o.GetClassName()=='Crystal');d=p.GetPowderPatternComponent(0)
block=gemmi.cif.read_file(src).sole_block();ss=gemmi.make_small_structure_from_block(block)
# Coordinates are in the source cell; replace the starting base cell consistently.
for k,v in zip(['a','b','c','alpha','beta','gamma'],[ss.cell.a,ss.cell.b,ss.cell.c,ss.cell.alpha,ss.cell.beta,ss.cell.gamma]):c.GetPar(k).SetHumanValue(v)
sg=ss.spacegroup_hm;c.ChangeSpaceGroup(sg)
for i,at in enumerate(ss.sites):
 el=at.element.name
 try:sp=c.GetScatteringPower(el)
 except:sp=ScatteringPowerAtom(el,el,float(at.u_iso*8*np.pi**2 if at.u_iso>0 else 3));c.AddScatteringPower(sp)
 a=Atom(at.fract.x,at.fract.y,at.fract.z,f'{el}{i+1}',sp,1);c.AddScatterer(a)
c.GetOption(1).SetChoice(0);d.SetExtractionMode(False);p.GetOption(0).SetChoice(1);p.Prepare();p.FitScaleFactorForRw()
print('EVAL',sid,src,'Rw',p.GetRw(),'Chi2',p.GetChi2(),flush=True)
x=np.rad2deg(p.GetPowderPatternX());y=np.asarray(p.GetPowderPatternObs());yc=np.asarray(p.GetPowderPatternCalc());fig,ax=plt.subplots(figsize=(14,5));ax.plot(x,y,'k',lw=.7);ax.plot(x,yc,'r',lw=.7);ax.plot(x,y-yc-.15*y.max(),'b',lw=.5);ax.set_title(sid+' '+tag+' Rwp %.5f'%p.GetRw());fig.tight_layout();fig.savefig(W+'/'+tag+'.png',dpi=130)
json.dump({'Rw':p.GetRw(),'chi2':p.GetChi2()},open(W+'/'+tag+'.json','w'));xml_cryst_file_save_global(W+'/'+tag+'.xml')
