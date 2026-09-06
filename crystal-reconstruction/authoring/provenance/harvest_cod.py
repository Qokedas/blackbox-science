#!/usr/bin/env python3
"""Harvest COD entries whose hkl file is a pdCIF profile: pair cifs/<id>.cif with cod_hkl/<id>.hkl.
Writes records in the same shape as harvest_epmc.py (source='COD')."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdcif, composition
root, ids_path, out_path, meta_path = sys.argv[1:5]
ids = json.load(open(ids_path)); meta = {x['file']: x for x in json.load(open(meta_path))}
fo = open(out_path, 'w')
for i in ids:
    cif = os.path.join(root, 'cifs', i + '.cif'); hkl = os.path.join(root, 'cod_hkl', i[0], i[1:3], i[3:5], i + '.hkl')
    if not (os.path.exists(cif) and os.path.exists(hkl)):
        continue
    rec = dict(pmcid='COD' + i, source='COD', cod_id=i, title=meta.get(i, {}).get('title'), journal=meta.get(i, {}).get('journal'), year=meta.get(i, {}).get('year'), doi=meta.get(i, {}).get('doi'), structure_file='cifs/' + i + '.cif', block=None)
    try:
        r = pdcif.extract(open(hkl, errors='replace').read())
        if r is not None:
            x, y, s, prov = r
            rec['profile'] = dict(file=os.path.relpath(hkl, root), block=prov['block'], prov=prov, x0=float(x[0]), x1=float(x[-1]), n=int(prov['n_points']))
        else:
            rec['profile'] = None
    except Exception as e:
        rec['profile'] = None; rec['profile_error'] = repr(e)[:200]
    try:
        rec['analysis'] = composition.analyse(open(cif, errors='replace').read(), cod_id=i)
        rec['block'] = rec['analysis']['block']
    except Exception as e:
        rec['analysis_error'] = repr(e)[:300]
    fo.write(json.dumps(rec, default=str) + '\n'); fo.flush()
fo.close()
