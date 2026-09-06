import os,sys,json,time,numpy as np,gemmi
from numba import njit
from scipy.optimize import least_squares
from pymatgen.core import Lattice
sid=sys.argv[1];W='/app/work/'+sid
ps=json.load(open(W+'/peaks_raw.json'));wl=json.load(open('/app/data/instances/'+sid+'/instrument.json'))['radiation']['wavelength_A']
sel=[4,10,11,12,13,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,38,39,40,41,43,44,46,49,50,51,52,53]
tt=np.array([ps[i-1]['two_theta'] for i in sel]);qobs=(2*np.sin(np.deg2rad(tt/2))/wl)**2;fac=wl**2/(2*np.sin(np.deg2rad(tt)))*180/np.pi
init=np.array([.0005964058906554,.0062107082732483,-.04102578]);kls=np.array([[k,l] for k in range(0,25) for l in range(0,9) if k or l],float);T2=np.array([kls[:,0]**2,kls[:,1]**2]).T
low=tt<17.65
for ii in range(4):
 ix=np.argmin(abs((T2@init[:2])[None,:]-(qobs-init[2]/fac)[:,None]),axis=1)
 init=least_squares(lambda x:(T2[ix[low]]@x[:2]-qobs[low])*fac[low]+x[2],init,loss='soft_l1',f_scale=.015).x
print('PLANE',init,flush=True)
G22,G33,zero=init;qcor=qobs-zero/fac;etol=float(os.getenv('TTHERR','.04'));nspur=int(os.getenv('NSPUR','1'));lo=float(os.getenv('VMIN','1500'));hi=float(os.getenv('VMAX','3400'))
gnames=['P 1 21/a 1','P 1 21/c 1','P 1 21/n 1','P 1 2/a 1','P 1 2/c 1','P 21 21 21','P 2 2 21','P b c a']
if len(sys.argv)>2:gnames=sys.argv[2:]
t0=time.time();outs=[]
for sgname in gnames:
 sg=gemmi.find_spacegroup_by_name(sgname);ops=sg.operations();orth=sg.crystal_system_str()=='orthorhombic'
 hk=np.array([[h,k,l] for h in range(0,5) for k in range(0,25) for l in (range(0,9) if orth else range(-8,9)) if (h or k or l) and not(h==0 and l<0) and not ops.is_systematically_absent([h,k,l])],float)
 terms=np.array([hk[:,0]**2,hk[:,1]**2,hk[:,2]**2,2*hk[:,0]*hk[:,2]]).T
 @njit(cache=False)
 def evaluate(g):
  qc=terms@g;dif=np.zeros(len(tt));ix=np.zeros(len(tt),np.int64)
  for i in range(len(tt)):
   best=1e20
   for j in range(len(qc)):
    dd=abs(qc[j]-qcor[i])
    if dd<best:best=dd;ix[i]=j
   dif[i]=(qc[ix[i]]-qobs[i])*fac[i]+zero
  sq=np.log1p((dif/etol)**2);sq.sort();v=1/np.sqrt(g[1]*(g[0]*g[2]-g[3]*g[3]));co=np.mean(sq[:len(sq)-nspur])*v/2500
  return co,ix,dif
 @njit(cache=False)
 def enumeration(i1,i2):
  rows=np.zeros((150000,5));nr=0
  for k in range(0,14):
   for l in range(-5,6):
    if k==0 and (not orth) and (('21/a' in sgname or '2/a' in sgname) or (('21/c' in sgname or '2/c' in sgname) and l%2) or (('21/n' in sgname) and (l+1)%2)):continue
    r1=qcor[i1]-G22*k*k-G33*l*l
    if orth:
     g=np.array([r1,G22,G33,0.])
     if r1<=0:continue
     vol=1/np.sqrt(r1*G22*G33)
     if lo<vol<hi:
      cost,ix,dd=evaluate(g)
      if cost<1.0:rows[nr,0]=cost;rows[nr,1:]=g;nr+=1
     continue
    for m in range(0,14):
     for n in range(-5,6):
      if n==l:continue
      if m==0 and (('21/a' in sgname or '2/a' in sgname) or (('21/c' in sgname or '2/c' in sgname) and n%2) or (('21/n' in sgname) and (n+1)%2)):continue
      r2=qcor[i2]-G22*m*m-G33*n*n
      cross=(r2-r1)/(2*(n-l));r0=r1-2*l*cross
      det=G22*(r0*G33-cross**2)
      if det<=0:continue
      vol=1/np.sqrt(det)
      if vol<lo or vol>hi:continue
      if abs(cross)/np.sqrt(r0*G33)>.6:continue
      g=np.array([r0,G22,G33,cross]);cost,ix,dd=evaluate(g)
      if cost<1.0:rows[nr,0]=cost;rows[nr,1:]=g;nr+=1
  return rows[:nr]
 candidates=[]
 for p1,p2 in [(31,35),(27,35),(35,38),(31,38)]:
  rows=enumeration(sel.index(p1),sel.index(p2));rows=rows[np.argsort(rows[:,0])][:100]
  for row in rows:
   if any(np.allclose(row[1:],s[1:],rtol=.0001,atol=1e-7) for s in candidates):continue
   candidates.append(row)
 print('ENUM',sgname,len(candidates),time.time()-t0,flush=True)
 for row in sorted(candidates,key=lambda s:s[0])[:40]:
  g=row[1:];co,ix,di=evaluate(g);x=np.r_[g,zero]
  for it in range(4):
   T=terms[ix]
   if orth:
    x[3]=0
    re=least_squares(lambda z:(T[:,:3]@z[:3]-qobs)*fac+z[3],x[[0,1,2,4]],loss='soft_l1',f_scale=.035,max_nfev=100);x=np.r_[re.x[:3],0.,re.x[3]]
   else:
    re=least_squares(lambda z:(T@z[:4]-qobs)*fac+z[4],x,loss='soft_l1',f_scale=.035,max_nfev=100);x=re.x
   qc=terms@x[:4];ix=np.argmin(abs(qc[None,:]-(qobs-x[4]/fac)[:,None]),axis=1)
  g=x[:4];GM=np.array([[g[0],0,g[3]],[0,g[1],0],[g[3],0,g[2]]]);L=Lattice(np.linalg.cholesky(np.linalg.inv(GM)));di=(terms[ix]@g-qobs)*fac+x[4];sq=np.sort(np.log1p((di/etol)**2));cost=np.mean(sq[:-nspur] if nspur else sq)*L.volume/2500
  o=dict(cell=list(L.parameters),volume=L.volume,cost=float(cost),zero=float(x[4]),system='ORTHOROMBIC' if orth else 'MONOCLINIC',centering='P',sg=sgname,score=float(1/max(cost,1e-10)),source='plane_mono',diff=di.tolist(),hkl=hk[ix].astype(int).tolist())
  if not any(s['sg']==sgname and np.allclose(s['cell'][:3],o['cell'][:3],rtol=.001) and abs(s['cell'][4]-o['cell'][4])<.1 for s in outs):outs.append(o)
 outs.sort(key=lambda s:s['cost']);json.dump(outs,open(W+'/candidates_planemono.json','w'),indent=1)
 print('BEST',sgname,[(np.round(s['cell'],4).tolist(),round(s['cost'],5)) for s in outs if s['sg']==sgname][:5],flush=True)
print('DONE',time.time()-t0,flush=True)
