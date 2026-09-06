import sys,numpy as np
from pyobjcryst.io import xml_cryst_file_load_all_object
objs=xml_cryst_file_load_all_object(sys.argv[1]);c=next(o for o in objs if o.GetClassName()=='Crystal');rows=[]
for i in range(c.GetNbScatterer()):
 m=c.GetScatterer(i)
 if m.GetClassName()!='Molecule':continue
 for tag,meth,n in [('bond',m.GetBondList,2),('angle',m.GetBondAngleList,3),('dihedral',m.GetDihedralAngleList,4)]:
  for b in meth():
   try:ll=b.GetLogLikelihood()
   except:continue
   ats=[getattr(b,'GetAtom'+str(k+1))() for k in range(n)];names=[a.GetName() for a in ats];rows.append((ll,tag,names,str(b)))
print('All geom',sum(r[0] for r in rows))
for row in sorted(rows,reverse=True,key=lambda r:r[0])[:30]:print(row[:3])
