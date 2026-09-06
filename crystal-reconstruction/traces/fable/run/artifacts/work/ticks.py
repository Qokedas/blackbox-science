import sys, json, numpy as np, gemmi, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
# usage: ticks.py <id> a b c al be ga "<SG>" ttmax [zero]
iid=sys.argv[1]; cell=[float(v) for v in sys.argv[2:8]]; spg=sys.argv[8]; ttmax=float(sys.argv[9]); zero=float(sys.argv[10]) if len(sys.argv)>10 else 0.0
ins=json.load(open(f'/app/data/instances/{iid}/instrument.json')); wl=ins['radiation']['wavelengths_A'][0]
d=np.loadtxt(f'/app/data/instances/{iid}/pattern.xye'); m=d[:,0]<=ttmax
uc=gemmi.UnitCell(*cell); sg=gemmi.find_spacegroup_by_name(spg); ops=sg.operations()
dmin=wl/(2*np.sin(np.radians(ttmax/2)))
refl=[]
hm=int(cell[0]/dmin)+1; km=int(cell[1]/dmin)+1; lm=int(cell[2]/dmin)+1
seen=set()
for h in range(-hm,hm+1):
  for k in range(-km,km+1):
    for l in range(-lm,lm+1):
      if (h,k,l)==(0,0,0): continue
      dd=uc.calculate_d((h,k,l))
      if dd<dmin: continue
      if ops.is_systematically_absent((h,k,l)): continue
      key=round(dd,4)
      if key in seen: continue
      seen.add(key); refl.append((dd,h,k,l))
refl.sort(reverse=True)
tt=[2*np.degrees(np.arcsin(wl/(2*r[0])))+zero for r in refl]
fig,axs=plt.subplots(2,1,figsize=(18,9))
for ax,(lo,hi) in zip(axs,[(d[m,0].min(),ttmax*0.5),(ttmax*0.5,ttmax)]):
    mm=(d[:,0]>=lo)&(d[:,0]<=hi)
    ax.plot(d[mm,0],d[mm,1],'k',lw=0.7)
    ymin=d[mm,1].min(); ymax=d[mm,1].max()
    for t,r in zip(tt,refl):
        if lo<=t<=hi: ax.plot([t,t],[ymin-0.05*(ymax-ymin),ymin-0.12*(ymax-ymin)],'r',lw=0.8)
    ax.set_xlim(lo,hi)
axs[0].set_title(f'{iid} {spg} cell={cell} nrefl={len(tt)}')
out=f'/app/work/{iid}/ticks_{spg.replace(" ","")}.png'.replace('/','_') if False else f'/app/work/{iid}/ticks.png'
plt.tight_layout(); plt.savefig(out,dpi=65)
print(out, 'nrefl', len(tt))
for t,r in zip(tt[:40],refl[:40]): print(f'{t:8.3f} {r[1]:3d}{r[2]:3d}{r[3]:3d} d={r[0]:.3f}')

# numeric check of observed peaks
import os
pf=f'/app/work/{iid}/peaks_clean.txt'
if not os.path.exists(pf): pf=f'/app/work/{iid}/peaks.txt'
pk=np.loadtxt(pf); pk=pk[pk[:,0]<=ttmax]
tta=np.array(tt)
print('observed peaks vs nearest calc (2th_obs, I, snr, nearest, delta):')
for r in pk:
    j=np.argmin(abs(tta-r[0])); print(f'{r[0]:8.3f} {r[1]:10.1f} {r[4]:6.1f}  {tta[j]:8.3f} {r[0]-tta[j]:+7.3f} {"<-- UNINDEXED" if abs(r[0]-tta[j])>0.02 else ""}')
