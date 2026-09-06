#!/usr/bin/env python3
"""QA: does the shipped pattern belong to the reference structure at the stated wavelength?

For every instance: simulate the powder pattern of the reference structure (pymatgen XRDCalculator, heavy
atoms + H as deposited) at the stated wavelength and at alternative wavelengths, broaden to ~0.1 deg, and
correlate with the observed pattern after a rolling-minimum background removal, over the observed 2theta
range up to a common d-spacing limit. The stated wavelength should win clearly and correlate well (>0.5);
a low correlation flags a mismatched profile/structure pair, a wrong wavelength or a wrong zero shift.
Writes authoring/evidence/qa_pairing.json and prints a table.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests"))

ALT = {"CuKa1": 1.540598, "CuKa": 1.5418, "MoKa1": 0.709319, "CoKa1": 1.788965, "CrKa1": 2.28970, "AgKa1": 0.559421}


def rolling_min_background(y, w):
    n = len(y)
    b = np.empty(n)
    for i in range(n):
        lo, hi = max(0, i - w), min(n, i + w + 1)
        b[i] = y[lo:hi].min()
    # smooth the minimum envelope
    k = max(1, w // 2)
    kern = np.ones(2 * k + 1) / (2 * k + 1)
    return np.convolve(np.pad(b, k, mode="edge"), kern, mode="valid")


def simulate(struct, wl, x, fwhm):
    from pymatgen.analysis.diffraction.xrd import XRDCalculator
    calc = XRDCalculator(wavelength=wl)
    tt_max = min(x.max(), 179.0)
    pat = calc.get_pattern(struct, two_theta_range=(max(0.01, x.min()), tt_max), scaled=True)
    y = np.zeros_like(x)
    s = fwhm / 2.3548
    for tt, inten in zip(pat.x, pat.y):
        # Lorentz-polarisation is included by pymatgen; simple Gaussian broadening
        m = np.abs(x - tt) < 5 * fwhm
        y[m] += inten * np.exp(-0.5 * ((x[m] - tt) / s) ** 2)
    return y


def main(task, out_path):
    import grade as GR
    GR.load_deps()
    from pymatgen.io.cif import CifParser
    man = json.load(open(os.path.join(task, "tests", "manifest.json")))
    rows = []
    for iid in man["ids"]:
        truth = json.load(open(os.path.join(task, "tests", "truth", iid + ".json")))
        inst = json.load(open(os.path.join(task, "environment", "data", "instances", iid, "instrument.json")))
        xs, ys = [], []
        for line in open(os.path.join(task, "environment", "data", "instances", iid, "pattern.xye")):
            if line.startswith("#"):
                continue
            p = line.split()
            xs.append(float(p[0]))
            ys.append(float(p[1]))
        x = np.array(xs)
        y = np.array(ys)
        struct = CifParser.from_str(truth["reference_cif"], occupancy_tolerance=1.0).parse_structures(primitive=False)[0]
        wl0 = inst["radiation"]["wavelength_A"]
        # restrict to d >= 2.0 A equivalent for the stated wavelength (low-angle region carries the fingerprint)
        step = np.median(np.diff(x))
        w = int(max(3, 1.5 / step))
        bkg = rolling_min_background(y, w)
        yo = y - bkg
        yo = np.clip(yo, 0, None)
        res = {}
        for name, wl in dict(stated=wl0, **ALT).items():
            if wl is None:
                continue
            tt_lim = 2 * np.degrees(np.arcsin(min(0.999, wl / (2 * 2.0))))
            m = (x <= tt_lim) & (x > 0.2)
            if m.sum() < 50:
                continue
            fwhm = max(0.05, 3 * step)
            ysim = simulate(struct, wl, x[m], fwhm)
            if ysim.std() == 0 or yo[m].std() == 0:
                continue
            res[name] = float(np.corrcoef(ysim, yo[m])[0, 1])
        best = max(res, key=res.get) if res else None
        row = dict(id=iid, source=truth.get("candidate_name"), stated_wl=wl0, corr_stated=res.get("stated"), best=best, corr_best=res.get(best) if best else None,
                   n_points=len(x), x_min=float(x.min()), x_max=float(x.max()), ok=bool(res.get("stated") is not None and res["stated"] >= 0.5 and (best == "stated" or abs(res[best] - res["stated"]) < 0.05)))
        rows.append(row)
        print("%s corr(stated)=%.3f best=%s(%.3f) wl=%s n=%d range %.2f-%.2f %s  %s" % (iid, row["corr_stated"] or -9, best, row["corr_best"] or -9, wl0, len(x), x.min(), x.max(), "OK" if row["ok"] else "CHECK", (truth.get("candidate_name") or "")[:40].replace("\n", " ")), flush=True)
    json.dump(rows, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
