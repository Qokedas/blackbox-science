"""Generate a P-1 search seed by least-squares inversion pairing of P1 fragments.
The origin/permutation is determined from all anion heavy atoms. NH4 nitrogen
positions are inversion-paired and will be searched anew, not assumed correct.
"""
import os,sys,json,numpy as np,itertools
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif
from pymatgen.core import Lattice
from rdkit import Chem
sid='X7e382cb';W='/app/work/'+sid;tag='centro100';R=W+'/search_'+tag;os.makedirs(R,exist_ok=True)
O=xml_cryst_file_load_all_object(W+'/refined_ionH85.xml');c=next(o for o in O if o.GetClassName()=='Crystal');p=next(o for o in O if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0);md=json.load(open(W+'/search_ionH85/model.json'));info=json.load(open(W+'/p1_centrosymmetry97.json'));o=np.array(info['origin']);S=2*o;perm=np.array(info['permutation']);mols=[c.GetScatterer(i) for i in range(c.GetNbScatterer())];L=Lattice.from_parameters(*[c.GetPar(k).GetHumanValue() for k in ['a','b','c','alpha','beta','gamma']]);M=np.array([c.FractionalToOrthonormalCoords(*v) for v in np.eye(3)]);F=[];N=[]
for m,mo in zip(mols,md):
 nr=Chem.MolFromSmiles(mo['smiles']).GetNumAtoms();sc=list(m.GetScatteringComponentList())[:nr];fr=np.array([[a.X,a.Y,a.Z] for a in sc])
 if nr==18:F.append(fr);am=mo
 else:N.append(fr[0])
N=np.array(N)
def paired(a,b):
 t=S-b;im=L.get_distance_and_image(a,t)[1];return (a+t+im)/2-o
anion=np.array([paired(a,b) for a,b in zip(F[0],F[1][perm])]);pairs=[[(0,1),(2,3)],[(0,2),(1,3)],[(0,3),(1,2)]]
pp=min(pairs,key=lambda P:sum(L.get_distance_and_image(N[i],S-N[j])[0]**2 for i,j in P));ions=[paired(N[i],N[j])[None] for i,j in pp];print('PAIRING',pp,'origin',o,flush=True)
for m in mols:c.RemoveScatterer(m)
c.ChangeSpaceGroup('P -1');new=[]
for j,fr in enumerate([anion]+ions):
 sm=am['smiles'] if j==0 else '[NH4+]';ideal=np.array(am.get('restraint_coords',am['rdkit_coords'])) if j==0 else None;m,mo=add_component(c,sm,'centro_m'+str(j),coords_override=ideal);xyz=fr@M;ctr=xyz.mean(0)
 if m.GetClassName()=='Molecule':
  for i,v in enumerate(xyz-ctr):a=m.GetAtom(i);a.X,a.Y,a.Z=map(float,v)
  m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.
 m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*ctr);new.append(mo)
 actual=np.array([[a.X,a.Y,a.Z] for a in list(m.GetScatteringComponentList())[:len(fr)]]);print('DEBUG',j,'maxerr',np.max(np.abs(actual-fr)), 'actual',actual[:3],'desired',fr[:3], 'xyzrange',np.ptp(xyz,axis=0),flush=True);assert np.max(np.abs((actual-fr+.5)%1-.5))<1.e-6
c.GetOption(1).SetChoice(0);d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();json.dump(new,open(R+'/model.json','w'),indent=1);xml_cryst_file_save_global(R+'/best.xml');export_cif(c,R+'/best.cif');print('SYMMETRISED_HEAVY_RW',p.GetRw(),flush=True)
