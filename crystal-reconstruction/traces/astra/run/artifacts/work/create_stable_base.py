import os,sys,json,numpy as np,gemmi
import matplotlib
matplotlib.use('Agg')
from pyobjcryst.crystal import Crystal
from pyobjcryst.powderpattern import PowderPattern,ReflectionProfileType
from pyobjcryst.io import xml_cryst_file_save_global
sid=sys.argv[1];tag=sys.argv[2];sg=sys.argv[3];W='/app/work/'+sid
j=json.load(open(W+'/fit_'+tag+'.json'));cp=j['cell'];ins=json.load(open('/app/data/instances/'+sid+'/instrument.json'));wl=ins['radiation']['wavelength_A'];rad=ins['radiation']
c=Crystal(*cp[:3],*np.deg2rad(cp[3:]),sg);c.SetName(sid)
from obj_model import add_component
dummy,_=add_component(c,'C','stable_dummy')
data=np.loadtxt('/app/data/instances/'+sid+'/pattern.xye');peaks=json.load(open(W+'/peaks.json'));mh=max(p['height'] for p in peaks);valid=[p for p in peaks if p['height']>.015*mh];xmin=max(data[0,0],min(p['two_theta'] for p in valid)-.5*wl/1.54)
if os.path.exists(W+'/peak_select.json'):xmin=max(xmin,json.load(open(W+'/peak_select.json')).get('min_two_theta',xmin))
stol=float(os.environ.get('MAX_STOL','.25'));data=data[(data[:,0]>=xmin)&(data[:,0]<np.rad2deg(2*np.arcsin(stol*wl)))]
if len(data)>12000:
 n=len(data)//2*2;data=np.column_stack([data[:n,0].reshape(-1,2).mean(1),data[:n,1].reshape(-1,2).mean(1),np.sqrt((data[:n,2]**2).reshape(-1,2).sum(1))/2])
# A constant uncertainty rescaling preserves all diffraction relative weights and prevents disproportionate molecular restraint weighting.
scale=max(1.,np.median(np.sqrt(np.clip(data[:,1],1,None))/data[:,2]));data[:,2]*=scale
np.savetxt(W+'/base_profile.xye',data)
p=PowderPattern();p.SetName(sid);p.ImportPowderPattern2ThetaObsSigma(W+'/base_profile.xye');p.SetWavelength(wl);p.SetMaxSinThetaOvLambda(stol)
if len(rad.get('wavelengths_A') or [])>1:p.SetWavelength('Mo' if wl<1 else 'Cu')
d=p.AddPowderPatternDiffraction(c);d.SetName(sid+'_diffraction')
wid=np.median([v['fwhm'] for v in sorted(valid,key=lambda z:-z['height'])[:25]])
d.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT,np.deg2rad(wid)**2,0,0,.5,0)
b=p.AddPowderPatternBackground();b.SetName(sid+'_background');nbkg=max(20,int((data[-1,0]-data[0,0])/(1.2*wl/1.54)));bx=np.linspace(np.deg2rad(data[0,0]),np.deg2rad(data[-1,0]),nbkg);raw=np.load(W+'/processed.npz');by=np.interp(np.rad2deg(bx),raw['x'],raw['background']);b.SetInterpPoints(bx,by)
p.Prepare();p.quick_fit_profile(pdiff=d,auto_background=False,init_profile=False,plot=False,asym=True,verbose=False);p.FitScaleFactorForRw()
print('FRESH_BASE',sid,sg,p.GetRw(),p.GetChi2(),flush=True)
# Save the actual optimum reached. Excessive multiplicative Le Bail cycles can destabilize heavily overlapped lines.
scale2=max(1.,np.sqrt(p.GetChi2()/len(data)));data[:,2]*=scale2;np.savetxt(W+'/base_profile.xye',data);p.ImportPowderPattern2ThetaObsSigma(W+'/base_profile.xye');p.Prepare();p.FitScaleFactorForRw()
print('SCALED',scale*scale2,'Rw',p.GetRw(),'Chi2',p.GetChi2(),flush=True)
cell={n:float(c.GetPar(n).GetHumanValue()) for n in ['a','b','c','alpha','beta','gamma']};out={'cell':cell,'space_group':sg,'space_group_number':gemmi.find_spacegroup_by_name(sg).number}
json.dump(out,open(W+'/lattice.json','w'),indent=1)
if '--submit' in sys.argv:json.dump(out,open('/app/results/submission/'+sid+'.json','w'),indent=1)
xml_cryst_file_save_global(W+'/base.xml')
# Keep a model-free base for direct-space searches, but retain a finite Pawley scale.
import xml.etree.ElementTree as ET
tree=ET.parse(W+'/base.xml');root=tree.getroot();cc=next(q for q in root if q.tag=='Crystal')
for at in list(cc):
 if at.tag=='Atom':cc.remove(at)
tree.write(W+'/base.xml',encoding='unicode')
np.savez_compressed(W+'/lebail.npz',h=d.GetH(),k=d.GetK(),l=d.GetL(),stol=d.GetSinThetaOverLambda(),f2=d.GetFhklObsSq(),x=p.GetPowderPatternX(),obs=p.GetPowderPatternObs(),calc=p.GetPowderPatternCalc())
p.plot(diff=True,hkl=False);p.figure.savefig(W+'/base.png',dpi=140)
