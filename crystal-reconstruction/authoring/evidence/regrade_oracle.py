#!/usr/bin/env python3
"""Re-grade the best CIFs saved by fox_solve runs with the shipped grader (identical code path to the trial).
Usage: regrade_oracle.py <task_dir> <batch_out_root> <out_json>"""
import json, os, sys, glob, shutil, tempfile
import gemmi
task, root, out = sys.argv[1:4]
sys.path.insert(0, os.path.join(task, "tests"))
import grade as GR
GR.load_deps()
rows = []
for d in sorted(glob.glob(os.path.join(root, "X*"))):
    iid = os.path.basename(d)
    if not os.path.exists(os.path.join(task, "tests", "truth", iid + ".json")):
        continue  # instance no longer in the panel
    truth = json.load(open(os.path.join(task, "tests", "truth", iid + ".json")))
    log = [json.loads(l) for l in open(os.path.join(d, "log.jsonl"))] if os.path.exists(os.path.join(d, "log.jsonl")) else []
    cellrow = next((r for r in log if r.get("stage") in ("cell", "spacegroup", "index")), None)
    a = b = c = al = be = ga = None
    if cellrow and cellrow.get("cell"):
        a, b, c, al, be, ga = cellrow["cell"]
    sg = next((r.get("sg") for r in log if r.get("sg")), None)
    best = None
    for cif in sorted(glob.glob(os.path.join(d, "best_*.cif"))):
        tmp = tempfile.mkdtemp()
        shutil.copy(cif, os.path.join(tmp, iid + ".cif"))
        # FOX writes dynamical-occupancy values; the calibration grades the arrangement, so occupancies are reset to 1
        doc = gemmi.cif.read(os.path.join(tmp, iid + ".cif"))
        for block in doc:
            occ = block.find_values("_atom_site_occupancy")
            for k in range(len(occ)):
                occ[k] = "1"
        doc.write_file(os.path.join(tmp, iid + ".cif"))
        if a is not None and sg:
            json.dump(dict(cell=dict(a=a, b=b, c=c, alpha=al, beta=be, gamma=ga), space_group=sg), open(os.path.join(tmp, iid + ".json"), "w"))
        try:
            g = GR.grade_instance(iid, truth, tmp)
            r = dict(cif=os.path.basename(cif), L=g["L"], S=g["S"], rmsd=g["S_detail"].get("rmsd"), dmax=g["S_detail"].get("dmax"), reason=g["S_detail"].get("reason"))
        except Exception as e:
            r = dict(cif=os.path.basename(cif), error=repr(e)[:100])
        shutil.rmtree(tmp)
        if best is None or (r.get("S") and not best.get("S")) or (r.get("rmsd") is not None and (best.get("rmsd") is None or r["rmsd"] < best["rmsd"])):
            best = r
    if best is None and a is not None and sg:
        # no CIF was produced (search never reached a checkpoint): grade the declared cell/space group alone
        tmp = tempfile.mkdtemp()
        json.dump(dict(cell=dict(a=a, b=b, c=c, alpha=al, beta=be, gamma=ga), space_group=sg), open(os.path.join(tmp, iid + ".json"), "w"))
        try:
            g = GR.grade_instance(iid, truth, tmp)
            best = dict(cif=None, L=g["L"], S=False, rmsd=None, dmax=None, reason="no CIF produced; " + str(g["L_detail"].get("reason") or ""))
        except Exception as e:
            best = dict(cif=None, error=repr(e)[:100])
        shutil.rmtree(tmp)
    if best is None:
        best = dict(cif=None, L=False, S=False, reason="no cell found (indexing returned nothing)" if not (a and sg) else "run produced nothing")
    endrow = next((r for r in log if r.get("stage") == "end"), None)
    mc = [r for r in log if r.get("stage") == "mc"]
    rows.append(dict(id=iid, dof=truth.get("dof"), zprime=truth.get("zprime"), radiation=truth.get("radiation_class"), best=best, minutes=endrow.get("minutes") if endrow else None,
                     trials_total=max((r.get("trials", 0) for r in mc), default=0), runs_done=len(set(r.get("run") for r in mc)), best_rw=min((r.get("rw", 9) for r in mc), default=None),
                     solved_seconds_inrun=(endrow or {}).get("solved_seconds")))
    print(iid, truth.get("dof"), best, "min", rows[-1]["minutes"], "best_rw", rows[-1]["best_rw"], flush=True)
json.dump(rows, open(out, "w"), indent=1)
print("S solved:", sum(1 for r in rows if r["best"] and r["best"].get("S")), "of", len(rows))
