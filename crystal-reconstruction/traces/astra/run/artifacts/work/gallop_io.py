"""GALLOP serialization with the full space-group setting retained."""
import os,json,xml.etree.ElementTree as ET,numpy as np,gemmi
from gallop.structure import Structure
from pymatgen.symmetry.groups import SpaceGroup

def load_structure(path):
    data=json.load(open(path));original=int(data['sg_number'][0]);number=int(data.get('original_sg_number',[original])[0] or original)
    data['sg_number']=[number,False]
    s=Structure();s.from_json(json.dumps(data))
    symbol=data.get('sg_symbol',[None])[0]
    if symbol is None:
        directory=os.path.dirname(path)
        for fn in [directory+'/base.xml',os.path.dirname(directory)+'/base.xml']:
            if os.path.exists(fn):
                root=ET.parse(fn).getroot();cr=root.find('Crystal')
                if cr is not None:symbol=cr.attrib['SpaceGroup'];break
    if symbol is None:symbol=gemmi.find_spacegroup_by_number(number).xhm()
    s.space_group=SpaceGroup(symbol);s.sg_symbol=symbol
    s.affine_matrices=np.array([op.affine_matrix for op in s.space_group.symmetry_ops]);s.sg_number=original
    return s
