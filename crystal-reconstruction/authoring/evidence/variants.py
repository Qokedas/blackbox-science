#!/usr/bin/env python3
"""Make submission variants from a reference CIF for the fixture battery.
variants: oracle, p1 (P1 expansion of the full cell), jitter<x> (random Cartesian jitter of x A, seed 0),
mirror (inverted coordinates, same cell), randcoords (same cell/sg, random coords), ringflip (rotate one ring? -> n/a),
hedge (two CIFs), nocif (json only), nojson (cif only), wrongsg (cell right, P1 declared), subcell (a/2).
"""
import sys,json,os,random
import numpy as np
from pymatgen.io.cif import CifParser, CifWriter
from pymatgen.core import Structure, Lattice
def load(cif_text):
    return CifParser.from_str(cif_text, occupancy_tolerance=1.0).parse_structures(primitive=False)[0]
def write_p1(struct, path):
    CifWriter(struct).write_file(path)
def make(variant, cif_text, iid, outdir, cell_json):
    os.makedirs(outdir, exist_ok=True)
    cif_p = os.path.join(outdir, iid+'.cif'); js_p = os.path.join(outdir, iid+'.json')
    js = dict(cell_json)
    if variant == 'oracle':
        open(cif_p,'w').write(cif_text)
    elif variant == 'p1':
        s = load(cif_text); write_p1(s, cif_p); js['space_group']='P 1'
    elif variant.startswith('jitter'):
        amp=float(variant[6:]); s=load(cif_text); rng=np.random.default_rng(0)
        for i in range(len(s)):
            v=rng.normal(size=3); v=v/np.linalg.norm(v)*amp
            s.translate_sites([i], v, frac_coords=False, to_unit_cell=True)
        write_p1(s, cif_p); js['space_group']='P 1'
    elif variant == 'mirror':
        s = load(cif_text); s2 = Structure(s.lattice, [x.specie for x in s], [(-x.frac_coords)%1 for x in s]); write_p1(s2, cif_p); js['space_group']='P 1'
    elif variant == 'randcoords':
        s = load(cif_text); rng=np.random.default_rng(1); s2=Structure(s.lattice,[x.specie for x in s], rng.random((len(s),3))); write_p1(s2,cif_p)
    elif variant == 'hedge':
        open(cif_p,'w').write(cif_text); open(os.path.join(outdir, iid+'_alt.cif'),'w').write(cif_text)
    elif variant == 'nocif':
        pass
    elif variant == 'nojson':
        open(cif_p,'w').write(cif_text); js=None
    elif variant == 'wrongsg':
        open(cif_p,'w').write(cif_text); js['space_group']='P 1'
    elif variant == 'subcell':
        open(cif_p,'w').write(cif_text); js['cell']=dict(js['cell']); js['cell']['a']=js['cell']['a']/2
    elif variant == 'stretch2pct':
        js['cell']=dict(js['cell']); js['cell']['a']*=1.02; open(cif_p,'w').write(cif_text)
    elif variant == 'stretch0p5pct':
        js['cell']=dict(js['cell']); js['cell']['a']*=1.005; open(cif_p,'w').write(cif_text)
    elif variant == 'shift_origin':
        s = load(cif_text); s.translate_sites(list(range(len(s))), [0.25,0.13,0.37], frac_coords=True, to_unit_cell=True); write_p1(s, cif_p); js['space_group']='P 1'
    elif variant == 'wrongmol':
        s = load(cif_text); s2=s.copy(); s2.remove_sites([len(s)-1]); write_p1(s2,cif_p)
    else:
        raise SystemExit('unknown variant '+variant)
    if js is not None: json.dump(js, open(js_p,'w'))
if __name__=='__main__':
    variant, cif, iid, outdir, celljson = sys.argv[1:6]
    make(variant, open(cif).read(), iid, outdir, json.load(open(celljson)))
