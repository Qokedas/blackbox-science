import os,sys,time,json,io
import numpy as np
from pyobjcryst.indexing import *
from rdkit import Chem
sid=sys.argv[1]; system=sys.argv[2] if len(sys.argv)>2 else 'MONOCLINIC'; center=sys.argv[3] if len(sys.argv)>3 else 'P'
mode=int(sys.argv[4]) if len(sys.argv)>4 else 0
W='/app/work/'+sid
ins=json.load(open('/app/data/instances/'+sid+'/instrument.json'));comp=json.load(open('/app/data/instances/'+sid+'/composition.json'));wl=ins['radiation']['wavelength_A']
peakfile=os.environ.get('PEAK_FILE','peaks.json');peaks=json.load(open(W+'/'+peakfile));data=np.load(W+'/processed.npz');x=data['x'];dx=np.median(np.diff(x))
maxh=max(p['height'] for p in peaks); medwid=np.median([p['fwhm'] for p in sorted(peaks,key=lambda p:-p['height'])[:25]])
# Pre-selected peak list used verbatim in this diagnostic.
# For indexing low-lying broad peaks in otherwise fine data are suspect
npeak=int(os.environ.get('NPEAK',22 if mode not in [3,4] else 18))
peaks=peaks[int(os.environ.get('PEAK_SKIP','0')):][:npeak]
if len(peaks)<10: sys.exit(1)
ns=int(os.environ.get('NSPUR',1 if mode in [1,4] else 0))
# deviations incorporate peak-profile asymmetry and blended maxima
base_err=(.012 if wl>1.3 else .003 if wl>.65 else .0015)*(2 if mode>=2 else 1)
base_err=float(os.environ.get('TTHERR',base_err))
ss=''
for p in peaks:
 theta=p['two_theta']-float(os.environ.get('TTHSHIFT',0)); d=wl/(2*np.sin(np.deg2rad(theta/2)));terr=min(float(os.environ.get('MAXERR','100')),max(base_err,p['error']*2,min(p['fwhm']*.15,base_err*2)))
 dsig=d/np.tan(np.deg2rad(theta/2))*np.deg2rad(terr/2)*2
 ss+=f"{d:.9f} {dsig:.9f} {p['height']:.3f}\n"
pl=PeakList();pl.ImportDhklDSigmaIntensity(io.BytesIO(ss.encode()))
cs=getattr(CrystalSystem,system);cen=getattr(CrystalCentering,'LATTICE_'+center)
heavy=sum(Chem.MolFromSmiles(c['smiles']).GetNumHeavyAtoms()*c['count'] for c in comp['components'])
v1=heavy*18
lo=EstimateCellVolume(1/peaks[-1]['d'],1/(peaks[0]['d']*4),len(peaks),cs,cen,1.4)
hi=EstimateCellVolume(1/peaks[-1]['d'],1/(peaks[0]['d']*4),len(peaks),cs,cen,.20 if system!='TRICLINIC' else .35)
lo=max(lo, v1*.65,80);hi=min(hi,v1*(10 if system not in ['MONOCLINIC','TRICLINIC'] else 8 if system=='MONOCLINIC' else 4),15000)
if hi<lo:hi=lo*1.1
if len(sys.argv)>5:lo=float(sys.argv[5]);hi=float(sys.argv[6])
lmax=max(25,min(60,2.8*hi**(1/3)))
if heavy>25 and all(set(c['smiles'])<=set('C[]@H()') for c in comp['components']): lmax=100
lmax=float(os.environ.get('LMAX',lmax))
if system=='TRICLINIC':lmax=min(lmax,float(os.environ.get('LMAX_TRI','40')))
ex=CellExplorer(pl,cs,ns);ex.SetCrystalCentering(cen);ex.SetLengthMinMax(3,lmax);ex.SetAngleMinMax(np.deg2rad(90),np.deg2rad(135 if system=='TRICLINIC' else 140));ex.SetVolumeMinMax(lo,hi);ex.SetD2Error(0)
print(sid,system,center,mode,'peaks',[round(p['two_theta'],5) for p in peaks], 'V',lo,hi, 'Lmax',lmax,flush=True)
start=time.time();ex.DicVol(8,4,float(os.environ.get("INDEX_SCORE",80)),int(os.environ.get("INDEX_DEPTH",7)),True);ex.ReduceSolutions()
sols=[]
for cell,score in ex.GetSolutions():
 c=cell.DirectUnitCell(False,True)
 if all(np.isfinite(c)):
  sols.append(dict(cell=list(c[:6]),volume=c[6],score=score,system=cell.lattice.name,centering=cell.centering.name.replace('LATTICE_',''),mode=mode))
print('DONE',sid,system,center,len(sols),time.time()-start,sols[:5],flush=True)
tag=system+'_'+center+'_'+str(mode)
if len(sys.argv)>5:tag+='_'+sys.argv[5]+'_'+sys.argv[6]
if 'TTHSHIFT' in os.environ:tag+='_z'+os.environ['TTHSHIFT']
if 'INDEX_TAG' in os.environ:tag+='_'+os.environ['INDEX_TAG']
if peakfile!='peaks.json':tag+='_'+peakfile.replace('.json','')
json.dump(sols,open(W+'/index_'+tag+'.json','w'),indent=1)
