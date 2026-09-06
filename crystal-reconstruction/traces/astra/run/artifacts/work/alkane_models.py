import sys,json,numpy as np,networkx as nx
from rdkit import Chem
from rdkit.Chem import AllChem,rdMolTransforms
for sid in ['Xfca9f3c','Xdcc971e','X2327841']:
 comp=json.load(open('/app/data/instances/'+sid+'/composition.json'));smi=comp['components'][0]['smiles'];r=Chem.AddHs(Chem.MolFromSmiles(smi));AllChem.EmbedMolecule(r,randomSeed=29)
 g=nx.Graph();g.add_edges_from((b.GetBeginAtomIdx(),b.GetEndAtomIdx()) for b in r.GetBonds() if b.GetBeginAtom().GetSymbol()=='C' and b.GetEndAtom().GetSymbol()=='C')
 paths=dict(nx.all_pairs_shortest_path(g));path=max([p for di in paths.values() for p in di.values()],key=len);cf=r.GetConformer()
 for k in range(len(path)-3):rdMolTransforms.SetDihedralDeg(cf,*path[k:k+4],180)
 props=AllChem.MMFFGetMoleculeProperties(r);ff=AllChem.MMFFGetMoleculeForceField(r,props)
 for k in range(len(path)-3):ff.MMFFAddTorsionConstraint(*path[k:k+4],False,178,182,100)
 ff.Initialize();ff.Minimize(maxIts=1000)
 xyz=Chem.RemoveHs(r).GetConformer().GetPositions();comp['components'][0]['coords']=xyz.tolist()
 json.dump(comp,open('/app/work/'+sid+'/alltrans.json','w'));print(sid,len(path),np.linalg.norm(xyz[path[-1]]-xyz[path[0]]))
