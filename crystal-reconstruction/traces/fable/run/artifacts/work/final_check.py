import warnings; warnings.filterwarnings('ignore')
import os, json, glob, sys
from pymatgen.io.cif import CifParser
from pymatgen.symmetry.groups import SpaceGroup
sub = '/app/results/submission'
ids = json.load(open('/app/data/instances.json'))
if isinstance(ids, dict): ids = ids.get('instances', list(ids.keys()))
ids = [i if isinstance(i, str) else i.get('id') for i in ids]
files = sorted(os.listdir(sub))
print('files:', len(files))
for f in files:
    stem = f.rsplit('.', 1)[0]
    if stem not in ids and stem.split('_')[0] in ids:
        print('!! EXTRA FILE (would zero the instance):', f)
    elif stem not in ids:
        print('!! unknown file', f)
for iid in ids:
    js = f'{sub}/{iid}.json'; cf = f'{sub}/{iid}.cif'
    if not os.path.exists(js) and not os.path.exists(cf):
        continue
    line = iid
    if os.path.exists(js):
        d = json.load(open(js))
        c = d['cell']
        line += f"  JSON {d['space_group']} ({d.get('space_group_number')}) {c['a']:.4f} {c['b']:.4f} {c['c']:.4f} {c['alpha']:.3f} {c['beta']:.3f} {c['gamma']:.3f}"
        try:
            sg = SpaceGroup(d['space_group'].replace(' ', '')) if False else None
        except Exception as e:
            line += f' !! SG symbol problem {e}'
    else:
        line += '  NO JSON'
    if os.path.exists(cf):
        try:
            txt = open(cf).read()
            nblocks = sum(1 for l in txt.splitlines() if l.startswith('data_'))
            s = CifParser(cf).parse_structures(primitive=False)[0]
            heavy = [x for x in s if x.specie.symbol != 'H']
            line += f'  CIF ok: {len(s)} atoms ({len(heavy)} heavy), blocks={nblocks}, sg={s.get_space_group_info()[0]}'
            if nblocks != 1: line += ' !! MULTIPLE BLOCKS'
        except Exception as e:
            line += f'  !! CIF PARSE ERROR {e}'
    else:
        line += '  (no cif)'
    print(line)
