"""Build an acid--lactam R2(8) hydrogen-bonded cluster from supplied components.
This is a direct-space search hypothesis, not crystallographic evidence. Only
hydrogen-bond geometry is preorganised; all original internal rotors remain.
A virtual O...O link is used by the Z-matrix, never as a perceived chemical bond.
"""
import sys,json,numpy as np,os
from rdkit import Chem
from obj_model import make_rdkit
sid=sys.argv[1];tag=sys.argv[2] if len(sys.argv)>2 else 'synthon';rank=int(os.getenv('CONF_RANK','0'));W='/app/work/'+sid
j=json.load(open('/app/data/instances/'+sid+'/composition.json'));assert len(j['components'])==2
sm1,sm2=[co['smiles'] for co in j['components']];r,x,e=make_rdkit(sm1,seed=482,conf_rank=rank);q,y,f=make_rdkit(sm2,seed=722,conf_rank=rank)
pat=Chem.MolFromSmarts('[CX3](=[OX1])[OX2H1]');ac,oa,od=r.GetSubstructMatch(pat)
pat2=Chem.MolFromSmarts('[CX3](=[OX1])[NX3H1]');bc,ob,nb=q.GetSubstructMatch(pat2)
ma=(x[oa]+x[od])/2;mb=(y[ob]+y[nb])/2
ay=x[od]-x[oa];ay/=np.linalg.norm(ay);ax=ma-x[ac];ax-=ax@ay*ay;ax/=np.linalg.norm(ax);az=np.cross(ax,ay)
by=y[ob]-y[nb];by/=np.linalg.norm(by);bx=y[bc]-mb;bx-=bx@by*by;bx/=np.linalg.norm(bx);bz=np.cross(bx,by)
ynew=(y-mb)@np.array([bx,by,bz]).T@np.array([ax,ay,az])+ma+float(os.getenv('SYNTHON_GAP','2.78'))*ax
xyz=np.vstack([x,ynew]);n=len(x);print('SYNTHON',sid,'O...O',np.linalg.norm(x[od]-ynew[ob]),'N...O',np.linalg.norm(x[oa]-ynew[nb]),'energy',e,f)
co={'smiles':sm1+'.'+sm2,'count':1,'charge':0,'coords':xyz.tolist(),'virtual_bonds':[[int(od),int(n+ob)]]};json.dump({'components':[co]},open(W+'/'+tag+'.json','w'),indent=1)
# Save a molecular XYZ for auditing the proposed local geometry.
els=[a.GetSymbol() for a in r.GetAtoms()]+[a.GetSymbol() for a in q.GetAtoms()];open(W+'/'+tag+'.xyz','w').write(str(len(els))+'\nacid-lactam search hypothesis\n'+'\n'.join(e+' '+' '.join(str(v) for v in pos) for e,pos in zip(els,xyz))+'\n')
