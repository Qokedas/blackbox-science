import sys,numpy as np,networkx as nx
from pymatgen.io.cif import CifParser
from rdkit import Chem
s=CifParser(sys.argv[1]).parse_structures(primitive=False)[0];s.remove_species(['H'])
D=s.distance_matrix;rad=np.array([Chem.GetPeriodicTable().GetRcovalent(x.specie.symbol) for x in s]);A=(D>.3)&(D<(rad[:,None]+rad[None,:])*1.2);g=nx.from_numpy_array(A);cs=list(nx.connected_components(g));print('Cell',s.lattice.parameters,'n',len(s),'components',[len(c) for c in cs]);comp={i:k for k,c in enumerate(cs) for i in c}
pairs=sorted((D[i,j],i,j) for i in range(len(s)) for j in range(i+1,len(s)) if comp[i]!=comp[j]);unique=set()
for d,i,j in pairs:
 sig=tuple(sorted([s[i].label,s[j].label]));sig=sig+(round(d,3),)
 if sig in unique:continue
 unique.add(sig);print('%.4f'%d,i,s[i].label,s[i].specie.symbol,comp[i],j,s[j].label,s[j].specie.symbol,comp[j]);
 if len(unique)>=25:break
