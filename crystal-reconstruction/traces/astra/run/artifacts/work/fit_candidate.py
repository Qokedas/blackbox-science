import os,sys,json,glob,time
import numpy as np,gemmi,spglib
from pymatgen.core import Lattice
import matplotlib
matplotlib.use('Agg')
from pyobjcryst.crystal import Crystal
from pyobjcryst.powderpattern import PowderPattern,ReflectionProfileType,SpaceGroupExplorer
from pyobjcryst.io import xml_cryst_file_save_global
from pyobjcryst.refinableobj import refpartype_scattdata_background
sid=sys.argv[1];tag=sys.argv[2] if len(sys.argv)>2 else 'best';W='/app/work/'+sid
spec=json.load(open(os.environ.get('CANDIDATE_FILE',W+'/candidates.json')))
sol=spec[int(os.environ.get('CANDIDATE_INDEX',tag if tag.isdigit() else '0'))]
cp=sol['cell'];sgstart=sol.get('sg','P m m m' if sol['system']=='ORTHOROMBIC' else 'P 1 2/m 1' if sol['system']=='MONOCLINIC' else 'P -1')
ins=json.load(open('/app/data/instances/'+sid+'/instrument.json'));wl=ins['radiation']['wavelength_A'];comp=json.load(open('/app/data/instances/'+sid+'/composition.json'));chiral=any('@' in m['smiles'] for m in comp['components'])
# cell angles are constrained using the corresponding metric symmetry
c=Crystal(*cp[:3],*np.deg2rad(cp[3:]),sgstart);c.SetName(sid+'_'+tag)
data=np.loadtxt('/app/data/instances/'+sid+'/pattern.xye');peaks=json.load(open(W+'/peaks.json'));mx=max(v['height'] for v in peaks);valid=[v for v in peaks if v['height']>mx*.015];xmin=max(data[0,0],min(v['two_theta'] for v in valid)-.5*wl/1.54)

if os.path.exists(W+'/peak_select.json'):
 manual=json.load(open(W+'/peak_select.json'));xmin=max(xmin,manual.get('min_two_theta',xmin))
stol=float(sys.argv[3]) if len(sys.argv)>3 else .25
sel=(data[:,0]>=xmin)&(data[:,0]<min(data[-1,0]+.001,np.rad2deg(2*np.arcsin(wl*stol))));data=data[sel]
# reduce oversampling at very fine synchrotron steps, preserving counting errors appropriately
step=1
if len(data)>12000: step=2
if step>1:
 n=len(data)//step*step;data=np.column_stack([data[:n,0].reshape(-1,step).mean(1),data[:n,1].reshape(-1,step).mean(1),np.sqrt((data[:n,2]**2).reshape(-1,step).sum(1))/step])
np.savetxt(W+'/fit_'+tag+'.xye',data)
p=PowderPattern();p.SetName(sid+'_'+tag);p.ImportPowderPattern2ThetaObsSigma(W+'/fit_'+tag+'.xye');p.SetWavelength(wl);p.SetMaxSinThetaOvLambda(stol)
rad=ins['radiation']
if len(rad.get('wavelengths_A') or [])>1: p.SetWavelength('Mo' if wl<1 else 'Cu')
d=p.AddPowderPatternDiffraction(c)
wid=np.median([v['fwhm'] for v in sorted(valid,key=lambda z:-z['height'])[:25]])
d.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT,np.deg2rad(wid)**2,0,0,.5,0)
b=p.AddPowderPatternBackground();nbkg=max(20,int((data[-1,0]-data[0,0])/(1.2*wl/1.54)))
bx=np.linspace(np.deg2rad(data[0,0]),np.deg2rad(data[-1,0]),nbkg);orig=np.load(W+'/processed.npz');by=np.interp(np.rad2deg(bx),orig['x'],orig['background']);b.SetInterpPoints(bx,by)
p.Prepare()
p.quick_fit_profile(pdiff=d,auto_background=False,init_profile=False,plot=False,asym=True,verbose=False)
print('STARTFIT',sid,tag,'Rw',p.GetRw(),flush=True)
xml_cryst_file_save_global(W+'/pre_scan_'+tag+'.xml')
# Enumerate meaningful settings with compatible symmetry; absences alone do not prove chirality/centrosymmetry.
system=sol['system'];cent=sol['centering']
if system=='ORTHOROMBIC':
 nums=[16,17,18,19,20,21,22,23,24] if chiral else [16,17,18,19,20,21,22,23,24,29,33,36,37,38,39,40,41,42,43,46,50,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74]
elif system=='MONOCLINIC': nums=[3,4,5] if chiral else list(range(3,16))
else:nums=[1] if chiral else [1,2]
groups=[]
for sg in gemmi.spacegroup_table():
 if sg.number not in nums:continue
 if system=='MONOCLINIC' and sg.monoclinic_unique_axis()!='b':continue
 name=sg.xhm()
 # Avoid alternate origin choices (irrelevant extinctions)
 if ':2' in name:continue
 if name not in groups:groups.append(name)
if os.environ.get('SG_SCAN','1')=='0':groups=[sgstart]
sgex=SpaceGroupExplorer(d);scores=[]
for name in groups:
 try:
  r=sgex.Run(name,False,False,True,False)
  scores.append(dict(sg=name,number=gemmi.find_spacegroup_by_name(name).number,Rw=float(r.Rw),GoF=float(r.GoF),nGoF=float(r.nGoF),mult=len(gemmi.find_spacegroup_by_name(name).operations())))
 except Exception as e:print('ERRORSG',name,str(e),flush=True)
scores.sort(key=lambda x:x['Rw'])
print('GROUPS',json.dumps(scores),flush=True)
d.SetExtractionMode(True,True);d.ExtractLeBail(40)
# save baseline refined parameters and candidate scan without arbitrarily finalising SG
cp=[float(c.GetPar(n).GetHumanValue()) for n in ['a','b','c','alpha','beta','gamma']]
result=dict(sol,cell=cp,sgstart=sgstart,Rw=float(p.GetRw()),groups=scores,stol=stol)
json.dump(result,open(W+'/fit_'+tag+'.json','w'),indent=1)
p.plot(diff=True,hkl=False);p.figure.savefig(W+'/fit_'+tag+'.png',dpi=130)
xml_cryst_file_save_global(W+'/fit_'+tag+'.xml')
# Profile values for custom intensity/model code
try:
 pp={p.GetPar(i).GetName():p.GetPar(i).GetHumanValue() for i in range(p.GetNbPar())}
 dp={d.GetPar(i).GetName():d.GetPar(i).GetHumanValue() for i in range(d.GetNbPar())}
 result['p_pars']=pp;result['d_pars']=dp
 json.dump(result,open(W+'/fit_'+tag+'.json','w'),indent=1)
except:pass
print('DONE',sid,tag,p.GetRw(),cp,flush=True)
