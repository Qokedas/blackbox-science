import sys,json
from pyobjcryst.io import xml_cryst_file_load_all_object
objs=xml_cryst_file_load_all_object(sys.argv[1]);c=next(o for o in objs if o.GetClassName()=='Crystal');rows=[]
for i in range(c.GetNbScatterer()):
 m=c.GetScatterer(i);sc=m.GetScatteringComponentList();fr=[[a.X,a.Y,a.Z] for a in sc];xyz=[list(c.FractionalToOrthonormalCoords(*v)) for v in fr];els=[a.mpScattPow.GetSymbol() for a in sc];rows.append(dict(name=m.GetName(),fractional=fr,cartesian=xyz,elements=els))
json.dump(rows,open(sys.argv[2],'w'))
