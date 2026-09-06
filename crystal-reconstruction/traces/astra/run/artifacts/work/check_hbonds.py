"""Report short heteroatom contacts and donor-H-acceptor geometry in a CIF.
Distances use exact nearest lattice images; no assignment of formal protonation.
"""
import sys,numpy as np,gemmi,networkx as nx
from pymatgen.io.cif import CifParser
s=CifParser(sys.argv[1]).parse_structures(primitive=False)[0]
E=np.array([a.specie.symbol for a in s]);D=s.distance_matrix
H=np.flatnonzero(E=='H');het=np.flatnonzero(np.isin(E,['N','O','Cl','Br','F','S']))
seen=set()
for i in het:
 if E[i] not in ['N','O','S']:continue
 hs=[h for h in H if D[i,h]<1.27]
 if not hs:continue
 for h in hs:
  _,im=s.lattice.get_distance_and_image(s[i].frac_coords,s[h].frac_coords)
  vH=(s[h].frac_coords+im-s[i].frac_coords)@s.lattice.matrix
  for j in het:
   if i==j or D[i,j]<2.1 or D[i,j]>3.9:continue
   _,im=s.lattice.get_distance_and_image(s[i].frac_coords,s[j].frac_coords)
   vA=(s[j].frac_coords+im-s[i].frac_coords)@s.lattice.matrix
   dhA=vA-vH;ang=np.rad2deg(np.arccos(np.clip(dhA@(-vH)/np.linalg.norm(dhA)/np.linalg.norm(vH),-1,1)))
   if np.linalg.norm(dhA)>3.3:continue
   key=(s[i].label,s[h].label,s[j].label,round(D[i,j],3),round(ang,1))
   if key in seen:continue
   seen.add(key)
   print(s[i].label,s[h].label,s[j].label,'DA %.4f'%D[i,j],'HA %.4f'%np.linalg.norm(dhA),'DHA %.2f'%ang)
