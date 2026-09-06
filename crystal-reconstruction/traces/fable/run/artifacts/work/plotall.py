import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, json, os
ids=json.load(open('/app/data/instances.json'))['ids']
fig,axes=plt.subplots(10,3,figsize=(18,30))
for ax,i in zip(axes.flat,ids):
    d=np.loadtxt(f'/app/data/instances/{i}/pattern.xye')
    ins=json.load(open(f'/app/data/instances/{i}/instrument.json'))
    wl=ins['radiation']['wavelength_A']
    tt=d[:,0]; y=d[:,1]
    # convert to Cu-equivalent 2theta for display via d-spacing -> Q
    q=4*np.pi*np.sin(np.radians(tt/2))/wl
    m=q<2.2
    ax.plot(q[m],y[m],lw=0.5)
    ax.set_title(f'{i} wl={wl} n={len(tt)}',fontsize=9)
plt.tight_layout(); plt.savefig('all_patterns.png',dpi=60)
