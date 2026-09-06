# Knobs: every authoring rule that touches the truth or the score, with its value

All fixed before the first trial. None is tuned on a model result.

| Knob | Value | Where | Effect if changed |
|---|---|---|---|
| Unit L length tolerance | 1 % (fractional, per Niggli vector, via `Lattice.find_mapping`) | `tests/grade.py` `L_LTOL` | looser lets a 2 %-stretched cell pass (fixture `stretch2pct` currently fails) |
| Unit L angle tolerance | 1.0° | `L_ATOL` | idem for angles |
| Unit L volume equality | primitive volumes within 3 % | `lattice_match` | without it, sub-cells pass (fixture `subcell`) |
| Space-group type equivalence | enantiomorphic pairs merged; settings/origins free | `ENANTIOMORPH`, `sg_type` | — |
| Unit S RMSD | ≤ 0.35 Å over all non-H atoms in the primitive cell, reference lattice frame | `S_RMSD` | 0.2 Å jitter (RMSD 0.20) passes; 0.6 Å fails |
| Unit S max displacement | ≤ 1.0 Å | `S_DMAX` | ring flips (dmax 1.2–1.5 Å, RMSD 0.19–0.39 Å) fail only because of this |
| Matcher tolerances | ltol 0.06, stol 0.6 (normalised), angle 3°, no scaling, no supercell | `match_structures` | only affects whether a mapping is *found*; pass/fail uses the Å thresholds |
| Bond perception | covalent radii (RDKit) + slack, slack tried at 0.45/0.35/0.55/0.25/0.65 Å; polymeric components rejected | `SLACKS`, `molecule_graphs` | — |
| Identity fallback | geometric match within S tolerance establishes identity when perception fails | `grade_instance` | see DEVIATIONS 7 |
| Primitive reduction | 0.25 Å, loosened to 1.0 Å only until the submission's atom count reaches the reference's | `reduce_primitive` | noisy P1 descriptions of centred cells |
| Handedness | mirror accepted unless (Sohncke group AND chiral component); chirality from CIP on constitution, N/P/S tags stripped | truth `chiral`, `sohncke` | — |
| Hedging | extra `<id>*.cif` or multi-block CIF → instance 0 | `grade_instance` | — |
| Points | L 1, S 2, score = points / (3 N) | `main` | fixed by spec |
| Hydrogens | ignored everywhere (D, T too) | `HYDROGEN` | — |
| Pattern clipping | 2θ < 0.5° dropped (two ESRF scans started at −9°) | `build_instances.py` | data-only |
| Intensity column | measured total > processed total > net (background-subtracted, flagged in instrument.json) | `pdcif.py` | data-only |
| Sigma column | *_su > parenthesised su > 1/sqrt(weight) > sqrt(max(I,1)) flagged as assumed | `pdcif.py` | data-only |
| Kα1,2 without weights | weights 1 : 0.5 assumed, stated in `instrument.json.notes` | `selection.json` overrides | data-only |
| DoF definition | 6 per rigid fragment in the asym. unit (3 monatomic, 5 diatomic) + RDKit rotatable bonds, times per-asym multiplicity | `composition.py` | binning only, no score effect |
| DoF bins | `calib_lt15` (< 15), `mid_15_25`, `hard_dof25_or_Z2` (≥ 25 or Z′ ≥ 2) | `selection.json` | reporting only |
| Panel exclusions | metal-containing, disordered/partial occupancy, polymeric, flagged in the 2014 validation, mis-paired profile (correlation check), single-crystal-derived structures, famous-compound cocrystals with both components famous, model-recalled cells, duplicate compound | `harvest_*.py`, `selection.json` | who is in |
| Memorisation probe | SMILES-only prompt, no tools; instance dropped if Unit L passes on the answer | `recall_probe.py` | one instance replaced |
