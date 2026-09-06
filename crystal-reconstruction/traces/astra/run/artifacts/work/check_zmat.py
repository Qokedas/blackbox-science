import os,sys,json,numpy as np,torch
from rdkit import Chem
from gallop.structure import Structure
from gallop import tensor_prep,zm_to_cart
for D in sys.argv[1:]:
 s=Structure();s.from_json(open(D+'/structure.json').read());md=json.load(open(D+'/model.json'));t=tensor_prep.get_all_required_tensors(s,n_samples=50,requires_grad=False,device=torch.device('cpu'),verbose=False)
 with torch.no_grad():frac=zm_to_cart.get_asymmetric_coords(**t['zm']).numpy();xyz=frac@s.lattice.matrix
 off=0
 for m in md:
  r=Chem.MolFromSmiles(m['smiles']);order=m['order'];idx={v:i for i,v in enumerate(order)};ref=np.array(m['rdkit_coords']);err=[]
  for b in r.GetBonds():
   i=b.GetBeginAtomIdx();j=b.GetEndAtomIdx();dd=np.linalg.norm(xyz[:,off+idx[i]]-xyz[:,off+idx[j]],axis=-1);err.append(max(abs(dd-np.linalg.norm(ref[i]-ref[j]))))
  print(D,m['smiles'],'maxbondError',max(err,default=0),flush=True);off+=len(order)
