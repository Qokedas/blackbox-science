import os,sys,time,json,itertools,numpy as np,torch,gemmi
from scipy.spatial.transform import Rotation
from pyobjcryst.io import xml_cryst_file_load_all_object
from obj_bridge import exact_pawley
from obj_model import make_rdkit
from pymatgen.core import Lattice
from rdkit import Chem
sid='X7e382cb';W='/app/work/'+sid;run=sys.argv[1] if len(sys.argv)>1 else 'twocentre1';out=W+'/'+run;os.makedirs(out,exist_ok=True)
torch.set_num_threads(1);torch.set_num_interop_threads(1)
O=xml_cryst_file_load_all_object(W+'/base.xml');p=next(o for o in O if o.GetClassName()=='PowderPattern');c=next(o for o in O if o.GetClassName()=='Crystal');d=p.GetPowderPatternComponent(0)

from obj_model import add_component
if c.GetNbScatterer()==0:dummy,_=add_component(c,'C','dummy_pawley')
d.SetExtractionMode(True,False);p.Prepare();d.ExtractLeBail(20);p.Prepare();p.FitScaleFactorForRw()
print('LEBAIL_RW',p.GetRw(),flush=True)
pw=exact_pawley(p,d,stolmax=float(os.environ.get('STOL','.25')),rcond=.001);sel=pw['sel'];hkl=np.array([d.GetH(),d.GetK(),d.GetL()]).T[sel];stol=np.asarray(d.GetSinThetaOverLambda())[sel]
cp=[c.GetPar(n).GetHumanValue() for n in ['a','b','c','alpha','beta','gamma']];lat=Lattice.from_parameters(*cp)
r,xyz,en=make_rdkit('O=C([O-])c1ccccc1',seed=143,hydrogen=False)
axis=xyz[6]-(xyz[5]+xyz[7])/2;axis/=np.linalg.norm(axis);center=xyz[6]+axis*.745;xyz=xyz-center
axis=xyz[1]-xyz[3];axis/=np.linalg.norm(axis);point=xyz[3].copy();delta=xyz[[0,2]]-point
els=[a.GetSymbol() for a in r.GetAtoms()]*2+['N','N'];counts=[a.GetTotalNumHs() for a in r.GetAtoms()];counts[6]=0;counts=counts*2+[4,4];rad=[.98 if el=='O' else 1.01 if el=='N' else 1.09 for el in els]
sf=np.array([[gemmi.Element(el).it92.calculate_sf(float(s*s))+counts[i]*gemmi.Element('H').it92.calculate_sf(float(s*s))*np.sinc(4*s*rad[i]) for i,el in enumerate(els)] for s in stol])*2*np.exp(-3*stol[:,None]**2)
T=lambda a:torch.tensor(a,dtype=torch.float32)
li=T(np.linalg.inv(lat.matrix));lm=T(lat.matrix);sf=T(sf);hk=T(hkl);xy0=T(xyz);dv=T(delta);ax=T(axis);pt=T(point);nm=T(pw['normal']*1000/pw['var']);obs=T(pw['obs']);no=nm@obs;oo=obs@no
N=int(os.environ.get('PARTICLES','256'));IT=int(os.environ.get('ITERATIONS','500'));BATCH=int(os.environ.get('BATCHES','40'));MAX=float(os.environ.get('SEARCH_TIME','1200'));centres=np.array([[0,0,.5],[0,.5,0],[.5,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0],[.5,.5,.5]])
if 'CENTRE' in os.environ:centres=np.array([[float(x) for x in os.environ['CENTRE'].split(',')]])
ids=np.arange(N)%len(centres);cnt=T(centres[ids]);best=1.e20;t0=time.time();bestpars=None;bestctr=None

def coords(q,phi,pos):
    q=q/torch.linalg.norm(q,dim=-1,keepdim=True);x,y,z,w=q.unbind(-1)
    rr=torch.stack([1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w,2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w,2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y],-1).reshape(-1,2,3,3)
    ca=torch.cos(phi)[...,None,None];sa=torch.sin(phi)[...,None,None]
    mov=pt+dv*ca+torch.linalg.cross(ax.expand_as(dv),dv)*sa+ax*(dv@ax)[...,None]*(1-ca)
    xy=xy0.repeat(len(q),2,1,1);xy[:,:,0]=mov[:,:,0];xy[:,:,2]=mov[:,:,1]
    fr=(xy@rr.transpose(-1,-2))@li;fr[:,1]=fr[:,1]+cnt[:len(q),None,:]
    return torch.cat([fr.reshape(-1,18,3),pos],1)

# Covalent connectivity of each inversion-centred biphenyl excludes the
# central bond and its 1-3/1-4 neighbours, without suppressing true contacts.
rad0=[1.28 if e=='O' else 1.35 if e=='N' else 1.48 for e in els]
dm=Chem.GetDistanceMatrix(r);ii=[];jj=[];signs=[];limits=[];weights=[]
for sign in [1.,-1.]:
 for i in range(20):
  for j in range(20):
   same_half=i<18 and j<18 and i//9==j//9
   if sign==1 and (i>=j or (same_half and dm[i%9,j%9]<=3)):continue
   if sign==-1 and same_half and dm[i%9,6]+1+dm[6,j%9]<=3:continue
   ii.append(i);jj.append(j);signs.append(sign);limits.append(rad0[i]+rad0[j]-(.10 if els[i] in ['N','O'] and els[j] in ['N','O'] else 0.));weights.append(1. if sign==1 else .5)
ii=torch.tensor(ii);jj=torch.tensor(jj);sgn=T(signs);limits=T(limits);weights=T(weights)
shifts=T(np.array(list(itertools.product([-1,0,1],repeat=3)))@lat.matrix);shifts2=(shifts*shifts).sum(-1);coef=float(os.getenv('BUMP_COEFF','150'))
def pack(fr):
 dd=fr[:,ii]-fr[:,jj]*sgn[None,:,None];dd=dd-torch.round(dd).detach();cart=dd@lm
 with torch.no_grad():correct=shifts[(2*(cart.detach()@shifts.T)+shifts2).argmin(-1)]
 dist=torch.sqrt(((cart+correct)**2).sum(-1)+1e-8)
 return coef*((torch.clamp(limits-dist,min=0)**2)*weights).sum(-1)

def calc(q,phi,pos):
    fr=coords(q,phi,pos);f=((torch.cos(2*np.pi*(fr@hk.T)))*sf.T).sum(1)**2
    nf=f@nm;of=f@no;ff=(f*nf).sum(1);cost=oo-torch.clamp(of,min=0)**2/ff.clamp(min=1e-20)
    penalty=pack(fr)
    return cost,penalty,fr

def save(q,ph,po,ctr,cost,batch):
    global cnt
    savecnt=cnt;cnt=T(np.array([ctr]));fr=coords(T(q[None]),T(ph[None]),T(po[None]))[0].detach().numpy();cnt=savecnt
    text='data_solution\n'
    for k,v in zip(['length_a','length_b','length_c','angle_alpha','angle_beta','angle_gamma'],cp):text+=f'_cell_{k} {v:.9f}\n'
    text+="_space_group_name_H-M_alt 'P -1'\n_space_group_IT_number 2\nloop_\n_space_group_symop_id\n_space_group_symop_operation_xyz\n1 'x,y,z'\n2 '-x,-y,-z'\nloop_\n_atom_site_label\n_atom_site_type_symbol\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n"
    for i,(e,v) in enumerate(zip(els,fr)):text+=f'{e}{i+1} {e} {v[0]%1:.9f} {v[1]%1:.9f} {v[2]%1:.9f} 1\n'
    open(out+'/best.cif','w').write(text);np.savez_compressed(out+'/best.npz',q=q,phi=ph,pos=po,centre=ctr,frac=fr);json.dump({'cost':float(cost),'batch':batch,'elapsed':time.time()-t0,'centre':list(ctr)},open(out+'/best.json','w'),indent=1)

print('TWO_CENTRES',cp,'Nref',len(hkl),'Nparticle',N,flush=True)
for batch in range(BATCH):
    q=T(np.random.normal(size=(N,2,4)));phi=T(np.random.uniform(-np.pi,np.pi,size=(N,2)));pos=T(np.random.rand(N,2,3))
    if bestpars is not None and batch%5!=0:
        n=N//2;mask=np.all(centres[ids]==bestctr,axis=1);sel=np.where(mask)[0]
        for ar,br in zip([q,phi,pos],bestpars):ar[sel]=T(br).unsqueeze(0)+torch.randn_like(ar[sel])*.16
    for ar in [q,phi,pos]:ar.requires_grad_(True)
    opt=torch.optim.Adam([q,phi,pos],lr=.035)
    for it in range(IT):
        opt.zero_grad();co,pe,fr=calc(q,phi,pos);loss=(co+pe).sum();loss.backward();torch.nn.utils.clip_grad_norm_([q,phi,pos],max_norm=100000);opt.step()
        if it==IT*3//4:
            for g in opt.param_groups:g['lr']=.008
    with torch.no_grad():
        co,pe,fr=calc(q,phi,pos);score=co+pe;k=int(score.argmin());val=float(score[k]);print('BATCH',batch,'best',val,'diffraction',float(co[k]),'p25',float(torch.quantile(score,.25)),'seconds',time.time()-t0,'centre',centres[ids[k]],flush=True)
        if val<best:
            best=val;bestpars=[ar[k].detach().numpy().copy() for ar in [q,phi,pos]];bestctr=centres[ids[k]].copy();save(*bestpars,bestctr,best,batch)
    if time.time()-t0>MAX or best<3:break
