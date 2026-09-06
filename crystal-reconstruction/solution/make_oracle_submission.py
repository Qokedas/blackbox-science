#!/usr/bin/env python3
"""Reference solution: writes the deposited structures as a submission (one CIF + one JSON per instance).
It uses the private truth, so it can only run outside the solver container. Grading it must give 1.000000.
Usage: make_oracle_submission.py <task_dir> <out_dir>"""
import json
import os
import sys

task, out = sys.argv[1:3]
sys.path.insert(0, os.path.join(task, "tests"))
import grade as GR  # noqa
GR.load_deps()
os.makedirs(out, exist_ok=True)
man = json.load(open(os.path.join(task, "tests", "manifest.json")))
for iid in man["ids"]:
    t = json.load(open(os.path.join(task, "tests", "truth", iid + ".json")))
    open(os.path.join(out, iid + ".cif"), "w").write(t["reference_cif"])
    s = GR.structure_from_cif(t["reference_cif"])
    a, b, c, al, be, ga = s.lattice.parameters
    json.dump(dict(cell=dict(a=a, b=b, c=c, alpha=al, beta=be, gamma=ga), space_group=t["space_group_symbol"], space_group_number=t["space_group_number"]),
              open(os.path.join(out, iid + ".json"), "w"), indent=1)
print("wrote", len(man["ids"]), "instances to", out)
