import os,json,glob,sys
import numpy as np,spglib
from pymatgen.core import Lattice
ids=sys.argv[1:] or json.load(open('/app/data/instances.json'))['ids']
for sid in ids:
 W='/app/work/'+sid;alls=[]
 for f in glob.glob(W+'/index*.json'):
  ss=json.load(open(f))
  for s in ss:s['source']=os.path.basename(f)
  alls+=ss
 alls.sort(key=lambda s:-s['score']);out=[];nig=[]
 for s in alls:
  if s['score']<max(8,alls[0]['score']*.65):continue
  cp=np.array(s['cell']);L=Lattice.from_parameters(*cp)
  cen=s['centering'];pos={'P':[[0,0,0]],'C':[[0,0,0],[.5,.5,0]],'I':[[0,0,0],[.5,.5,.5]],'A':[[0,0,0],[0,.5,.5]],'B':[[0,0,0],[.5,0,.5]],'F':[[0,0,0],[.5,.5,0],[.5,0,.5],[0,.5,.5]]}[cen]
  try:
   std=spglib.standardize_cell((L.matrix,pos,[1]*len(pos)),to_primitive=False,no_idealize=False,symprec=.025)
   prim=spglib.standardize_cell((L.matrix,pos,[1]*len(pos)),to_primitive=True,no_idealize=False,symprec=.025)
   primL=Lattice(prim[0]).get_niggli_reduced_lattice();n=np.array(primL.parameters)
   if any(np.allclose(n[:3],n2[:3],rtol=.006) and np.allclose(n[3:],n2[3:],atol=.5) for n2 in nig):continue
   nig.append(n)
   ds=spglib.get_symmetry_dataset(std,symprec=.015)
   L=Lattice(std[0]);cp=list(L.parameters);num=ds.number;sg=ds.international;cen=sg[0]
   sys='TRICLINIC' if num<=2 else 'MONOCLINIC' if num<=15 else 'ORTHOROMBIC' if num<=74 else 'TETRAGONAL' if num<=142 else 'HEXAGONAL' if num<=194 else 'CUBIC'
  except Exception as e:print(sid,e);continue
  new=dict(s,cell=cp,volume=L.volume,system=sys,centering=cen,sg=sg)
  out.append(new)
  if len(out)>=8:break
 json.dump(out,open(W+'/candidates.json','w'),indent=1)
 if out:print(sid,len(out),out[0]['score'],[round(x,4) for x in out[0]['cell']],out[0]['sg'])
