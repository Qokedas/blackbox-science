#!/usr/bin/env python3
"""Derive the chemical composition (SMILES per component, stoichiometry), degrees of freedom and
selection flags from a deposited CIF. Authoring-side only.

Method: expand the CIF to P1 (pymatgen), perceive bonds by distance (all atoms incl. H when present),
split into molecules, group identical heavy-atom graphs, assign bond orders with RDKit DetermineBonds
using the per-moiety charge parsed from _chemical_formula_moiety (fallback: try 0, +1, -1, +2, -2).
DoF (DASH-style, heavy atoms only): per component in the asymmetric unit 6 (3 for a single heavy atom,
5 for a linear two-atom fragment) + RDKit rotatable bonds (default SMARTS, ring bonds excluded).
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict

import gemmi
import networkx as nx
import numpy as np
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser
from rdkit import Chem, RDLogger
from rdkit.Chem import rdDetermineBonds, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")
HYD = {"H", "D", "T"}
PT = Chem.GetPeriodicTable()
SOHNCKE = {1, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 75, 76, 77, 78, 79, 80, 89, 90, 91, 92, 93, 94, 95,
           96, 97, 98, 143, 144, 145, 146, 149, 150, 151, 152, 153, 154, 155, 168, 169, 170, 171, 172, 173,
           177, 178, 179, 180, 181, 182, 195, 196, 197, 198, 199, 207, 208, 209, 210, 211, 212, 213, 214}
METALS = set("Li Na K Rb Cs Be Mg Ca Sr Ba Sc Ti V Cr Mn Fe Co Ni Cu Zn Y Zr Nb Mo Tc Ru Rh Pd Ag Cd Hf Ta W Re Os Ir Pt Au Hg Al Ga In Tl Ge Sn Pb Sb Bi La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu U Th".split())


def rcov(sym):
    try:
        return PT.GetRcovalent(sym)
    except Exception:
        return 1.5


def cif_value(block, *tags):
    for t in tags:
        v = block.find_value(t)
        if v is not None and v not in ("?", "."):
            return gemmi.cif.as_string(v) if v.startswith(("'", '"', ";")) else v
    return None


def parse_moiety(s):
    """'C29 H34 Cl N2 O2 +, Cl -' -> list of (Counter(elements), charge)."""
    if not s:
        return []
    out = []
    for part in re.split(r",", s):
        part = part.strip()
        if not part:
            continue
        # leading multiplier like '2(C6 H5 O -)' or '2C6H5'
        mult = 1
        m = re.match(r"^(\d+)\s*\((.*)\)\s*(\d*[+-])?$", part)
        if m:
            mult = int(m.group(1))
            inner = m.group(2)
            ch = m.group(3) or ""
            part = inner + " " + ch
        charge = 0
        cm = re.search(r"(\d*)\s*([+-])\s*$", part)
        if cm:
            charge = (int(cm.group(1)) if cm.group(1) else 1) * (1 if cm.group(2) == "+" else -1)
            part = part[:cm.start()]
        els = Counter()
        for em in re.finditer(r"([A-Z][a-z]?)\s*(\d*\.?\d*)", part):
            n = em.group(2)
            els[em.group(1)] += float(n) if n else 1
        if els:
            for _ in range(mult):
                out.append((els, charge))
    return out


def perceive(struct):
    """Return list of molecules: each dict(indices, offsets) with consistent unwrapped Cartesian coords."""
    n = len(struct)
    els = [s.specie.symbol for s in struct]
    r = [rcov(e) for e in els]
    G = nx.Graph()
    G.add_nodes_from(range(n))
    all_nbrs = struct.get_all_neighbors(3.2)
    # hydrogens: attach each H to its single nearest heavy atom (powder H positions are too crude for distance rules)
    h_parent = {}
    for i, nbrs in enumerate(all_nbrs):
        if els[i] in HYD:
            cands = [(nb.nn_distance, nb) for nb in nbrs if els[nb.index] not in HYD]
            if cands:
                d, nb = min(cands, key=lambda t: t[0])
                if d < 1.6:
                    h_parent[i] = (nb.index, tuple(int(round(v)) for v in nb.image))
    for i, (j, img) in h_parent.items():
        G.add_edge(i, j, img=img, frm=i)
    for i, nbrs in enumerate(all_nbrs):
        if els[i] in HYD:
            continue
        for nb in nbrs:
            j = nb.index
            d = nb.nn_distance
            if d < 0.4:
                raise ValueError("overlapping atoms (%.2f A)" % d)
            if els[j] in HYD:
                continue
            slack = 0.45
            if d <= r[i] + r[j] + slack:
                img = tuple(int(round(v)) for v in nb.image)
                if i == j:
                    raise ValueError("polymeric: atom bonded to own image")
                if G.has_edge(i, j):
                    if G[i][j]["img"] not in (img, tuple(-v for v in img)) and G[i][j]["from"] != i:
                        pass
                    continue
                G.add_edge(i, j, img=img, frm=i)
    mols = []
    for comp in nx.connected_components(G):
        sub = G.subgraph(comp)
        root = min(comp)
        off = {root: np.zeros(3)}
        stack = [root]
        while stack:
            u = stack.pop()
            for v in sub[u]:
                e = sub[u][v]
                vec = np.array(e["img"], dtype=float)
                if e["frm"] != u:
                    vec = -vec
                cand = off[u] + vec
                if v in off:
                    if np.any(np.abs(off[v] - cand) > 1e-6):
                        raise ValueError("polymeric component")
                else:
                    off[v] = cand
                    stack.append(v)
        idx = sorted(comp)
        cart = np.array([struct.lattice.get_cartesian_coords(struct[i].frac_coords + off[i]) for i in idx])
        mols.append(dict(indices=idx, cart=cart, els=[els[i] for i in idx]))
    return mols


def heavy_graph(mol_dict, struct):
    idx = [i for i, e in zip(mol_dict["indices"], mol_dict["els"]) if e not in HYD]
    G = nx.Graph()
    pos = {i: mol_dict["cart"][mol_dict["indices"].index(i)] for i in idx}
    for i in idx:
        G.add_node(i, el=struct[i].specie.symbol)
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            i, j = idx[a], idx[b]
            d = np.linalg.norm(pos[i] - pos[j])
            if d <= rcov(G.nodes[i]["el"]) + rcov(G.nodes[j]["el"]) + 0.45:
                G.add_edge(i, j)
    return G


def wl_hash(G):
    return nx.weisfeiler_lehman_graph_hash(G, node_attr="el")


def rdkit_from_xyz(els, cart, charge):
    xyz = "%d\n\n" % len(els) + "\n".join("%s %.5f %.5f %.5f" % (e if e not in ("D", "T") else "H", *c) for e, c in zip(els, cart))
    mol = Chem.MolFromXYZBlock(xyz)
    if mol is None:
        return None
    try:
        rdDetermineBonds.DetermineBonds(mol, charge=charge, useHueckel=False, allowChargedFragments=True, embedChiral=True)
        Chem.SanitizeMol(mol)
    except Exception:
        return None
    return mol


def component_smiles(els, cart, charges_to_try):
    has_h = any(e in HYD for e in els)
    for ch in charges_to_try:
        mol = rdkit_from_xyz(els, cart, ch)
        if mol is not None:
            try:
                Chem.AssignStereochemistryFrom3D(mol)
            except Exception:
                pass
            for a in mol.GetAtoms():
                if a.GetSymbol() in ("N", "P", "S"):
                    a.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
            heavy = Chem.RemoveHs(mol, sanitize=False)
            try:
                Chem.SanitizeMol(heavy)
            except Exception:
                pass
            smi = Chem.MolToSmiles(heavy)
            return dict(smiles=smi, charge=ch, has_h=has_h, ok=True, mol=heavy)
    return dict(smiles=None, charge=None, has_h=has_h, ok=False, mol=None)


def dof_of(mol, n_heavy):
    if n_heavy == 1:
        return 3, 0
    if n_heavy == 2:
        return 5, 0
    rot = rdMolDescriptors.CalcNumRotatableBonds(mol) if mol is not None else 0
    return 6, rot


def analyse(cif_text, cod_id=None):
    doc = gemmi.cif.read_string(cif_text)
    block = doc.sole_block() if len(doc) == 1 else doc[0]
    out = dict(cod_id=cod_id, block=block.name)
    out["formula_sum"] = cif_value(block, "_chemical_formula_sum")
    out["formula_moiety"] = cif_value(block, "_chemical_formula_moiety")
    out["name"] = cif_value(block, "_chemical_name_common", "_chemical_name_systematic")
    out["sg_symbol"] = cif_value(block, "_space_group_name_H-M_alt", "_symmetry_space_group_name_H-M")
    num = cif_value(block, "_space_group_IT_number", "_symmetry_Int_Tables_number")
    out["sg_number"] = int(num) if num else None
    if out["sg_number"] is None and out["sg_symbol"]:
        for cand in (out["sg_symbol"], out["sg_symbol"].replace(" ", ""), re.sub(r"\s+", " ", out["sg_symbol"])):
            g = gemmi.find_spacegroup_by_name(cand)
            if g is not None:
                out["sg_number"] = g.number
                break
    if out["sg_number"] is None:
        hall = cif_value(block, "_space_group_name_Hall", "_symmetry_space_group_name_Hall")
        if hall:
            try:
                ops = gemmi.symops_from_hall(hall)
                g = gemmi.find_spacegroup_by_ops(ops)
                if g is not None:
                    out["sg_number"] = g.number
            except Exception:
                pass
    if out["sg_number"] is None:
        xyz = block.find_values("_space_group_symop_operation_xyz") or block.find_values("_symmetry_equiv_pos_as_xyz")
        if xyz:
            try:
                ops = gemmi.GroupOps([gemmi.Op(gemmi.cif.as_string(o)) for o in xyz])
                g = gemmi.find_spacegroup_by_ops(ops)
                if g is not None:
                    out["sg_number"] = g.number
            except Exception:
                pass
    out["Z"] = cif_value(block, "_cell_formula_units_Z")
    out["temperature"] = cif_value(block, "_diffrn_ambient_temperature", "_cell_measurement_temperature")
    out["wavelength"] = cif_value(block, "_diffrn_radiation_wavelength")
    out["radiation_type"] = cif_value(block, "_diffrn_radiation_type")
    out["radiation_probe"] = cif_value(block, "_diffrn_radiation_probe")
    out["source"] = cif_value(block, "_diffrn_source")
    out["device"] = cif_value(block, "_diffrn_measurement_device_type")
    out["geometry"] = cif_value(block, "_pd_instr_geometry")
    out["mounting"] = cif_value(block, "_pd_spec_mounting")
    out["mount_mode"] = cif_value(block, "_pd_spec_mount_mode")
    out["spec_shape"] = cif_value(block, "_pd_spec_shape")
    out["rwp"] = cif_value(block, "_pd_proc_ls_prof_wR_factor")
    out["rp"] = cif_value(block, "_pd_proc_ls_prof_R_factor")
    out["rwp_expected"] = cif_value(block, "_pd_proc_ls_prof_wR_expected")
    out["R_I"] = cif_value(block, "_refine_ls_R_I_factor")
    out["pref_orient"] = cif_value(block, "_pd_proc_ls_pref_orient_corr")
    out["method_text"] = cif_value(block, "_computing_structure_solution")
    out["refine_special"] = (cif_value(block, "_refine_special_details") or "")[:600]
    out["journal"] = cif_value(block, "_journal_name_full")
    out["year"] = cif_value(block, "_journal_year")
    out["doi"] = cif_value(block, "_journal_paper_doi")
    out["title"] = cif_value(block, "_publ_section_title")
    out["ccdc"] = cif_value(block, "_database_code_depnum_ccdc_archive", "_database_code_CSD")
    out["source_file"] = cif_value(block, "_cod_data_source_file")
    # disorder / occupancy
    occ = block.find_values("_atom_site_occupancy")
    dis = block.find_values("_atom_site_disorder_group")
    out["partial_occupancy"] = any(abs(float(re.sub(r"\(.*\)", "", o)) - 1) > 0.01 for o in occ if o not in ("?", ".")) if occ else False
    out["disorder_group"] = any(d not in (".", "?") for d in dis) if dis else False
    types = [t for t in block.find_values("_atom_site_type_symbol")] or [re.match(r"[A-Z][a-z]?", l).group(0) for l in block.find_values("_atom_site_label")]
    els_present = sorted(set(re.match(r"[A-Z][a-z]?", t).group(0) for t in types))
    out["elements"] = els_present
    out["has_H_atoms"] = any(e in HYD for e in els_present)
    out["contains_metal"] = any(e in METALS for e in els_present)
    # structure
    parser = CifParser.from_str(cif_text, occupancy_tolerance=1.05, site_tolerance=1e-3)
    struct = parser.parse_structures(primitive=False, symmetrized=False, check_occu=False, on_error="raise")[0]
    out["cell"] = [round(float(v), 5) for v in struct.lattice.parameters]
    out["volume"] = round(float(struct.volume), 3)
    out["n_atoms_cell"] = len(struct)
    mixed = [i for i, site in enumerate(struct) if len(site.species) != 1 or abs(site.species.num_atoms - 1.0) > 0.02]
    out["mixed_or_partial_sites"] = len(mixed)
    if mixed:
        out["disordered"] = True
        out["components"] = []
        out["dof"] = None
        out["all_smiles_ok"] = False
        return out
    out["disordered"] = bool(out["partial_occupancy"] or out["disorder_group"])
    out["n_heavy_cell"] = sum(1 for s in struct if s.specie.symbol not in HYD)
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    try:
        spg_found = SpacegroupAnalyzer(struct, symprec=0.1, angle_tolerance=2).get_space_group_number()
        spg_loose = SpacegroupAnalyzer(struct, symprec=0.3, angle_tolerance=3).get_space_group_number()
    except Exception:
        spg_found = spg_loose = None
    out["spglib_sg_0.1"] = spg_found
    out["spglib_sg_0.3"] = spg_loose
    mols = perceive(struct)
    moiety = parse_moiety(out["formula_moiety"])
    groups = defaultdict(list)
    for m in mols:
        groups[wl_hash(heavy_graph(m, struct))].append(m)
    comps = []
    total_dof = 0
    gen_mult = len(gemmi.find_spacegroup_by_number(out["sg_number"]).operations()) if out["sg_number"] else None
    chiral_any = False
    for h, ms in groups.items():
        m = ms[0]
        els_all = m["els"]
        heavy_els = Counter(e for e in els_all if e not in HYD)
        h_count = sum(1 for e in els_all if e in HYD)
        # charge from moiety formula by heavy-atom element match
        charges = []
        for els_c, ch in moiety:
            hc = Counter({k: v for k, v in els_c.items() if k not in HYD})
            if all(abs(hc.get(k, 0) - heavy_els.get(k, 0)) < 0.01 for k in set(hc) | set(heavy_els)):
                charges.append(ch)
        tries = list(dict.fromkeys(charges + [0, 1, -1, 2, -2, 3, -3]))
        cs = component_smiles(els_all, m["cart"], tries) if m["cart"].shape[0] >= 1 else dict(smiles=None, ok=False)
        n_heavy = sum(heavy_els.values())
        rigid, rot = dof_of(cs.get("mol"), n_heavy)
        count_cell = len(ms)
        per_asym = count_cell / gen_mult if gen_mult else None
        chiral = False
        smiles_flat = None
        if cs.get("mol") is not None:
            try:
                flat = Chem.Mol(cs["mol"])
                Chem.RemoveStereochemistry(flat)
                smiles_flat = Chem.MolToSmiles(flat)
                # true stereocentres from the constitution (CIP-based, legacy implementation)
                centers = Chem.FindMolChiralCenters(flat, includeUnassigned=True, useLegacyImplementation=True)
                chiral = len(centers) > 0
            except Exception:
                chiral = False
        chiral_any = chiral_any or chiral
        if n_heavy == 1:
            el = next(iter(heavy_els))
            default = {"Cl": -1, "Br": -1, "I": -1, "F": -1}.get(el, 0)
            if el == "N" and h_count == 4:
                default = 1
            ch = charges[0] if charges else default
            if el == "O" and h_count == 2 and ch == 0:
                ion = "O"
            else:
                ion = "[%s%s%s]" % (el, ("H%d" % h_count if h_count else ""), ("" if ch == 0 else ("+" if ch == 1 else "-" if ch == -1 else "%+d" % ch)))
            cs["smiles"] = ion
            cs["charge"] = ch
            cs["ok"] = True
            smiles_flat = ion
            chiral = False
        comps.append(dict(smiles=cs.get("smiles"), smiles_flat=smiles_flat, smiles_shipped=(cs.get("smiles") if chiral else smiles_flat), charge=cs.get("charge"), heavy_formula="".join("%s%d" % (k, v) for k, v in sorted(heavy_els.items())),
                          n_heavy=n_heavy, n_H=h_count, count_in_cell=count_cell, per_asym=per_asym, rigid_dof=rigid, torsions=rot,
                          chiral_centres=chiral, smiles_ok=cs.get("ok", False)))
        if per_asym:
            total_dof += per_asym * (rigid + rot)
    comps.sort(key=lambda c: -c["n_heavy"])
    out["components"] = comps
    out["n_components_asym"] = sum(c["per_asym"] for c in comps if c["per_asym"]) if gen_mult else None
    out["Zprime"] = max((c["per_asym"] for c in comps if c["per_asym"]), default=None)
    out["dof"] = round(total_dof, 2)
    out["sohncke"] = out["sg_number"] in SOHNCKE if out["sg_number"] else None
    out["chiral_molecule"] = chiral_any
    out["all_smiles_ok"] = all(c["smiles_ok"] for c in comps)
    for c in comps:
        c.pop("mol", None)
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            r = analyse(open(p, errors="replace").read(), cod_id=p.split("/")[-1].split(".")[0])
            print(json.dumps(r, indent=1, default=str))
        except Exception as e:
            print(p, "ERROR", repr(e))
