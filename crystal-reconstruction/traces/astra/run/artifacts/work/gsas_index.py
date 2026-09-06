import os,sys,json,time,copy,numpy as np
sys.path.insert(0,'/opt/g2/GSAS-II/GSASII')
from GSASII import GSASIIindex as gi
from GSASII import GSASIIlattice as gl
sid=sys.argv[1];W='/app/work/'+sid;P=json.load(open(W+'/peaks_raw.json'));wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A']
selpath=os.environ.get('SELECT_FILE',W+'/peak_select_raw.json')
if os.path.exists(selpath):s=json.load(open(selpath));P=[P[i-1] for i in s['indices']]
P=P[int(os.environ.get('PEAK_SKIP',0)):][:int(os.environ.get('NPEAK',20))];zero=float(os.environ.get('ZERO',0));peaks=[[p['two_theta']-zero,p['height'],True,False,0,0,0,wl/(2*np.sin(np.deg2rad((p['two_theta']-zero)/2))),0] for p in P];brav=[False]*18
for i in sys.argv[2].split(','):brav[int(i)]=True
control=[False,zero,int(os.environ.get('NCMAX',20)),float(os.environ.get('VMIN',500))]
print('START',sid,'PEAKS',[p[0] for p in peaks],flush=True)
r=gi.DoIndexPeaks(peaks,control,brav,None,ifX20=True,timeout=float(os.environ.get('INDEX_TIME',120)),M20_min=2,X20_max=5,return_Nc=True)
if r[0]:
 cands=[]
 for c in r[2]:
  typ=['CUBIC','CUBIC','CUBIC','RHOMBOEDRAL','HEXAGONAL','TETRAGONAL','TETRAGONAL']+['ORTHOROMBIC']*6+['MONOCLINIC']*4+['TRICLINIC'];ct=['F','I','P','P','P','I','P','F','I','A','B','C','P','I','A','C','P','P'];cands.append(dict(cell=c[3:9],volume=c[9],score=c[0],system=typ[c[2]],centering=ct[c[2]],mode=19,unindexed=c[1],nc=c[-1],zero=zero))
 cands.sort(key=lambda c:-c['score']);json.dump(cands,open(W+'/index_gsas_'+os.environ.get('INDEX_TAG',sys.argv[2])+'.json','w'),indent=1)
 print('RESULTS',cands[:10],flush=True)
else:print('NOT_FOUND',flush=True)
