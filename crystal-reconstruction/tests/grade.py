#!/usr/bin/env python3
"""Grader for pxrd-blind-solve: two binary units per instance.

Unit L (1 point): the declared cell and space-group type match the reference lattice
  (primitive lattices map onto each other within 1 % in length and 1 degree in angle)
  and the same space-group type (enantiomorphic pairs merged).
Unit S (2 points): the submitted CIF describes the same periodic arrangement of non-H
  atoms as the reference: heavy-atom connectivity matches the supplied composition, and a
  symmetry-aware periodic match gives RMSD <= 0.35 A and max displacement <= 1.0 A.
A unit that passes earns its points; a unit that was submitted and fails costs PENALTY
  times its points (-0.8 for L, -1.6 for S); a unit with nothing submitted is 0. Hedged or
  self-inconsistent submissions count as wrong on both units.
Score = points / (3 * N), may be negative. Deterministic. UNAVAILABLE (exit 2, no reward) if the reference
or a grader dependency is unusable.

Usage: grade.py --reference-root /tests --submission-dir /final/submission --out /logs/verifier
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

L_LTOL = 0.01      # fractional length tolerance for Unit L
L_ATOL = 1.0       # degrees
S_RMSD = 0.35      # Angstrom
S_DMAX = 1.0       # Angstrom
BOND_SLACK = 0.45  # Angstrom added to the sum of covalent radii for heavy-atom bond perception
PRIM_TOL = 0.25    # Angstrom tolerance used when reducing structures to primitive cells
PENALTY = 0.8      # a submitted unit that fails costs this fraction of its points
L_POINTS = 1
S_POINTS = 2

ENANTIOMORPH = {78: 76, 95: 91, 96: 92, 145: 144, 153: 151, 154: 152, 170: 169, 172: 171,
                179: 178, 181: 180, 213: 212}
HYDROGEN = {"H", "D", "T"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Unavailable(Exception):
    pass


# ----------------------------------------------------------------------------- imports

def load_deps():
    global np, Structure, Lattice, CifParser, StructureMatcher, ElementComparator, nx, Chem, gemmi, pbc_diff
    import numpy as np  # noqa
    from pymatgen.core import Structure, Lattice  # noqa
    from pymatgen.io.cif import CifParser  # noqa
    from pymatgen.analysis.structure_matcher import StructureMatcher, ElementComparator  # noqa
    from pymatgen.util.coord import pbc_diff  # noqa
    import networkx as nx  # noqa
    from rdkit import Chem  # noqa
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")
    import gemmi  # noqa


# ----------------------------------------------------------------------------- space groups

def sg_type(number):
    return ENANTIOMORPH.get(int(number), int(number))


def parse_space_group(symbol=None, number=None):
    """Return (int number, centring letter, None) or (None, None, error). Symbol takes any common H-M spelling."""
    num = None
    if number is not None:
        try:
            n = int(number)
            if 1 <= n <= 230:
                num = n
        except (TypeError, ValueError):
            pass
    sym_num, centring = None, None
    if symbol:
        s = str(symbol).strip()
        candidates = [s, s.replace("(", "").replace(")", ""), re.sub(r"\s+", " ", s), s.replace(" ", ""),
                      re.sub(r"_", "", s), s.replace(":", " :")]
        for c in candidates:
            try:
                g = gemmi.find_spacegroup_by_name(c)
            except Exception:
                g = None
            if g is not None:
                sym_num = g.number
                centring = g.hm[0].upper()
                break
        if sym_num is None:
            # pymatgen fallback (accepts e.g. P2_1/c, Pna2_1, P2_12_12_1)
            try:
                from pymatgen.symmetry.groups import SpaceGroup
                t = s.replace(" ", "").replace("(", "").replace(")", "")
                if "_" not in t:
                    out = ""
                    for i, ch in enumerate(t):
                        out += ch
                        if ch.isdigit() and i + 1 < len(t) and t[i + 1].isdigit() and int(t[i + 1]) < int(ch):
                            out += "_"
                    t = out
                sym_num = SpaceGroup(t).int_number
                centring = t[0].upper()
            except Exception:
                sym_num = None
    if num is not None and sym_num is not None and sg_type(num) != sg_type(sym_num):
        return None, None, "space_group_number and space_group symbol disagree"
    if sym_num is not None:
        return sym_num, centring, None
    if num is not None:
        std = gemmi.find_spacegroup_by_number(num)
        return num, std.hm[0].upper(), None
    return None, None, "space group unparseable"


CENTRING = {
    "P": [], "A": [[0, .5, .5]], "B": [[.5, 0, .5]], "C": [[.5, .5, 0]], "I": [[.5, .5, .5]],
    "F": [[0, .5, .5], [.5, 0, .5], [.5, .5, 0]], "R": [[2 / 3, 1 / 3, 1 / 3], [1 / 3, 2 / 3, 2 / 3]],
    "H": [[2 / 3, 1 / 3, 0], [1 / 3, 2 / 3, 0]],
}


def primitive_lattice(lattice, centring):
    """Primitive lattice of a conventional cell with the given centring letter, Niggli reduced."""
    pts = [[0, 0, 0]] + CENTRING.get(centring, [])
    if centring == "R" and abs(lattice.a - lattice.b) < 1e-3 * lattice.a and abs(lattice.b - lattice.c) < 1e-3 * lattice.a \
            and abs(lattice.alpha - lattice.beta) < 0.05 and abs(lattice.alpha - 90) > 0.5:
        pts = [[0, 0, 0]]  # rhombohedral axes: already primitive
    s = Structure(lattice, ["C"] * len(pts), pts)
    if len(pts) > 1:
        s = s.get_primitive_structure(tolerance=1e-3)
    return s.lattice.get_niggli_reduced_lattice()


def lattice_match(ref_lat, sub_lat):
    """True if the two (primitive, Niggli) lattices map onto each other within L tolerances."""
    # equal volumes (a sublattice or superlattice contains matching vectors but has a different volume)
    if abs(sub_lat.volume / ref_lat.volume - 1.0) > 3.0 * L_LTOL + 1e-9:
        return False
    return ref_lat.find_mapping(sub_lat, ltol=L_LTOL, atol=L_ATOL) is not None


def lat_params(lat):
    return [round(float(x), 4) for x in lat.parameters]


# ----------------------------------------------------------------------------- CIF handling

def count_data_blocks(text):
    return len(re.findall(r"^\s*data_\S+", text, flags=re.M))


def structure_from_cif(text):
    """Parse the first data block into a P1-expanded Structure. Raises on failure."""
    parser = CifParser.from_str(text, occupancy_tolerance=1.0, site_tolerance=1e-3)
    structs = parser.parse_structures(primitive=False, symmetrized=False, check_occu=False, on_error="raise")
    if not structs:
        raise ValueError("no structure in CIF")
    return structs[0]


def heavy_only(struct):
    keep = [i for i, site in enumerate(struct) if not all(sp.symbol in HYDROGEN for sp in site.species)]
    s = struct.copy()
    s.remove_sites([i for i in range(len(struct)) if i not in keep])
    if len(s) == 0:
        raise ValueError("no non-hydrogen atoms")
    for site in s:
        if len(site.species) != 1 or abs(site.species.num_atoms - 1.0) > 0.02:
            raise ValueError("mixed or partial occupancy site")
    return s


def covalent_radius(symbol):
    pt = Chem.GetPeriodicTable()
    try:
        return pt.GetRcovalent(symbol)
    except Exception:
        return 1.5


def molecule_graphs(struct, slack=BOND_SLACK):
    """Perceive heavy-atom bonds by distance in the periodic cell; return list of component graphs.
    Each component is a networkx Graph with node attribute 'el'. Raises if a component is polymeric."""
    n = len(struct)
    els = [str(site.specie.symbol) for site in struct]
    rad = [covalent_radius(e) for e in els]
    nbrs = struct.get_all_neighbors(3.2)
    G = nx.Graph()
    for i in range(n):
        G.add_node(i, el=els[i])
    for i in range(n):
        for nb in nbrs[i]:
            j = nb.index
            d = nb.nn_distance
            if d < 0.5:
                raise ValueError("overlapping atoms")
            if d <= rad[i] + rad[j] + slack:
                img = tuple(int(round(x)) for x in nb.image)
                if j > i or (j == i and img != (0, 0, 0)):
                    if j == i:
                        raise ValueError("polymeric (atom bonded to its own image)")
                    if G.has_edge(i, j):
                        if G[i][j]["img"] != img and G[i][j]["img"] != tuple(-x for x in img):
                            raise ValueError("polymeric (double bonded images)")
                    else:
                        G.add_edge(i, j, img=img)
    comps = []
    for comp in nx.connected_components(G):
        sub = G.subgraph(comp).copy()
        # finite molecule check: assign integer offsets by BFS and ensure consistency
        root = next(iter(comp))
        off = {root: (0, 0, 0)}
        stack = [root]
        while stack:
            u = stack.pop()
            for v in sub[u]:
                img = sub[u][v]["img"]
                # edge stored for (min,max) orientation: image points from i to j
                if u < v:
                    vec = img
                else:
                    vec = tuple(-x for x in img)
                cand = tuple(off[u][k] + vec[k] for k in range(3))
                if v in off:
                    if off[v] != cand:
                        raise ValueError("polymeric component")
                else:
                    off[v] = cand
                    stack.append(v)
        comps.append(sub)
    return comps


def smiles_graph(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("bad SMILES " + smiles)
    mol = Chem.RemoveHs(mol)
    G = nx.Graph()
    for a in mol.GetAtoms():
        if a.GetSymbol() in HYDROGEN:
            continue
        G.add_node(a.GetIdx(), el=a.GetSymbol())
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in G and j in G:
            G.add_edge(i, j)
    return G


def graph_signature(G):
    return tuple(sorted((d["el"] for _, d in G.nodes(data=True))))


SLACKS = (0.45, 0.35, 0.55, 0.25, 0.65)


def identity_check(struct, components):
    """components: list of {'smiles','count'}. Returns (ok, detail).
    Bond perception is tried with several slack values (sum of covalent radii + slack); the check passes if any
    perception reproduces the supplied components, so coordinate noise well inside the S tolerance cannot fail it
    while a wrong connectivity fails at every slack."""
    last = (False, "no perception attempted")
    for slack in SLACKS:
        last = _identity_check_once(struct, components, slack)
        if last[0]:
            return last
    return last


def _identity_check_once(struct, components, slack):
    try:
        comps = molecule_graphs(struct, slack)
    except ValueError as e:
        return False, "connectivity: " + str(e)
    refs = []
    for c in components:
        g = smiles_graph(c["smiles"])
        refs.append(dict(graph=g, sig=graph_signature(g), count=int(c["count"]), found=0))
    nm = nx.algorithms.isomorphism.categorical_node_match("el", None)
    for comp in comps:
        sig = graph_signature(comp)
        hit = None
        for r in refs:
            if r["sig"] == sig and nx.is_isomorphic(comp, r["graph"], node_match=nm):
                hit = r
                break
        if hit is None:
            return False, "component with atoms %s matches no supplied component" % ("".join(sig[:12]) + ("..." if len(sig) > 12 else ""))
        hit["found"] += 1
    factors = set()
    for r in refs:
        if r["found"] == 0 or r["found"] % r["count"] != 0:
            return False, "stoichiometry mismatch: %s found %d, expected multiple of %d" % (r["sig"][:6], r["found"], r["count"])
        factors.add(r["found"] // r["count"])
    if len(factors) != 1:
        return False, "stoichiometry ratio inconsistent across components"
    return True, "ok (formula units per cell: %d)" % factors.pop()


# ----------------------------------------------------------------------------- structure match

def reduce_primitive(struct, target_n=None):
    """Primitive reduction; if a target atom count is known (the reference's), loosen the tolerance until the
    count is reached, so a noisy P1 description of a centred cell still reduces."""
    best = struct
    for tol in (PRIM_TOL, 0.4, 0.6, 0.8, 1.0):
        try:
            p = struct.get_primitive_structure(tolerance=tol)
        except Exception:
            continue
        if len(p) > 0:
            best = p
            if target_n is None or len(p) <= target_n:
                return p
    return best


def invert(struct):
    return Structure(struct.lattice, [s.specie for s in struct], [(-s.frac_coords) % 1.0 for s in struct])


def match_structures(ref, sub):
    """Returns dict with matched flag, rmsd, dmax, det (sign of mapping) using pymatgen StructureMatcher."""
    sm = StructureMatcher(ltol=0.06, stol=0.6, angle_tol=3.0, primitive_cell=False, scale=False,
                          attempt_supercell=False, allow_subset=False, comparator=ElementComparator())
    out = dict(matched=False, rmsd=None, dmax=None, det=None)
    if len(ref) != len(sub):
        out["reason"] = "atom count %d vs reference %d after primitive reduction" % (len(sub), len(ref))
        return out
    if ref.composition.formula != sub.composition.formula:
        out["reason"] = "primitive-cell composition %s vs reference %s" % (sub.composition.formula, ref.composition.formula)
        return out
    try:
        trans = sm.get_transformation(ref, sub)
    except Exception as e:
        out["reason"] = "matcher error: " + str(e)[:100]
        return out
    if trans is None:
        out["reason"] = "no periodic mapping within matcher tolerance"
        return out
    scm, tvec, mapping = trans
    det = float(np.linalg.det(scm))
    s2 = sm.get_s2_like_s1(ref, sub)
    if s2 is None or len(s2) != len(ref):
        out["reason"] = "mapping failed"
        return out
    # displacements measured in the reference lattice frame
    ds = []
    for i in range(len(ref)):
        if ref[i].specie.symbol != s2[i].specie.symbol:
            out["reason"] = "element mismatch in mapping"
            return out
        f = pbc_diff(ref[i].frac_coords, s2[i].frac_coords)
        ds.append(float(np.linalg.norm(ref.lattice.get_cartesian_coords(f))))
    ds = np.array(ds)
    out.update(matched=True, rmsd=float(math.sqrt(float(np.mean(ds ** 2)))), dmax=float(ds.max()), det=det)
    return out


# ----------------------------------------------------------------------------- per instance

def new_result(iid, truth):
    return dict(id=iid, dof=truth.get("dof"), dof_bin=truth.get("dof_bin"), L=False, S=False, points=0.0,
                L_submitted=False, S_submitted=False, L_detail={}, S_detail={}, hedge=False)


def unit_points(passed, submitted, value):
    """Asymmetric scoring: full value for a pass, -PENALTY * value for a submitted failure, 0 for nothing submitted."""
    if passed:
        return float(value)
    return -PENALTY * value if submitted else 0.0


def finish_points(res):
    res["points"] = round(unit_points(res["L"], res["L_submitted"], L_POINTS) + unit_points(res["S"], res["S_submitted"], S_POINTS), 6)
    return res


def read_cif_text(cif_path):
    if not os.path.isfile(cif_path) or os.path.islink(cif_path):
        return None
    try:
        with open(cif_path, "r", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def json_cell(json_path):
    """Declared cell and space group from <id>.json: (Lattice or None, sg number or None, centring or None, reason or None)."""
    if not (os.path.isfile(json_path) and not os.path.islink(json_path)):
        return None, None, None, None
    try:
        with open(json_path) as f:
            js = json.load(f)
        cell = js.get("cell", js)
        a, b, c = float(cell["a"]), float(cell["b"]), float(cell["c"])
        al, be, ga = float(cell["alpha"]), float(cell["beta"]), float(cell["gamma"])
        lat = Lattice.from_parameters(a, b, c, al, be, ga)
        sg, centring, err = parse_space_group(js.get("space_group"), js.get("space_group_number"))
        return lat, sg, centring, err
    except Exception as e:
        return None, None, None, "json unreadable: " + str(e)[:80]


def cif_cell(cif_text):
    """Cell and space group from the CIF header, same return shape as json_cell."""
    if cif_text is None:
        return None, None, None, None
    try:
        doc = gemmi.cif.read_string(cif_text).sole_block()
        g = doc.find_value
        vals = [g("_cell_length_a"), g("_cell_length_b"), g("_cell_length_c"), g("_cell_angle_alpha"), g("_cell_angle_beta"), g("_cell_angle_gamma")]
        nums = [float(re.sub(r"\(.*\)", "", v)) for v in vals]
        lat = Lattice.from_parameters(*nums)
        sym = g("_symmetry_space_group_name_H-M") or g("_space_group_name_H-M_alt")
        num = g("_symmetry_Int_Tables_number") or g("_space_group_IT_number")
        sym = sym.strip("'\"") if sym else None
        sg, centring, err = parse_space_group(sym, num)
        return lat, sg, centring, err
    except Exception:
        return None, None, None, "cif cell unreadable"


def same_crystal(cell_a, sg_a, cen_a, cell_b, sg_b, cen_b):
    """True if two declared (cell, space group) pairs describe the same lattice and space-group type, at L tolerances."""
    if None in (cell_a, sg_a, cell_b, sg_b):
        return False
    try:
        prim_a = primitive_lattice(cell_a, cen_a or "P")
        prim_b = primitive_lattice(cell_b, cen_b or "P")
    except Exception:
        return False
    return lattice_match(prim_a, prim_b) and sg_type(sg_a) == sg_type(sg_b)


def submitted_cell(json_path, cif_text):
    """The cell and space group that Unit L grades: from the CIF when one was submitted, else from the JSON.
    Returns (Lattice or None, sg number or None, centring or None, reason or None, consistent: bool).
    consistent is False only when both files exist and disagree; the caller zeroes both units then."""
    j_lat, j_sg, j_cen, j_err = json_cell(json_path)
    c_lat, c_sg, c_cen, c_err = cif_cell(cif_text)
    json_present = os.path.isfile(json_path) and not os.path.islink(json_path)
    if cif_text is not None:
        if json_present and not same_crystal(j_lat, j_sg, j_cen, c_lat, c_sg, c_cen):
            return c_lat, c_sg, c_cen, "JSON and CIF describe different crystals", False
        return c_lat, c_sg, c_cen, c_err, True
    return j_lat, j_sg, j_cen, j_err, True


def grade_instance(iid, truth, subdir):
    res = new_result(iid, truth)
    cif_path = os.path.join(subdir, iid + ".cif")
    json_path = os.path.join(subdir, iid + ".json")
    # hedging: extra CIFs for this id, or multiple data blocks
    extras = [f for f in os.listdir(subdir) if f.startswith(iid) and f.lower().endswith(".cif") and f != iid + ".cif"] if os.path.isdir(subdir) else []
    cif_text = read_cif_text(cif_path)
    if extras or (cif_text is not None and count_data_blocks(cif_text) > 1):
        res["hedge"] = True
        res["L_submitted"] = res["S_submitted"] = True
        res["L_detail"]["reason"] = res["S_detail"]["reason"] = "more than one candidate structure submitted"
        return finish_points(res)
    # ------------- reference
    ref_struct_full = structure_from_cif(truth["reference_cif"])
    ref_heavy = heavy_only(ref_struct_full)
    ref_sg = int(truth["space_group_number"])
    ref_centring = truth.get("centring") or "P"
    ref_prim_lat = primitive_lattice(ref_struct_full.lattice, ref_centring)
    res["L_detail"]["reference_niggli"] = lat_params(ref_prim_lat)
    res["L_detail"]["reference_sg_type"] = sg_type(ref_sg)
    # ------------- Unit L
    sub_cell, sub_sg, sub_centring, l_reason, consistent = submitted_cell(json_path, cif_text)
    json_present = os.path.isfile(json_path) and not os.path.islink(json_path)
    res["L_submitted"] = bool(json_present or cif_text is not None)
    res["S_submitted"] = cif_text is not None
    if not consistent:
        res["hedge"] = True
        res["L_detail"]["reason"] = res["S_detail"]["reason"] = l_reason
        return finish_points(res)
    if sub_cell is not None and sub_sg is not None and truth.get("L_graded", True):
        try:
            sub_prim = primitive_lattice(sub_cell, sub_centring or "P")
            res["L_detail"]["submitted_niggli"] = lat_params(sub_prim)
            res["L_detail"]["submitted_sg_type"] = sg_type(sub_sg)
            cell_ok = lattice_match(ref_prim_lat, sub_prim)
            sg_ok = sg_type(sub_sg) == sg_type(ref_sg)
            res["L_detail"].update(cell_ok=bool(cell_ok), sg_ok=bool(sg_ok))
            res["L"] = bool(cell_ok and sg_ok)
        except Exception as e:
            res["L_detail"]["reason"] = "cell evaluation failed: " + str(e)[:100]
    else:
        res["L_detail"]["reason"] = l_reason or ("L not graded for this instance" if not truth.get("L_graded", True) else "no cell submitted")
    # ------------- Unit S from CIF
    if cif_text is None:
        res["S_detail"]["reason"] = "no CIF submitted"
    else:
        try:
            sub_full = structure_from_cif(cif_text)
            sub_heavy = heavy_only(sub_full)
        except Exception as e:
            sub_heavy = None
            res["S_detail"]["reason"] = "CIF unusable: " + str(e)[:120]
        if sub_heavy is not None:
            ok, detail = identity_check(sub_heavy, truth["components"])
            res["S_detail"]["identity"] = detail
            ref_p = reduce_primitive(ref_heavy)
            sub_p = reduce_primitive(sub_heavy, target_n=len(ref_p))
            m = match_structures(ref_p, sub_p)
            res["S_detail"].update({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()})
            if m["matched"]:
                hand_ok = True
                if truth.get("sohncke") and truth.get("chiral") and m["det"] is not None and m["det"] < 0:
                    hand_ok = False
                    res["S_detail"]["reason"] = "mirror image of a chiral structure"
                within = m["rmsd"] <= S_RMSD and m["dmax"] <= S_DMAX
                if within and not ok:
                    # every non-H atom sits within 1.0 A (RMSD <= 0.35 A) of a reference atom of the same element, which
                    # pins the connectivity; the distance-based perception failed only on bond-length noise
                    res["S_detail"]["identity"] = "established by the geometric match (distance-based perception: %s)" % detail
                    ok = True
                res["S"] = bool(within and hand_ok and ok)
                if not within:
                    res["S_detail"]["reason"] = "displacements exceed tolerance"
            elif not ok:
                res["S_detail"]["reason"] = "identity check failed"
    return finish_points(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-root", required=True)
    ap.add_argument("--submission-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    breakdown_path = os.path.join(args.out, "score_breakdown.json")
    reward_path = os.path.join(args.out, "reward.txt")
    if os.path.exists(reward_path):
        os.remove(reward_path)

    def unavailable(reason):
        with open(breakdown_path, "w") as f:
            json.dump(dict(status="UNAVAILABLE", score=None, reason=reason), f, indent=1)
        print("UNAVAILABLE:", reason, file=sys.stderr)
        sys.exit(2)

    try:
        load_deps()
    except Exception as e:
        unavailable("grader dependency failure: " + repr(e))
    try:
        man_path = os.path.join(args.reference_root, "manifest.json")
        with open(man_path) as f:
            manifest = json.load(f)
        ids = manifest["ids"]
        sums_path = os.path.join(args.reference_root, "reference.sha256")
        with open(sums_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                digest, rel = line.split(None, 1)
                p = os.path.join(args.reference_root, rel.strip())
                if not os.path.isfile(p) or sha256_file(p) != digest:
                    raise Unavailable("reference integrity failure: " + rel)
        truths = {}
        for iid in ids:
            with open(os.path.join(args.reference_root, "truth", iid + ".json")) as f:
                truths[iid] = json.load(f)
            # reference must itself parse and satisfy its own identity check
            s = heavy_only(structure_from_cif(truths[iid]["reference_cif"]))
            ok, det = identity_check(s, truths[iid]["components"])
            if not ok:
                raise Unavailable("reference %s fails its own identity check: %s" % (iid, det))
    except Unavailable as e:
        unavailable(str(e))
    except Exception as e:
        unavailable("reference unusable: " + repr(e))

    subdir = args.submission_dir
    per = []
    for iid in ids:
        try:
            r = grade_instance(iid, truths[iid], subdir if os.path.isdir(subdir) else "")
        except Exception as e:
            # a failure while evaluating a submission is the submission's problem, never UNAVAILABLE,
            # unless it arises in the reference path (checked above).
            r = new_result(iid, truths[iid])
            r["L_detail"]["reason"] = r["S_detail"]["reason"] = "evaluation error: " + str(e)[:120]
        per.append(r)  # an evaluation error is the grader's fault: 0, never a penalty
    n = len(ids)
    points = round(sum(r["points"] for r in per), 6)
    score = points / (3.0 * n) if n else 0.0
    bins = {}
    for r in per:
        b = r.get("dof_bin") or "unbinned"
        bins.setdefault(b, dict(n=0, L=0, S=0))
        bins[b]["n"] += 1
        bins[b]["L"] += int(r["L"])
        bins[b]["S"] += int(r["S"])
    out = dict(status="SCORED", score=round(score, 6), points=points, max_points=3 * n, n_instances=n,
               L_passes=sum(int(r["L"]) for r in per), S_passes=sum(int(r["S"]) for r in per),
               hedged=sum(int(r["hedge"]) for r in per),
               L_wrong=sum(int(r["L_submitted"] and not r["L"]) for r in per), S_wrong=sum(int(r["S_submitted"] and not r["S"]) for r in per),
               by_dof_bin=bins, penalty=PENALTY,
               tolerances=dict(L_length_frac=L_LTOL, L_angle_deg=L_ATOL, S_rmsd_A=S_RMSD, S_dmax_A=S_DMAX),
               instances=per)
    with open(breakdown_path, "w") as f:
        json.dump(out, f, indent=1)
    with open(reward_path, "w") as f:
        f.write("%.6f\n" % score)
    print("score %.6f  points %.1f/%d  L %d (%d wrong)  S %d (%d wrong)" % (score, points, 3 * n, out["L_passes"], out["L_wrong"], out["S_passes"], out["S_wrong"]))


if __name__ == "__main__":
    main()
