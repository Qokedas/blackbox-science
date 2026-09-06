"""Restore measured low-angle observations which were omitted by a strong-peak cutoff."""
import sys,os,json,numpy as np,xml.etree.ElementTree as ET
from pyobjcryst.io import xml_cryst_file_load_all_object,xml_cryst_file_save_global
from obj_model import add_component,recenter_molecules
sid,src,dest=sys.argv[1:4];W='/app/work/'+sid
objs=xml_cryst_file_load_all_object(src);c=next(o for o in objs if o.GetClassName()=='Crystal');p=next(o for o in objs if o.GetClassName()=='PowderPattern');d=next(p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternDiffraction');b=next(p.GetPowderPatternComponent(i) for i in range(p.GetNbPowderPatternComponent()) if p.GetPowderPatternComponent(i).GetClassName()=='PowderPatternBackground')
dummy=c.GetNbScatterer()==0
if dummy:at,_=add_component(c,'C','low_dummy')
p.GetOption(0).SetChoice(1);p.Prepare();p.GetRw();xx=np.rad2deg(np.array(p.GetPowderPatternX()));ww=np.array(p.GetLSQWeight(0));raw=np.loadtxt('/app/data/instances/'+sid+'/pattern.xye');mid=len(ww)//2
scale=(1/np.sqrt(ww[mid]))/np.interp(xx[mid],raw[:,0],raw[:,2]);lo=float(os.getenv('MIN_TTH',str(raw[0,0])))
raw=raw[(raw[:,0]>=lo)&(raw[:,0]<=xx[-1]+1e-5)];raw[:,2]*=scale
nbin=max(1,int(np.ceil(len(raw)/12000)))
if nbin>1:
 n=len(raw)//nbin*nbin;raw=np.column_stack([raw[:n,0].reshape(-1,nbin).mean(1),raw[:n,1].reshape(-1,nbin).mean(1),np.sqrt((raw[:n,2]**2).reshape(-1,nbin).sum(1))/nbin])
bx=np.array(b.GetInterpPointsX());by=np.array(b.GetInterpPointsY());step=np.median(np.diff(bx));newx=np.arange(np.deg2rad(lo),bx[0]-.01*step,step);bg=np.load(W+'/processed.npz');newy=np.interp(np.rad2deg(newx),bg['x'],bg['background']);b.SetInterpPoints(np.r_[newx,bx],np.r_[newy,by]);fn=os.path.splitext(dest)[0]+'.xye';np.savetxt(fn,raw)
p.ImportPowderPattern2ThetaObsSigma(fn);d.SetExtractionMode(True,False);p.Prepare();d.ExtractLeBail(30);p.Prepare();p.FitScaleFactorForRw();recenter_molecules(c);print('RESTORED_LOW_RANGE',sid,lo,xx[0],xx[-1],len(raw),'Rw',p.GetRw(),flush=True);xml_cryst_file_save_global(dest)
if dummy:
 tree=ET.parse(dest);root=tree.getroot();cr=root.find('Crystal')
 for el in list(cr):
  if el.tag=='Atom' and el.attrib.get('Name')=='low_dummy':cr.remove(el)
 tree.write(dest,encoding='utf-8')
