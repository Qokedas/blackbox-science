#!/usr/bin/env python3
"""Extract the observed powder profile from a COD/IUCr pdCIF (.hkl / .rtv) file.

Returns x (2theta, deg), y (observed intensity), sigma, and a provenance dict naming the tags used.
Priority: measured/raw total intensity > processed total > net (background subtracted, flagged).
2theta: measured scan > processed corrected > range min/inc.
Sigma: *_su columns > parenthesised su > 1/sqrt(_pd_proc_ls_weight) > sqrt(y) for count data.
"""
import math
import re
import sys

import gemmi
import numpy as np

Y_TAGS = ["_pd_meas_intensity_total", "_pd_meas_counts_total", "_pd_proc_intensity_total",
          "_pd_meas_intensity_net", "_pd_proc_intensity_net", "_pd_proc_intensity_bkg_calc"]
X_TAGS = ["_pd_meas_2theta_scan", "_pd_proc_2theta_corrected"]
NET_TAGS = {"_pd_meas_intensity_net", "_pd_proc_intensity_net"}

META_TAGS = ["_diffrn_radiation_wavelength", "_diffrn_radiation_type", "_diffrn_radiation_probe", "_diffrn_source",
             "_diffrn_radiation_monochromator", "_diffrn_ambient_temperature", "_diffrn_measurement_device_type",
             "_pd_instr_geometry", "_pd_meas_scan_method", "_pd_spec_mounting", "_pd_spec_mount_mode", "_pd_spec_shape",
             "_pd_spec_size_axial", "_pd_spec_size_equat", "_pd_spec_size_thick", "_pd_proc_wavelength",
             "_pd_meas_2theta_range_min", "_pd_meas_2theta_range_max", "_pd_meas_2theta_range_inc",
             "_pd_proc_2theta_range_min", "_pd_proc_2theta_range_max", "_pd_proc_2theta_range_inc",
             "_pd_meas_number_of_points", "_pd_proc_number_of_points", "_pd_instr_source_type", "_pd_char_colour",
             "_pd_prep_temperature", "_pd_prep_pressure", "_pd_char_particle_morphology", "_pd_spec_preparation",
             "_pd_meas_step_count_time", "_pd_instr_dist_spec/detc", "_pd_instr_dist_src/spec",
             "_pd_proc_info_excluded_regions", "_pd_proc_ls_prof_wR_factor", "_pd_proc_ls_prof_R_factor",
             "_pd_proc_ls_prof_wR_expected", "_refine_ls_R_I_factor", "_pd_meas_time_of_flight",
             "_cod_data_source_file", "_cod_data_source_block", "_diffrn_radiation_wavelength_wt"]


def parse_num(s):
    s = s.strip()
    if s in ("?", ".", ""):
        return math.nan, math.nan
    m = re.match(r"^([-+]?[\d.]+(?:[eE][-+]?\d+)?)(?:\((\d+)\))?$", s)
    if not m:
        try:
            return float(s), math.nan
        except ValueError:
            return math.nan, math.nan
    val = float(m.group(1))
    su = math.nan
    if m.group(2):
        # su in units of the last digit
        digits = m.group(1)
        if "." in digits:
            ndec = len(digits.split(".")[1].split("e")[0].split("E")[0])
        else:
            ndec = 0
        su = int(m.group(2)) * 10 ** (-ndec)
    return val, su


def column(loop_block, tag):
    col = loop_block.find_values(tag)
    if not col:
        return None, None
    vals = np.empty(len(col))
    sus = np.full(len(col), math.nan)
    for i, v in enumerate(col):
        vals[i], sus[i] = parse_num(v)
    return vals, sus


def block_meta(block):
    d = {}
    for t in META_TAGS:
        v = block.find_value(t)
        if v is not None:
            d[t] = gemmi.cif.as_string(v) if v.startswith(("'", '"', ";")) else v
    # multi-valued wavelength loop (e.g. Kalpha1/Kalpha2)
    wl = block.find_values("_diffrn_radiation_wavelength")
    if wl and len(wl) > 1:
        d["_diffrn_radiation_wavelength_list"] = [w for w in wl]
        wt = block.find_values("_diffrn_radiation_wavelength_wt")
        if wt:
            d["_diffrn_radiation_wavelength_wt_list"] = [w for w in wt]
    return d


def extract(text):
    doc = gemmi.cif.read_string(text)
    best = None
    for block in doc:
        ytag = None
        for t in Y_TAGS:
            if block.find_values(t):
                ytag = t
                break
        if ytag is None:
            continue
        y, ysu = column(block, ytag)
        n = len(y)
        xtag = None
        x = None
        for t in X_TAGS:
            xv, _ = column(block, t)
            if xv is not None and len(xv) == n:
                xtag, x = t, xv
                break
        if x is None:
            for pre in ("_pd_meas_2theta_range_", "_pd_proc_2theta_range_"):
                mn, mx, inc = (block.find_value(pre + k) for k in ("min", "max", "inc"))
                if mn and inc:
                    mn_v = parse_num(mn)[0]
                    inc_v = parse_num(inc)[0]
                    x = mn_v + inc_v * np.arange(n)
                    xtag = pre + "min/inc"
                    if mx:
                        mx_v = parse_num(mx)[0]
                        if abs(x[-1] - mx_v) > 2 * inc_v:
                            # inconsistent count; trust min/max
                            x = np.linspace(mn_v, mx_v, n)
                            xtag = pre + "min/max"
                    break
        if x is None:
            continue
        sigtag = None
        sig = None
        for t in (ytag + "_su",):
            sv, _ = column(block, t)
            if sv is not None and len(sv) == n and np.isfinite(sv).all():
                sig, sigtag = sv, t
                break
        if sig is None and np.isfinite(ysu).all() and np.nanmax(ysu) > 0:
            sig, sigtag = ysu, ytag + "(su)"
        if sig is None:
            w, _ = column(block, "_pd_proc_ls_weight")
            if w is not None and len(w) == n and np.all(np.isfinite(w)) and np.all(w > 0):
                sig, sigtag = 1.0 / np.sqrt(w), "1/sqrt(_pd_proc_ls_weight)"
        if sig is None:
            sig = np.sqrt(np.maximum(np.abs(y), 1.0))
            sigtag = "sqrt(max(|y|,1)) [assumed counting statistics]"
        calc_present = bool(block.find_values("_pd_calc_intensity_total") or block.find_values("_pd_calc_intensity_net"))
        bkg_present = bool(block.find_values("_pd_proc_intensity_bkg_calc"))
        # if only net intensity is present but a calculated background is too, restore total
        restored = False
        if ytag in NET_TAGS and bkg_present:
            b, _ = column(block, "_pd_proc_intensity_bkg_calc")
            if b is not None and len(b) == n and np.isfinite(b).all():
                y = y + b
                restored = True
        good = np.isfinite(x) & np.isfinite(y) & np.isfinite(sig)
        prov = dict(block=block.name, y_tag=ytag, x_tag=xtag, sigma_tag=sigtag, n_points=int(good.sum()),
                    n_raw=n, background_subtracted=(ytag in NET_TAGS and not restored), background_restored=restored,
                    calc_columns_present=calc_present, meta=block_meta(block))
        cand = (x[good], y[good], sig[good], prov)
        if best is None or prov["n_points"] > best[3]["n_points"]:
            best = cand
    return best


def write_xye(path, x, y, sig, header_lines=()):
    with open(path, "w") as f:
        for h in header_lines:
            f.write("# " + h + "\n")
        for a, b, c in zip(x, y, sig):
            f.write("%.5f %.6g %.6g\n" % (a, b, c))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        r = extract(open(p, errors="replace").read())
        if r is None:
            print(p, "NO PROFILE")
            continue
        x, y, s, prov = r
        print(p, prov["n_points"], prov["x_tag"], prov["y_tag"], prov["sigma_tag"], "range %.2f-%.2f" % (x[0], x[-1]),
              "bkgsub" if prov["background_subtracted"] else "", prov["meta"].get("_diffrn_radiation_wavelength"))
