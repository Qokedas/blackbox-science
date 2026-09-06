"""Replace the free lactam in a candidate by an acid--lactam docking hypothesis.
The acid's current pose/conformation is retained. The docking is only a search
hypothesis and a virtual Z-matrix connection, not a perceived covalent bond.
"""
import sys,os,json,subprocess,numpy as np,gemmi,xml.etree.ElementTree as ET
from rdkit import Chem
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,export_cif,make_rdkit
sid=sys.argv[1];source=sys.argv[2];tag=sys.argv[3] if len(sys.argv)>3 else 'synseed';W='/app/work/'+sid;G=W+'/search_'+tag;os.makedirs(G,exist_ok=True)
mds=json.load(open(W+'/search_'+source+'/model.json'));src=W+'/refined_'+source+'.xml' if os.path.exists(W+'/refined_'+source+'.xml') else W+'/search_'+source+'/best.xml'
subprocess.run([sys.executable,'/app/work/extract_molecule_coords.py',src,G+'/source_coords.json'],check=True)
source_coords=json.load(open(G+'/source_coords.json'))
tree=ET.parse(src)
for cr in tree.getroot().findall('Crystal'):
 for el in list(cr):
  if el.tag in ['Molecule','Atom','ZScatterer']:cr.remove(el)
tree.write(G+'/empty.xml')
objs=xml_cryst_file_load_all_object(G+'/empty.xml');c=next(o for o in objs if o.GetClassName()=='Crystal');p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=p.GetPowderPatternComponent(0)
r=Chem.MolFromSmiles(mds[0]['smiles']);q,y,_=make_rdkit(mds[1]['smiles'],seed=722,conf_rank=int(os.getenv('CONF_RANK','0')));N=r.GetNumAtoms();x=np.array(source_coords[0]['cartesian'])[:N];ideal=np.array(mds[0].get('restraint_coords',mds[0]['rdkit_coords']))
assert all(.8 < np.linalg.norm(x[b.GetBeginAtomIdx()]-x[b.GetEndAtomIdx()]) < 2.3 for b in r.GetBonds()), 'Broken source geometry'
ac,oa,od=r.GetSubstructMatch(Chem.MolFromSmarts('[CX3](=[OX1])[OX2H1]'));bc,ob,nb=q.GetSubstructMatch(Chem.MolFromSmarts('[CX3](=[OX1])[NX3H1]'))
def dock(x,y):
 ma=(x[oa]+x[od])/2;mb=(y[ob]+y[nb])/2;ay=x[od]-x[oa];ay/=np.linalg.norm(ay);ax=ma-x[ac];ax-=ax@ay*ay;ax/=np.linalg.norm(ax);az=np.cross(ax,ay);by=y[ob]-y[nb];by/=np.linalg.norm(by);bx=y[bc]-mb;bx-=bx@by*by;bx/=np.linalg.norm(bx);bz=np.cross(bx,by)
 return (y-mb)@np.array([bx,by,bz]).T@np.array([ax,ay,az])+ma+float(os.getenv('SYNTHON_GAP','2.78'))*ax
xyz=np.vstack([x,dock(x,y)]);restraint=np.vstack([ideal,dock(ideal,y)]);sm=mds[0]['smiles']+'.'+mds[1]['smiles'];m,md=add_component(c,sm,'synthon',coords_override=restraint);ct=xyz.mean(0)
for i,v in enumerate(xyz-ct):a=m.GetAtom(i);a.X,a.Y,a.Z=v
m.Q0,m.Q1,m.Q2,m.Q3=1.,0.,0.,0.;m.X,m.Y,m.Z=c.OrthonormalToFractionalCoords(*ct)
md['virtual_bonds']=[[int(od),int(N+ob)]];md['restraint_coords']=restraint.tolist();json.dump([md],open(G+'/model.json','w'),indent=1)
d.SetExtractionMode(False);p.Prepare();p.FitScaleFactorForRw();print('GUIDED_SYNTHON',sid,'Rw',p.GetRw(),'O...O',np.linalg.norm(xyz[od]-xyz[N+ob]),'N...O',np.linalg.norm(xyz[oa]-xyz[N+nb]),flush=True)
export_cif(c,G+'/best.cif');xml_cryst_file_save_global(G+'/best.xml')
