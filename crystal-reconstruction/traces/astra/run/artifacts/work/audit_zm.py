import os,sys,json,numpy as np,torch
from gallop.structure import Structure
from gallop_io import load_structure
from gallop.optim.swarm import Swarm
from gallop_moves import coords
from rdkit import Chem
sid=sys.argv[1];run=sys.argv[2] if len(sys.argv)>2 else '11';G='/app/work/'+sid+'/gallop_'+run
torch.set_num_threads(1);torch.set_num_interop_threads(1);s=load_structure(G+'/structure.json');md=json.load(open(G+'/model.json'));e,i=Swarm(s,n_particles=32,n_swarms=1).get_initial_positions();f=coords(s,e,i)@s.lattice.matrix;off=0
for m in md:
 r=Chem.MolFromSmiles(m['smiles']);order=m['order'];inv=np.argsort(order);N=len(order);xyz=np.array(m['rdkit_coords']);x=f[:,off:off+N][:,inv];off+=N
 d=np.linalg.norm(x[:,:,None]-x[:,None,:],axis=-1);d0=np.linalg.norm(xyz[:,None]-xyz[None,:],axis=-1);dm=Chem.GetDistanceMatrix(r);mask=dm<=2;ix=np.unravel_index(np.argmax(np.abs(d-d0)*mask),d.shape)
 print(sid,len(order),'max1/2bond_error',np.max(np.abs(d-d0)*mask),'ix',ix,'i',i.shape,flush=True)
