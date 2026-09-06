import os,sys,glob,json,numpy as np,gemmi
from scipy.optimize import least_squares
from pymatgen.core import Lattice
from numba import njit
sid='X8a6f5a8';W='/app/work/'+sid
p=json.load(open(W+'/peaks_emg.json'));selected=json.load(open(W+'/peak_select_emg.json'))['indices'];pp=[p[i-1] for i in selected]
tt=np.array([q['two_theta'] for q in pp]);wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A'];q=(2*np.sin(np.deg2rad(tt/2))/wl)**2;fac=wl*wl/(2*np.sin(np.deg2rad(tt)))*180/np.pi
# Fixed conservative error, not overprecise least-squares formal uncertainty.
err=np.maximum(.018,np.array([r.get('emg_error',.02)*2 for r in pp]));out=[]
@njit
def assign(v,T,q,fac):
 qc=T@v[:-1];d=np.zeros(len(q));ind=np.zeros(len(q),np.int64)
 for i in range(len(q)):
  delta=(qc-q[i])*fac[i]+v[-1];j=np.argmin(np.abs(delta));d[i]=delta[j];ind[i]=j
 return d,ind
hkl={};terms={}
for sgname in ['P 1','P 1 2 1','P 1 21 1','C 1 2 1','P 21 21 21']:
 sg=gemmi.find_spacegroup_by_name(sgname);sysm='TRICLINIC' if sg.number==1 else 'ORTHOROMBIC' if sg.number==19 else 'MONOCLINIC'
 hk=np.array([[h,k,l] for h in range(11) for k in (range(-10,11) if sysm=='TRICLINIC' else range(11)) for l in (range(13) if sysm=='ORTHOROMBIC' else range(-12,13)) if (h or k>0 or (k==0 and l>0)) and not sg.operations().is_systematically_absent([h,k,l])],float)
 hkl[sgname]=hk
 tr=np.array([hk[:,0]**2,hk[:,1]**2,hk[:,2]**2,2*hk[:,1]*hk[:,2],2*hk[:,0]*hk[:,2],2*hk[:,0]*hk[:,1]]).T
 terms[sgname]=tr[:,:3] if sysm=='ORTHOROMBIC' else tr[:,[0,1,2,4]] if sysm=='MONOCLINIC' else tr
seen=[];starts=[]
for f in glob.glob(W+'/fit_*.json')+glob.glob(W+'/index_*.json')+glob.glob(W+'/candidates*.json'):
 try:
  rows=json.load(open(f));rows=rows if isinstance(rows,list) else [rows]
  for j,row in enumerate(rows[:30]):
   if not isinstance(row,dict) or 'cell' not in row:continue
   cp=row['cell'];sysm=row.get('system','TRICLINIC')
   if isinstance(cp,dict):cp=[cp[k] for k in ['a','b','c','alpha','beta','gamma']]
   L=Lattice.from_parameters(*cp)
   if L.volume<900 or L.volume>8500:continue
   re=L.get_niggli_reduced_lattice().parameters
   if any(np.allclose(re[:3],rr[:3],rtol=.002) and np.allclose(re[3:],rr[3:],atol=.15) for rr in seen):continue
   seen.append(re);starts.append((cp,sysm,os.path.basename(f)+':'+str(j),row.get('zero',0.)))
 except Exception:continue
print('STARTS',len(starts),flush=True)
for ni,(cp,sysm,source,zero) in enumerate(starts):
 sgs=['P 1'] if sysm=='TRICLINIC' else ['P 21 21 21'] if sysm=='ORTHOROMBIC' else ['P 1 21 1','P 1 2 1']
 if sysm=='MONOCLINIC':sgs+=['C 1 2 1']
 for sgname in sgs:
  mat=Lattice.from_parameters(*cp).reciprocal_lattice_crystallographic.metric_tensor
  v=np.array([mat[0,0],mat[1,1],mat[2,2]]+([] if sysm=='ORTHOROMBIC' else [mat[0,2]] if sysm=='MONOCLINIC' else [mat[1,2],mat[0,2],mat[0,1]])+[float(np.clip(zero+.04,-.18,.18))]);T=terms[sgname]
  for it in range(8):
   d,ind=assign(v,T,q,fac)
   res=least_squares(lambda vv:((T[ind]@vv[:-1]-q)*fac+vv[-1])/err,v,loss='soft_l1',f_scale=1.,max_nfev=80)
   if np.max(abs(res.x-v))<1e-10:break
   v=res.x
  d,ind=assign(v,T,q,fac);g=np.zeros(6);g[:3]=v[:3]
  if sysm=='MONOCLINIC':g[4]=v[3]
  if sysm=='TRICLINIC':g[3:]=v[3:6]
  GM=np.array([[g[0],g[5],g[4]],[g[5],g[1],g[3]],[g[4],g[3],g[2]]])
  if np.linalg.eigvalsh(GM).min()<=0:continue
  lat=Lattice(np.linalg.cholesky(np.linalg.inv(GM)));vol=lat.volume
  if not(900<vol<9000) or abs(v[-1])>.22:continue
  red=lat.get_niggli_reduced_lattice().parameters
  if any(o['sg']==sgname and np.allclose(red[:3],o['reduced'][:3],rtol=.002) and np.allclose(red[3:],o['reduced'][3:],atol=.15) for o in out):continue
  robust=float(np.mean(np.log1p((d/err)**2)));co=robust*(vol/(2 if sgname.startswith('C') else 1))/2800
  out.append(dict(cell=list(lat.parameters),system=sysm,centering=sgname[0],sg=sgname,volume=vol,zero=float(v[-1]),cost=co,robust=robust,rms=float(np.sqrt(np.mean(d*d))),nclose=int(sum(abs(d)<.035)),diff=d.tolist(),hkl=hkl[sgname][ind].astype(int).tolist(),source=source,reduced=list(red),score=1/max(co,1e-10),mode=81))
 if ni%30==0:print('AT',ni,flush=True)
out.sort(key=lambda x:x['cost']);json.dump(out,open(W+'/candidates_emgrefine.json','w'),indent=1)
for o in out[:30]:print('BEST',o['cost'],o['nclose'],o['sg'],np.round(o['cell'],5),o['zero'],o['source'],np.round(o['diff'],4),flush=True)
