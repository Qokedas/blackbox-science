import numpy as np, gemmi, json, types, os
from rdkit import Chem

def enable_hydrogen_prefix(s, model):
    """Spherical attached-H scattering, without adding search degrees of freedom.
    The radial average is sin(2 pi g r)/(2 pi g r), with g=2 sin(theta)/lambda.
    """
    metadata=json.load(open(model)) if isinstance(model,str) else model
    elements=[];counts=[];radii=[];bs=[]
    for md in metadata:
        r=Chem.MolFromSmiles(md['smiles'])
        for i in md['order']:
            bs.append(float(md['biso_by_atom'][i]) if md.get('biso_by_atom') is not None else np.nan)
            a=r.GetAtomWithIdx(i);elements.append(a.GetSymbol());counts.append(a.GetTotalNumHs(includeNeighbors=True));radii.append({'C':1.09,'N':1.01,'O':.98,'S':1.34}.get(a.GetSymbol(),1.09))
    elements=np.array(elements);counts=np.array(counts);radii=np.array(radii)
    hweight=float(os.environ.get('H_SCATTER_WEIGHT','1.0'))
    def prefix(self,debye_waller_factors=None,just_asymmetric=False,from_cif=False):
        if from_cif:raise ValueError('Attached-H prefix is for molecular search models, not CIFs')
        ss=np.sqrt(np.sum((self.hkl@self.lattice.reciprocal_lattice_crystallographic.matrix)**2,axis=1))/2
        sf=np.array([[gemmi.Element(str(el)).it92.calculate_sf(float(x*x)) for el in elements] for x in ss])
        hf=np.array([gemmi.Element('H').it92.calculate_sf(float(x*x)) for x in ss])
        sf+=hweight*hf[:,None]*counts[None,:]*np.sinc(4*ss[:,None]*radii[None,:])
        dw=debye_waller_factors or {};B=np.array([dw.get(str(el),3.0) for el in elements]);B=np.where(np.isfinite(bs),bs,B);sf*=np.exp(-ss[:,None]**2*B[None,:])
        self.fs=sf;self.prefix=sf
        return sf if just_asymmetric else np.tile(sf,(1,len(self.affine_matrices)))
    s.generate_intensity_calculation_prefix=types.MethodType(prefix,s)
    print('ATTACHED_H_SCATTERING',len(elements),'heavy atoms',int(counts.sum()),'H atoms',flush=True)
