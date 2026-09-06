#!/usr/bin/env python3
"""Build the solver-visible instances and the private truth from the selected records.

Input : selection.json (list of dicts: pmcid, block, structure_file, profile{file,block}, dof_bin,
        optional overrides: components, instrument, name_note, L_graded)
        harvest root (where PMC*/ and COD files live), SECRET_SALT
Output: <task>/environment/data/instances/<id>/{pattern.xye,instrument.json,composition.json}
        <task>/environment/data/instances.json
        <task>/tests/truth/<id>.json, <task>/tests/manifest.json, <task>/tests/reference.sha256
        <keys>/manifest_SECRET.json
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
from fractions import Fraction

import gemmi
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdcif  # noqa
import composition  # noqa

KEEP_PREFIX = ("_cell_length", "_cell_angle", "_cell_volume", "_cell_formula_units_Z", "_symmetry_space_group_name_H-M",
               "_symmetry_Int_Tables_number", "_symmetry_cell_setting", "_space_group_name_H-M_alt", "_space_group_IT_number",
               "_space_group_crystal_system", "_space_group_name_Hall", "_symmetry_space_group_name_Hall",
               "_symmetry_equiv_pos_as_xyz", "_symmetry_equiv_pos_site_id", "_space_group_symop_operation_xyz", "_space_group_symop_id",
               "_atom_site_label", "_atom_site_type_symbol", "_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z",
               "_atom_site_occupancy", "_atom_site_U_iso_or_equiv", "_atom_site_B_iso_or_equiv", "_atom_site_adp_type",
               "_atom_site_symmetry_multiplicity", "_atom_site_site_symmetry_multiplicity", "_atom_site_calc_flag",
               "_atom_site_disorder_group", "_atom_site_disorder_assembly", "_atom_type_symbol", "_atom_type_scat_source",
               "_atom_type_description", "_atom_type_scat_dispersion_real", "_atom_type_scat_dispersion_imag")


def clean_reference_cif(block, name):
    d = gemmi.cif.Document()
    b = d.add_new_block(name)
    for item in block:
        if item.pair is not None:
            if item.pair[0].startswith(KEEP_PREFIX):
                b.set_pair(item.pair[0], item.pair[1])
        elif item.loop is not None:
            tags = item.loop.tags
            keep_idx = [i for i, t in enumerate(tags) if t.startswith(KEEP_PREFIX)]
            if keep_idx:
                lp = b.init_loop("", [tags[i] for i in keep_idx])
                for r in range(item.loop.length()):
                    lp.add_row([item.loop[r, c] for c in keep_idx])
    return d.as_string()


def as_float(v):
    try:
        return float(re.sub(r"\(.*\)", "", str(v)))
    except Exception:
        return None


def guess_geometry(meta, ana):
    text = " ".join(str(x) for x in [meta.get("_pd_instr_geometry"), meta.get("_pd_spec_mount_mode"), meta.get("_pd_spec_mounting"),
                                     meta.get("_diffrn_measurement_device_type"), ana.get("geometry"), ana.get("mount_mode"), ana.get("mounting"),
                                     ana.get("device"), ana.get("spec_shape")] if x).lower()
    if "capillar" in text or "transmission" in text or "debye" in text or "cylinder" in text:
        geom = "transmission (capillary / Debye-Scherrer)"
    elif "reflection" in text or "bragg" in text or "flat" in text:
        geom = "reflection (flat plate / Bragg-Brentano)"
    else:
        geom = "not stated"
    return geom, text


def instrument_json(prov, ana, override=None):
    meta = prov["meta"]
    wl_list = meta.get("_diffrn_radiation_wavelength_list")
    wl = as_float(meta.get("_diffrn_radiation_wavelength") or meta.get("_pd_proc_wavelength") or ana.get("wavelength"))
    rad_type = meta.get("_diffrn_radiation_type") or ana.get("radiation_type")
    source = meta.get("_diffrn_source") or ana.get("source") or meta.get("_pd_instr_source_type")
    temp = as_float(meta.get("_diffrn_ambient_temperature") or ana.get("temperature"))
    geom, geom_text = guess_geometry(meta, ana)
    out = dict(
        radiation=dict(type=re.sub(r"\\a|~", "", rad_type).strip() if rad_type else "X-ray",
                       wavelength_A=wl,
                       wavelengths_A=[as_float(w) for w in wl_list] if wl_list else ([wl] if wl else None),
                       wavelength_weights=[as_float(w) for w in meta.get("_diffrn_radiation_wavelength_wt_list", [])] or None,
                       monochromator=meta.get("_diffrn_radiation_monochromator") or None,
                       source=source or None),
        geometry=geom,
        geometry_source_text=None,
        temperature_K=temp,
        two_theta_range_deg=[round(prov["x0"], 4), round(prov["x1"], 4)] if "x0" in prov else None,
        n_points=prov["n_points"],
        intensity_column="observed net intensity (instrument background subtracted by the depositors)" if prov["background_subtracted"] else "observed total intensity",
        sigma_column=prov["sigma_tag"].replace("(su)", " standard uncertainties") if "assumed" not in prov["sigma_tag"] else "sqrt(max(I,1)); counting statistics assumed",
        pattern_units="two_theta_deg intensity sigma",
        notes=[],
    )
    if wl is not None and abs(wl - 1.5418) < 0.0005 and not wl_list:
        out["notes"].append("the depositors recorded Cu K-alpha as a single wavelength 1.5418 A (the K-alpha1/K-alpha2 weighted mean); whether the K-alpha2 component is present in the data is not stated")
    if override:
        for k, v in override.items():
            out[k] = v
    return out


def integer_ratio(vals):
    fr = [Fraction(v).limit_denominator(12) for v in vals]
    den = 1
    for f in fr:
        den = den * f.denominator // math.gcd(den, f.denominator)
    ints = [int(f * den) for f in fr]
    g = 0
    for v in ints:
        g = math.gcd(g, v)
    return [v // g for v in ints]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True)
    ap.add_argument("--harvest-root", required=True)
    ap.add_argument("--cod-root", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--keys", required=True)
    args = ap.parse_args()
    salt = open(os.path.join(args.keys, "SECRET_SALT")).read().strip()
    sel = json.load(open(args.selection))
    data_root = os.path.join(args.task, "environment", "data", "instances")
    truth_root = os.path.join(args.task, "tests", "truth")
    os.makedirs(data_root, exist_ok=True)
    os.makedirs(truth_root, exist_ok=True)
    ids = []
    key = {}
    index = []
    for rec in sel:
        src = rec["pmcid"]
        block_name = rec["block"]
        iid = "X" + hashlib.sha1((salt + ":" + src + ":" + str(block_name)).encode()).hexdigest()[:7]
        root = args.cod_root if src.startswith("COD") else args.harvest_root
        stext = open(os.path.join(root, rec["structure_file"]), errors="replace").read()
        doc = gemmi.cif.read_string(stext)
        block = None
        for b in doc:
            if b.name == block_name or block_name is None:
                block = b
                break
        if block is None:
            raise SystemExit("block not found " + src + " " + str(block_name))
        ref_cif = clean_reference_cif(block, "ref")
        ana = composition.analyse(ref_cif, cod_id=src)
        # metadata (radiation, temperature, name) lives in the full block, not in the cleaned reference
        full_d = gemmi.cif.Document()
        full_d.add_copied_block(block)
        ana_meta = composition.analyse(full_d.as_string(), cod_id=src)
        for k in ("name", "wavelength", "radiation_type", "source", "temperature", "geometry", "mounting", "mount_mode", "device", "spec_shape", "rwp", "formula_moiety"):
            ana[k] = ana_meta.get(k)
        # profile
        ptext = open(os.path.join(root, rec["profile"]["file"]), errors="replace").read()
        pdoc = gemmi.cif.read_string(ptext)
        pblock = [b for b in pdoc if b.name == rec["profile"]["block"]][0]
        pd_d = gemmi.cif.Document()
        pd_d.add_copied_block(pblock)
        x, y, s, prov = pdcif.extract(pd_d.as_string())
        # keep physically meaningful angles only (some detector scans start below zero)
        keep = x >= 0.5
        if (~keep).any():
            x, y, s = x[keep], y[keep], s[keep]
            prov["n_points"] = int(len(x))
            prov["clipped_below_0p5deg"] = True
        # composition: components from analysis, allow override
        comps = rec.get("components")
        if comps is None:
            per = [c["per_asym"] for c in ana["components"]]
            counts = integer_ratio(per)
            comps = []
            for c, n in zip(ana["components"], counts):
                comps.append(dict(smiles=c["smiles_shipped"], count=n, charge=c["charge"], heavy_atoms=c["n_heavy"]))
        chiral = rec.get("chiral", ana["chiral_molecule"])
        sg_num = ana["sg_number"]
        sym = ana["sg_symbol"] or gemmi.find_spacegroup_by_number(sg_num).hm
        centring = sym.strip()[0].upper()
        # instance dir
        idir = os.path.join(data_root, iid)
        os.makedirs(idir, exist_ok=True)
        pdcif.write_xye(os.path.join(idir, "pattern.xye"), x, y, s, header_lines=["columns: two_theta_deg intensity sigma"])
        inst = instrument_json(dict(prov, x0=float(x[0]), x1=float(x[-1])), ana, rec.get("instrument"))
        json.dump(inst, open(os.path.join(idir, "instrument.json"), "w"), indent=1)
        comp_out = dict(components=[dict(smiles=c["smiles"], count=c["count"], charge=c.get("charge", 0)) for c in comps],
                        sample=rec.get("sample_note", "crystalline powder of a single phase; composition as listed (one formula unit = the listed components with the listed counts)"),
                        stereochemistry_note=("SMILES carry the stereochemistry of the crystallised compound; preserve it." if chiral else "achiral components; no stereodescriptors."),
                        hydrogens_note="hydrogen positions and protonation sites are not assessed; SMILES show the protonation state reported by the depositors")
        json.dump(comp_out, open(os.path.join(idir, "composition.json"), "w"), indent=1)
        truth = dict(id=iid, reference_cif=ref_cif, space_group_number=sg_num, space_group_symbol=sym, centring=centring,
                     sohncke=ana["sohncke"], chiral=bool(chiral), L_graded=rec.get("L_graded", True), dof=ana["dof"], dof_bin=rec["dof_bin"],
                     zprime=ana["Zprime"], n_heavy_asym=sum(c["n_heavy"] * c["per_asym"] for c in ana["components"]),
                     components=[dict(smiles=c["smiles"], count=c["count"]) for c in comps])
        truth.update(rec.get("truth_extra", {}))
        json.dump(truth, open(os.path.join(truth_root, iid + ".json"), "w"), indent=1)
        ids.append(iid)
        key[iid] = dict(source=src, block=block_name, doi=rec.get("doi"), title=rec.get("title"), name=ana.get("name"), structure_file=rec["structure_file"],
                        profile_file=rec["profile"]["file"], cell=ana["cell"], sg=sym, dof=ana["dof"], zprime=ana["Zprime"], year=rec.get("year"), journal=rec.get("journal"),
                        wavelength=inst["radiation"]["wavelength_A"], source_type=inst["radiation"]["source"], temperature=inst["temperature_K"], n_points=inst["n_points"],
                        rwp=ana.get("rwp"), notes=rec.get("notes"))
        index.append(dict(id=iid, n_points=inst["n_points"], two_theta_range_deg=inst["two_theta_range_deg"], n_components=len(comps),
                          heavy_atoms_per_formula_unit=sum(c["count"] * c["heavy_atoms"] for c in comps) if all("heavy_atoms" in c for c in comps) else None))
        print(iid, src, block_name, ana.get("name"), sym, ana["dof"], ana["Zprime"], inst["n_points"], inst["radiation"]["wavelength_A"], flush=True)
    ids.sort()
    index.sort(key=lambda r: r["id"])
    json.dump(dict(ids=ids, n=len(ids), instances=index), open(os.path.join(args.task, "environment", "data", "instances.json"), "w"), indent=1)
    json.dump(dict(ids=ids, n=len(ids), points_per_instance=3), open(os.path.join(args.task, "tests", "manifest.json"), "w"), indent=1)
    with open(os.path.join(args.task, "tests", "reference.sha256"), "w") as f:
        for iid in ids:
            p = os.path.join(truth_root, iid + ".json")
            f.write(hashlib.sha256(open(p, "rb").read()).hexdigest() + "  truth/" + iid + ".json\n")
    json.dump(key, open(os.path.join(args.keys, "manifest_SECRET.json"), "w"), indent=1)
    print("built", len(ids))


if __name__ == "__main__":
    main()
