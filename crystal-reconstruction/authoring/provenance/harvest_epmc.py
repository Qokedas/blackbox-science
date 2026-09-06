#!/usr/bin/env python3
"""Harvest powder profiles + structures from Europe PMC supplementary zips of IUCr powder papers.

For each PMC directory (containing supp.zip): unzip, scan every text file for pdCIF profile loops
(pdcif.extract) and for structural blocks (_atom_site_fract_x). Pair profile blocks with structure
blocks by block name (fallback: unique pairing). Run composition.analyse on the structural block.
Writes one JSON line per (paper, structure block) to records.jsonl. Resumable: skips PMCIDs present.
"""
import json
import os
import re
import sys
import traceback
import zipfile

import gemmi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdcif  # noqa
import composition  # noqa

PROFILE_RE = re.compile(r"_pd_(meas|proc)_(intensity|counts)_(total|net)")


def text_files(d):
    for root, _, files in os.walk(d):
        for f in files:
            if f.lower().endswith((".cif", ".rtv", ".hkl", ".txt", ".fcf", ".pdcif", ".xye", ".dat")):
                yield os.path.join(root, f)


def split_blocks(text):
    """Return list of (name, block_text) using gemmi for robustness."""
    try:
        doc = gemmi.cif.read_string(text)
    except Exception:
        return []
    out = []
    for b in doc:
        out.append((b.name, b))
    return out


def block_to_cif_text(block):
    d = gemmi.cif.Document()
    d.add_copied_block(block)
    return d.as_string()


def main(root, out_path, meta_path=None):
    meta = {}
    if meta_path and os.path.exists(meta_path):
        for r in json.load(open(meta_path)):
            if r.get("pmcid"):
                meta[r["pmcid"]] = r
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            try:
                done.add(json.loads(line)["pmcid"])
            except Exception:
                pass
    fo = open(out_path, "a")
    pmcs = sorted(d for d in os.listdir(root) if d.startswith("PMC") and os.path.isdir(os.path.join(root, d)))
    for pmc in pmcs:
        if pmc in done:
            continue
        d = os.path.join(root, pmc)
        z = os.path.join(d, "supp.zip")
        if not os.path.isfile(z) or os.path.getsize(z) == 0:
            continue
        try:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(d)
        except zipfile.BadZipFile:
            fo.write(json.dumps(dict(pmcid=pmc, error="bad zip")) + "\n")
            continue
        profiles = []   # (file, blockname, prov, x, y, s)
        structures = []  # (file, blockname, block)
        for f in text_files(d):
            try:
                txt = open(f, errors="replace").read()
            except Exception:
                continue
            if "data_" not in txt:
                continue
            has_prof = bool(PROFILE_RE.search(txt))
            if has_prof:
                # extract per block: pdcif.extract picks the best block; do per-block by splitting
                try:
                    doc = gemmi.cif.read_string(txt)
                except Exception:
                    doc = None
                if doc is not None:
                    for b in doc:
                        bt = block_to_cif_text(b)
                        if not PROFILE_RE.search(bt):
                            continue
                        try:
                            r = pdcif.extract(bt)
                        except Exception as e:
                            r = None
                        if r is not None and r[3]["n_points"] >= 200:
                            x, y, s, prov = r
                            profiles.append(dict(file=os.path.relpath(f, root), block=b.name, prov=prov,
                                                 x0=float(x[0]), x1=float(x[-1]), n=int(prov["n_points"])))
            try:
                doc = gemmi.cif.read_string(txt)
            except Exception:
                continue
            for b in doc:
                if b.find_values("_atom_site_fract_x") and len(b.find_values("_atom_site_fract_x")) >= 3:
                    structures.append((os.path.relpath(f, root), b.name, b))
        paper = meta.get(pmc, {})
        base = dict(pmcid=pmc, title=paper.get("title"), journal=paper.get("journalTitle"), year=paper.get("pubYear"),
                    doi=paper.get("doi"), n_profiles=len(profiles), n_structures=len(structures))
        if not structures:
            base["error"] = "no structure block"
            fo.write(json.dumps(base) + "\n")
            fo.flush()
            continue
        # de-duplicate structure blocks with identical block names across files (cif vs rtv copies): prefer .cif
        seen = {}
        for f, bn, b in structures:
            key = bn
            if key not in seen or f.lower().endswith(".cif"):
                seen[key] = (f, bn, b)
        for bn, (f, _, b) in seen.items():
            rec = dict(base)
            rec.update(structure_file=f, block=bn)
            # profile pairing
            cands = [p for p in profiles if p["block"] == bn]
            if not cands and len(seen) == 1 and profiles:
                cands = sorted(profiles, key=lambda p: -p["n"])[:1]
            if not cands and profiles:
                # block names like 'I' vs 'I_profile': try prefix match
                cands = [p for p in profiles if p["block"].startswith(bn) or bn.startswith(p["block"])]
            rec["profile"] = cands[0] if cands else None
            try:
                ana = composition.analyse(block_to_cif_text(b), cod_id=pmc + ":" + bn)
                rec["analysis"] = ana
            except Exception as e:
                rec["analysis_error"] = repr(e)[:300]
            fo.write(json.dumps(rec, default=str) + "\n")
            fo.flush()
        print(pmc, len(profiles), "profiles", len(seen), "structures", flush=True)
    fo.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
