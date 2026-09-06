#!/usr/bin/env python3
"""QA: Rietveld-style agreement of the deposited reference structure with the shipped pattern.

For each instance, load the reference CIF into ObjCryst (pyobjcryst), attach the shipped pattern at the
stated wavelength(s), fit background (Bayesian), zero shift, pseudo-Voigt profile and scale with the atoms
fixed, and report Rwp / chi2. A reference that belongs to the pattern gives a low Rwp (typically < 0.15 with
a crude profile model); a mismatched pair or wrong wavelength gives Rwp near the no-structure value.
Also fits a "P1 with random atoms" null for comparison. Runs inside the tools image on the VM.
Usage: reference_rwp.py <task_dir> <out_json> [ids...]   (env SUBMISSION_DIR=<dir> grades submitted CIFs instead of the reference)
"""
import json
import math
import os
import sys
import time

import numpy as np


def main(task, out_path, only=None):
    from pyobjcryst.crystal import Crystal
    from pyobjcryst.powderpattern import PowderPattern, ReflectionProfileType
    from pyobjcryst.radiation import RadiationType
    from pyobjcryst import loadCrystal
    import pyobjcryst.crystal as pc
    man = json.load(open(os.path.join(task, "tests", "manifest.json")))
    rows = []
    for iid in man["ids"]:
        if only and iid not in only:
            continue
        t0 = time.time()
        truth = json.load(open(os.path.join(task, "tests", "truth", iid + ".json")))
        inst = json.load(open(os.path.join(task, "environment", "data", "instances", iid, "instrument.json")))
        xye = os.path.join(task, "environment", "data", "instances", iid, "pattern.xye")
        cifp = "/tmp/ref_%s.cif" % iid
        subdir = os.environ.get("SUBMISSION_DIR")
        if subdir:
            sp = os.path.join(subdir, iid + ".cif")
            if not os.path.exists(sp):
                rows.append(dict(id=iid, error="no submitted CIF")); continue
            import shutil; shutil.copy(sp, cifp)
        else:
            open(cifp, "w").write(truth["reference_cif"])
        row = dict(id=iid, name=(truth.get("candidate_name") or "")[:50])
        try:
            cryst = pc.create_crystal_from_cif(cifp) if hasattr(pc, "create_crystal_from_cif") else loadCrystal(cifp)
            pp = PowderPattern()
            pp.ImportPowderPattern2ThetaObsSigma(xye, 1)
            wls = inst["radiation"].get("wavelengths_A") or [inst["radiation"]["wavelength_A"]]
            wts = inst["radiation"].get("wavelength_weights")
            pp.SetRadiationType(RadiationType.RAD_XRAY)
            if len(wls) == 2 and wts:
                pp.SetWavelength("CuA12") if abs(wls[0] - 1.5406) < 0.002 else pp.SetWavelength(wls[0])
                if abs(wls[0] - 0.7093) < 0.002:
                    pp.SetWavelength("MoA12")
            else:
                pp.SetWavelength(wls[0])
            # limit to d >= 1.5 A for speed and robustness
            pp.SetMaxSinThetaOvLambda(1.0 / (2 * 1.5))
            diff = pp.AddPowderPatternDiffraction(cryst)
            diff.SetReflectionProfilePar(ReflectionProfileType.PROFILE_PSEUDO_VOIGT, 0.00001)
            # fit background + zero + profile + cell (small) with fixed atoms; structure factors from the model (not Le Bail)
            pp.quick_fit_profile(plot=False, verbose=False, cell=False)
            diff.SetExtractionMode(False)
            pp.FitScaleFactorForRw()
            # a few LSQ cycles on scale/profile/zero with structure factors from the model
            from pyobjcryst.lsq import LSQ
            lsq = LSQ()
            lsq.SetRefinedObj(pp, 0, True, True)
            lsq.PrepareRefParList(True)
            lsqr = lsq.GetCompiledRefinedObj()
            lsqr.FixAllPar()
            for name in ("Zero", "W", "U", "V", "Eta0", "Scale"):
                try:
                    lsq.SetParIsFixed(name, False)
                except Exception:
                    pass
            for i in range(pp.GetNbPowderPatternComponent()):
                pass
            try:
                lsq.SafeRefine(nbCycle=8, useLevenbergMarquardt=True, silent=True)
            except Exception as e:
                row["lsq_error"] = repr(e)[:100]
            pp.FitScaleFactorForRw()
            row.update(rwp=float(pp.GetRw()), rp=float(pp.GetR()), chi2=float(pp.GetChi2()), n_refl=int(diff.GetNbRefl()), seconds=round(time.time() - t0, 1))
            # null: same cell, symmetry, profile and background, atoms at random positions (3 draws, best Rwp kept)
            rng = np.random.default_rng(0)
            nulls = []
            for k in range(3):
                for i in range(cryst.GetNbScatterer()):
                    sc = cryst.GetScatt(i)
                    sc.X, sc.Y, sc.Z = rng.random(3)
                pp.FitScaleFactorForRw()
                nulls.append(float(pp.GetRw()))
            row["rwp_null_random_atoms"] = min(nulls)
        except Exception as e:
            row["error"] = repr(e)[:200]
        rows.append(row)
        print(json.dumps(row), flush=True)
    json.dump(rows, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
