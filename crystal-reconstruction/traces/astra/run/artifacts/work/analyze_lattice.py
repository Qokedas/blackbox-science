import sys,os,json,itertools,numpy as np
from pymatgen.core import Lattice
from scipy.optimize import least_squares
sid=sys.argv[1];tag=sys.argv[2] if len(sys.argv)>2 else '0';W='/app/work/'+sid
f=W+'/fit_'+tag+'.json';j=json.load(open(f if os.path.exists(f) else W+'/candidates.json'));j=j[int(tag)] if isinstance(j,list) else j
cp=np.array(j['cell']);L=Lattice.from_parameters(*cp);wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A'];ps=json.load(open(W+'/peaks.json'));mnh=0;sel={}
if os.path.exists(W+'/peak_select.json'):sel=json.load(open(W+'/peak_select.json'))
if 'indices' in sel:ps=[ps[i-1] for i in sel['indices']]
else:ps=[p for p in ps if p['two_theta']>=sel.get('min_two_theta',0) and all(abs(p['two_theta']-v)>.01 for v in sel.get('exclude',[]))]
maxh=max(p['height'] for p in ps);ps=[p for p in ps if p['height']>maxh*.004 and p['two_theta']<np.rad2deg(2*np.arcsin(wl*.28))];ps=ps[:100]
mx=np.ceil(np.array(L.abc)*.57).astype(int)+1
hkl=np.array([v for v in itertools.product(*[range(-n,n+1) for n in mx]) if next((z for z in v if z),0)>0]);q=np.sqrt(np.sum((hkl@L.reciprocal_lattice_crystallographic.matrix)**2,axis=1));good=q*wl/2<1;hkl=hkl[good];q=q[good];tth=np.rad2deg(2*np.arcsin(q*wl/2));srt=np.argsort(tth);tth=tth[srt];hkl=hkl[srt]
zero=j.get('p_pars',{}).get('Zero',0)
print('CELL',cp,'V',L.volume,'zero',zero)
lookup=[];weights=[]
for ip,p in enumerate(ps):
 t=p['two_theta'];tol=max(.0025*wl/.47,min(p['fwhm']*.3,.017*wl/.47));near=np.where(np.abs(tth+zero-t)<tol)[0];lookup.append(near);weights.append(p['area'])
 if ip<40:
  k=np.argmin(np.abs(tth+zero-t));print(f'{ip+1:3d} {t:9.5f} H{p["height"]:9.1f} W{p["fwhm"]:7.4f} diff{tth[k]+zero-t:8.4f}',hkl[near].tolist() if len(near) else ['?',hkl[k].tolist()])
trs=set()
for den in [2,3,4,5,6]:
 for nums in itertools.product(range(den),repeat=3):
  if max(nums)==0:continue
  v=tuple(round(z/den,6) for z in nums);neg=tuple(round((-z/den)%1,6) for z in nums)
  trs.add(min(v,neg))
weights=np.array(weights);known=np.array([len(v)>0 for v in lookup]);weights*=known
sc=[]
for tr in trs:
 cond=np.abs(hkl@tr-np.round(hkl@tr))<.0001
 passed=np.array([np.any(cond[ind]) if len(ind) else False for ind in lookup]);bad=1-(weights*passed).sum()/weights.sum();count=(known&~passed).sum()
 sc.append((bad,count,tr))
print('UNINDEXED',int((~known).sum()),'of',len(ps),'best translations:')
for bad,count,tr in sorted(sc)[:24]:print(round(bad,5),count,tr)
json.dump({'translations':[{'bad':float(b),'count':int(n),'t':t} for b,n,t in sorted(sc)[:24]],'cell':cp.tolist(),'ps':ps},open(W+'/translations_'+tag+'.json','w'),indent=1)
