#!/usr/bin/env python3
"""Summarise a harness run: API calls, tool calls by name, bash commands (from provider request
bodies), images viewed, compactions, wall time, when each submission file first appeared, and the final grader ledger.
Usage: analyze_trajectory.py <run_dir (contains trajectory.jsonl, provider/, artifacts/)> <verifier score_breakdown.json> <out.md>
"""
import collections
import glob
import json
import os
import re
import sys


def load_events(run):
    ev = []
    with open(os.path.join(run, "trajectory.jsonl"), encoding="utf-8") as f:
        for line in f:
            try:
                ev.append(json.loads(line))
            except Exception:
                pass
    return ev


def bash_commands(run):
    """Extract tool-use inputs from saved provider request bodies (both providers)."""
    cmds = []
    for p in sorted(glob.glob(os.path.join(run, "provider", "**", "*.json"), recursive=True)):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        stack = [d]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if x.get("type") in ("tool_use", "function_call") and (x.get("name") or "").startswith(("bash", "write_file", "view_image")):
                    inp = x.get("input") if "input" in x else x.get("arguments")
                    if isinstance(inp, str):
                        try:
                            inp = json.loads(inp)
                        except Exception:
                            inp = {"raw": inp}
                    cmds.append((x.get("name"), inp, x.get("id") or x.get("call_id")))
                stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
    seen = set()
    out = []
    for name, inp, cid in cmds:
        if cid in seen:
            continue
        seen.add(cid)
        out.append((name, inp))
    return out


def main(run, breakdown, out):
    ev = load_events(run)
    t0 = next((e["utc_epoch"] for e in ev if e["event"] == "trial_started"), ev[0]["utc_epoch"])
    t1 = next((e["utc_epoch"] for e in reversed(ev) if e["event"] == "trial_closed"), ev[-1]["utc_epoch"])
    api = [e for e in ev if e["event"] == "api_finish"]
    tools = [e for e in ev if e["event"] == "tool_result"]
    comp = [e for e in ev if e["event"] == "context_compacted"]
    errs = [e for e in ev if e["event"] in ("api_error", "infrastructure_failure")]
    by_name = collections.Counter(e["name"] for e in tools)
    images = sum(1 for e in tools if e.get("image_bytes_base64"))
    # submission timeline: first tool_result mentioning each submission file written
    first_seen = {}
    for e in tools:
        for m in re.finditer(r"/app/results/submission/(X[0-9a-f]{7})\.(cif|json)", e.get("text") or ""):
            key = m.group(1) + "." + m.group(2)
            first_seen.setdefault(key, round((e["utc_epoch"] - t0) / 3600, 2))
    cmds = bash_commands(run)
    usage = json.load(open(os.path.join(run, "usage.json"))) if os.path.exists(os.path.join(run, "usage.json")) else {}
    rec = json.load(open(os.path.join(run, "trial_record.json"))) if os.path.exists(os.path.join(run, "trial_record.json")) else {}
    bd = json.load(open(breakdown)) if os.path.exists(breakdown) else {}
    lines = []
    lines.append("# Trajectory summary: %s" % os.path.basename(os.path.dirname(run.rstrip("/"))))
    lines.append("")
    lines.append("- wall clock: %.2f h; termination: %s; execution: %s" % ((t1 - t0) / 3600, rec.get("termination"), rec.get("execution_status")))
    lines.append("- API responses: %d; tool results: %d (%s); images viewed: %d; context compactions: %d; API errors: %d" % (
        len(api), len(tools), ", ".join("%s %d" % kv for kv in by_name.most_common()), images, len(comp), len(errs)))
    if usage:
        lines.append("- usage: %s" % json.dumps({k: v for k, v in usage.items() if not isinstance(v, (dict, list))})[:400])
    lines.append("- tool inputs recovered from provider bodies: %d (bash %d, write_file %d, view_image %d)" % (
        len(cmds), sum(1 for n, _ in cmds if n == "bash"), sum(1 for n, _ in cmds if n == "write_file"), sum(1 for n, _ in cmds if n == "view_image")))
    lines.append("")
    lines.append("## Timeline of first submission writes (hours since start)")
    for k, v in sorted(first_seen.items(), key=lambda kv: kv[1]):
        lines.append("- %s at %.2f h" % (k, v))
    if not first_seen:
        lines.append("- (no submission path seen in tool results)")
    lines.append("")
    lines.append("## Compaction handoffs (first 300 characters each)")
    for e in comp:
        lines.append("- t=%.2f h: %s" % ((e["utc_epoch"] - t0) / 3600, (e.get("handoff") or "").replace("\n", " ")[:300]))
    lines.append("")
    if bd:
        lines.append("## Grader ledger")
        lines.append("score %s, points %s/%s, L %s, S %s, hedged %s" % (bd.get("score"), bd.get("points"), bd.get("max_points"), bd.get("L_passes"), bd.get("S_passes"), bd.get("hedged")))
        lines.append("")
        lines.append("| id | DoF | bin | L | S | L reason / cells | S reason | rmsd | dmax |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in bd.get("instances", []):
            L = r.get("L_detail", {})
            S = r.get("S_detail", {})
            lines.append("| %s | %s | %s | %d | %d | %s | %s | %s | %s |" % (
                r["id"], r.get("dof"), (r.get("dof_bin") or "")[:5], r["L"], r["S"],
                (L.get("reason") or ("cell_ok=%s sg_ok=%s sub=%s" % (L.get("cell_ok"), L.get("sg_ok"), L.get("submitted_niggli")))).replace("|", "/")[:90],
                (S.get("reason") or "")[:60], S.get("rmsd"), S.get("dmax")))
    lines.append("")
    lines.append("## Bash commands (first 120 chars each, in order)")
    for n, inp in cmds:
        if n == "bash" and isinstance(inp, dict):
            lines.append("- " + (inp.get("command") or "").replace("\n", " ")[:120])
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
