# Authoring pipeline (never shipped in any container)

Order of operations, with inputs/outputs. Scratch and secrets live in a private working directory, `pxrd-work/`, outside this folder (never in the task dir; not part of this release).

1. `provenance/scan_hkl.py` — scan a COD `hkl` rsync mirror for pdCIF profiles → `pd_scan_all.jsonl` (348 files had `_pd_` tags).
2. `provenance/harvest_cod.py` — pair COD CIF + pdCIF hkl, run `pdcif.extract` and `composition.analyse` → `cod_records.jsonl`.
3. Europe PMC: search IUCr journals for powder papers with supplements (977), download `rest/<PMCID>/supplementaryFiles` zips (`pxrd-work/epmc/`), then `provenance/harvest_epmc.py` → `records.jsonl` (2 486 structure blocks; profiles paired to structures by block name).
4. Candidate table: dedupe, classify radiation, exclude metals/disorder/polymers/DFT blocks → `pxrd-work/harvest/candidates.json` (59 unique structures).
5. Cross-check with the 2014 DFT-D validation study (`pxrd-work/vdsn2014/`: SI CIFs + flagged list) by cell matching; exclude flagged; note validated.
6. Hand selection of 30 with notes and instrument overrides → `pxrd-work/build/selection.json`.
7. `provenance/build_instances.py` — writes `environment/data/instances/<id>/{pattern.xye,instrument.json,composition.json}`, `tests/truth/<id>.json`, `tests/manifest.json`, `tests/reference.sha256`, and the private key `pxrd-work/keys/manifest_SECRET.json` (ids = sha1(salt:source:block)[:7]).
8. QA: `evidence/qa_pairing.py` (simulated vs observed correlation, wavelength alternatives) and `evidence/reference_rwp.py` (deposited structure refined against the shipped pattern vs random-atoms null; runs in the tools image). Any failure → fix the pairing or drop the instance (done four times; see DEVIATIONS).
9. `evidence/recall_probe.py` — memorisation probe for both models (SMILES only, no tools); recalled cells → drop (one).
10. `evidence/battery.py` (+ `variants.py`) — fixture battery through the shipped grader → `battery_out/calibration_table.md`.
11. `evidence/fox_solve.py` + `run_batch.sh` — oracle-assisted and routine FOX runs on the calibration VM; `regrade_oracle.py` re-grades the saved best CIFs with the shipped grader.
12. Freeze (`execution/freeze_contract.py` on each trial VM), then trials (`execution/worker.py`).

`composition.py` details: bonds by covalent radii (+0.45 Å heavy–heavy; each H to its nearest heavy atom), molecules grouped by Weisfeiler–Lehman hash of the heavy-atom graph, bond orders by RDKit `DetermineBonds` with the moiety charge from `_chemical_formula_moiety` (fallback charges 0, ±1, ±2, ±3), stereo from 3D with N/P/S tags removed, chirality by CIP on the constitution, DoF = Σ(6 | 5 | 3 per fragment + rotatable bonds) × per-asymmetric-unit multiplicity.
