"""Enumerate D-H...A contacts over all periodic images, not only nearest D-A.
Hydrogen positions are modeled, so this is a geometry diagnostic only.
"""
import sys,numpy as np
from pymatgen.io.cif import CifParser
s=CifParser(sys.argv[1]).parse_structures(primitive=False)[0]
E=np.array([a.specie.symbol for a in s]);H=np.flatnonzero(E=='H');het=np.flatnonzero(np.isin(E,['N','O','Cl','Br','F','S']));don=np.flatnonzero(np.isin(E,['N','O','S']));D=s.distance_matrix;L=s.lattice.matrix
seen=set()
for i in don:
 hs=[h for h in H if D[i,h]<1.28]
 for h in hs:
  _,im=s.lattice.get_distance_and_image(s[i].frac_coords,s[h].frac_coords);vH=(s[h].frac_coords+im-s[i].frac_coords)@L
  for nn in s.get_neighbors(s[i],4.,include_index=True):
   j=nn.index
   if j not in het or nn.nn_distance<2.1:continue
   vA=(nn.frac_coords-s[i].frac_coords)@L;vv=vA-vH;ha=np.linalg.norm(vv);ang=np.rad2deg(np.arccos(np.clip(vv@(-vH)/max(ha*np.linalg.norm(vH),1e-9),-1,1)))
   if ha>2.95 or ang<110:continue
   key=(s[i].label,s[h].label,s[j].label,round(nn.nn_distance,3),round(ang,1))
   if key in seen:continue
   seen.add(key);nearest=np.isclose(nn.nn_distance,D[i,j],atol=.005)
   print(s[i].label,s[h].label,s[j].label,'DA %.4f HA %.4f DHA %.2f'%(nn.nn_distance,ha,ang),'nearest' if nearest else 'NONNEAREST',tuple(nn.image))
