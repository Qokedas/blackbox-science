#!/usr/bin/env python3
"""Memorisation probe: ask each model, with no tools and no pattern, for the unit cell and space group of the
crystal given only the shipped composition.json (SMILES, counts, charges). An instance whose cell is recalled
(Unit L passes on the answer) is flagged in the README and, per the spec, dropped or flagged before the trial.

Usage: recall_probe.py --task <task_dir> --provider anthropic|openai --model <id> --out <json>
Requires ANTHROPIC_API_KEY / OPENAI_API_KEY in the environment (host side only).
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests"))

PROMPT = """You are a crystallographer with an excellent memory of the literature. A crystalline solid form has the composition below (one formula unit; SMILES with counts and charges). Without any diffraction data, state from memory the published crystal structure of this solid form if you know it: unit cell (a, b, c in angstrom; alpha, beta, gamma in degrees) and space group (Hermann-Mauguin symbol). If you do not know it, give your best estimate anyway and say so. Answer ONLY with JSON of the form
{{"known": true|false, "cell": {{"a":..,"b":..,"c":..,"alpha":..,"beta":..,"gamma":..}}, "space_group": "...", "compound_guess": "..."}}

composition.json:
{comp}
"""


def ask_anthropic(model, text):
    import anthropic
    client = anthropic.Anthropic()
    r = client.messages.create(model=model, max_tokens=800, messages=[{"role": "user", "content": text}])
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


def ask_openai(model, text):
    from openai import OpenAI
    client = OpenAI()
    r = client.responses.create(model=model, input=text, max_output_tokens=1200)
    return r.output_text


def parse_json(s):
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--provider", choices=("anthropic", "openai"), required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--ids", nargs="*", default=None)
    args = ap.parse_args()
    import grade as GR
    GR.load_deps()
    man = json.load(open(os.path.join(args.task, "tests", "manifest.json")))
    rows = []
    for iid in man["ids"]:
        if args.ids and iid not in args.ids:
            continue
        comp = open(os.path.join(args.task, "environment", "data", "instances", iid, "composition.json")).read()
        truth = json.load(open(os.path.join(args.task, "tests", "truth", iid + ".json")))
        ref_struct = GR.structure_from_cif(truth["reference_cif"])
        ref_prim = GR.primitive_lattice(ref_struct.lattice, truth.get("centring", "P"))
        for rep in range(args.repeats):
            text = PROMPT.format(comp=comp)
            for attempt in range(4):
                try:
                    ans = ask_anthropic(args.model, text) if args.provider == "anthropic" else ask_openai(args.model, text)
                    break
                except Exception as e:
                    ans = "ERROR " + repr(e)[:200]
                    time.sleep(10 * (attempt + 1))
            js = parse_json(ans)
            L = False
            detail = {}
            if js and isinstance(js.get("cell"), dict):
                try:
                    c = js["cell"]
                    lat = GR.Lattice.from_parameters(float(c["a"]), float(c["b"]), float(c["c"]), float(c["alpha"]), float(c["beta"]), float(c["gamma"]))
                    sg, cen, err = GR.parse_space_group(js.get("space_group"), None)
                    if sg is not None:
                        sub_prim = GR.primitive_lattice(lat, cen or "P")
                        cell_ok = GR.lattice_match(ref_prim, sub_prim)
                        sg_ok = GR.sg_type(sg) == GR.sg_type(truth["space_group_number"])
                        L = bool(cell_ok and sg_ok)
                        detail = dict(cell_ok=cell_ok, sg_ok=sg_ok, submitted=GR.lat_params(sub_prim), reference=GR.lat_params(ref_prim))
                except Exception as e:
                    detail = dict(error=repr(e)[:120])
            rows.append(dict(id=iid, repeat=rep, claimed_known=js.get("known") if js else None, compound_guess=(js or {}).get("compound_guess"),
                             L_recalled=L, detail=detail, raw=ans[:600]))
            print(iid, rep, "known=%s" % (js.get("known") if js else None), "L=%s" % L, (js or {}).get("compound_guess"), flush=True)
    json.dump(dict(provider=args.provider, model=args.model, rows=rows, n_recalled=sum(r["L_recalled"] for r in rows)), open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
