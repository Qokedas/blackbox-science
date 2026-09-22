# Blackbox-Science, open example: blind crystal-structure solution from powder diffraction

This folder is the one Blackbox-Science environment we publish in full: the task as the models saw it, the grader, the reference data with provenance, the specification and its deviations, the grader validation battery, the execution harness, and the complete visible traces of the two frontier-model runs we scored. Everything needed to reproduce the grading or rerun the environment is here. Everything needed to check our claims about the runs is here.

## The task

For each of 30 organic solid forms (drugs, salts, cocrystals, solvates, a pigment, two long-chain alkanes) the solver receives one measured powder X-ray diffraction pattern, the instrument facts, and the composition of one formula unit as SMILES with stereochemistry. It must return the crystal structure: unit cell, space group and the positions of all non-hydrogen atoms, as one JSON and one CIF per instance. Nothing about the cell, the symmetry, Z or the coordinates is given. Solver-facing text: `instruction.md`. Tools in the container: `environment/TOOLS.md` (GSAS-II, ObjCryst++/FOX, GALLOP on CPU, RDKit, xtb, pymatgen and the rest). Budget: 4 CPUs, 16 GiB, no GPU, no network, eight hours for the whole panel.

Reference for each instance is the depositors' Rietveld-refined structure, taken byte-for-byte from open IUCr supplementary material or the Crystallography Open Database (`SOURCES.md`, `tests/truth/`). Reference quality checks, the memorisation probe that replaced one instance before the freeze, and the difficulty evidence are in `authoring/`.

## Scoring

Two binary units per instance, fixed weights, score = points / 90:

- **Unit L, 1 point.** Declared cell reduces to the reference's primitive lattice within 1 % in lengths and 1° in angles, and the space-group type is the reference's.
- **Unit S, 2 points.** The CIF's heavy-atom connectivity matches the supplied composition, and a symmetry-aware periodic match to the reference gives RMSD ≤ 0.35 Å and no atom more than 1.0 Å off. Mirror images of chiral molecules fail. Extra CIFs or multi-block CIFs zero the instance.

Grader: `tests/grade.py`, deterministic. Its validation battery over all 30 instances is in `authoring/evidence/battery_out/calibration_table.md`: the deposited structures score 1.0, 0.2 Å random jitter still passes S, 0.6 Å fails, mirror images of the 13 chiral Sohncke structures fail, one rotated ring fails, right cell with random coordinates earns L only.

## Results, one run per model, 2026-09-06

| model | score | full structures | cell and symmetry only | nothing submitted | wall clock |
|---|---:|---:|---:|---:|---|
| Fable 5.1 | 0.211 | 3 / 30 | 10 | 17 | 7.25 h, stopped itself |
| GPT-6 Astra | 0.478 | 10 / 30 | 13 | 7 | 8.00 h, deadline |

Twelve of the 30 structures were solved by at least one run, one by both. Eighteen have no correct structure from either. Per-instance ledger with the grader's own reason strings: `SCORES.md`. Full traces: `traces/`.

Every S pass is within 0.17 Å RMSD of the deposited structure. Every S fail that had a periodic mapping is at least 1.23 Å off at its worst atom. No instance sits on the tolerance edge.

## The clarithromycin case (`X238783d`)

Both runs indexed the 52-atom macrolide from a laboratory Cu Kα pattern and declared the correct P2₁2₁2₁ cell. Fable ran one Le Bail fit, submitted the cell, and never started a structure search on this instance. Astra ran two GALLOP searches and a restrained refinement and submitted a CIF that passed the identity check and failed the periodic match: the macrolide core is close (0.66 Å over the 14-membered ring after rigid fit) but the two sugar groups are in the wrong orientation, 40 of 52 heavy atoms more than 1 Å off, worst atom 6.7 Å, and the atoms-fixed profile residual is 20.2 % against 8.6 % for the deposited structure (`authoring/evidence/astra_submission_rwp.json`, `reference_rwp.json`). The molecular comparison is reproducible from `authoring/evidence/molecule_shape_compare.py`; its output for this case is `authoring/evidence/X238783d_astra_molecule_shape.json`. Both runs earned 1 of 3 points. Where to look in the traces: `traces/README.md`.

## Disclosures

- **Single run per model.** These are results for one agent-plus-tools-plus-compute configuration each, not a distribution.
- **Serialisation example leaks one cell.** The JSON example in `instruction.md` uses the real cell and space group of loperamide hydrochloride (`Xbfeeda9`). It was noticed after the trials. Scores are left as recorded; Astra solved that instance and Fable submitted nothing on it. A future version will use an unrelated example.
- **Public references.** The answer key is published literature. Both runs were offline, and neither reproduced deposited coordinates on any failed instance. This benchmark is not contamination-proof for future online systems.
- **No human baseline.** We did not measure a human under the same offline, eight-hour, four-core constraint and make no claim about one.
- **Astra's scratch space is trimmed** to fit repository limits; see `traces/README.md` for exactly what was removed.
- **Post-trial code cleanup.** After the trials, `tests/grade.py`, `task.toml`, `environment/Dockerfile` and `execution/freeze_contract.py` were rewritten for readability with identical behaviour. Their hashes therefore differ from the ones recorded in `traces/<model>/provenance.json` (the frozen contract at trial time). Tolerances, rules and outputs are unchanged; regrading both submission folders with the shipped grader reproduces the recorded scores and the identical per-instance L/S verdicts.
- **Grader change after publication (2026-09-22).** Unit L is now read from the CIF when one is submitted, and the JSON, when also present, must describe the same lattice and space-group type or the instance scores zero on both units. This closes a split bet (P2₁ CIF with a P2₁/c JSON, for instance). The JSON is graded alone only when no CIF exists. Regrading both recorded submissions with the new grader reproduces the recorded scores exactly; neither run had an inconsistent pair.
- **Asymmetric scoring after publication (2026-09-22).** A submitted unit that fails now costs 0.8 of its value (−0.8 for L, −1.6 for S); nothing submitted stays at 0; hedged or self-inconsistent submissions count as wrong on both units. The results table above is under the original zero-floor rule. Under the shipped grader the same two submission folders score Astra 0.095556 (8.6/90: 23 L passes, 7 L wrong, 10 S passes, 18 S wrong) and Fable 0.157778 (14.2/90: 13 L passes, 0 wrong, 3 S passes, 3 S wrong).
- **Harness hash inventory.** `execution/harness/package_manifest.json` lists one internal operations note (`HANDOFF.md`) that is not published, and its recorded hashes for `README.md` and `validation.json` in that folder no longer match because references to unrelated internal machines and paths were scrubbed from those two files. All harness code files match the inventory.
- **Internal paths.** Some authoring documents refer to a private working directory (`pxrd-work/`, the salted id key) and a private cloud bucket. Those are not part of this release. Nothing in this folder depends on them.

## Layout

```
instruction.md          what the solver was told
task.toml               resource and timeout contract
environment/            Dockerfile, TOOLS.md, data/instances/<id>/{pattern.xye,instrument.json,composition.json}
tests/                  grade.py, test.sh, truth/<id>.json (reference CIF + metadata), manifest, hashes
authoring/              SPEC.md, DEVIATIONS.md, KNOBS.md, provenance/ (harvest and build scripts), evidence/ (battery, oracle-assisted solves, reference fit checks, recall probe)
solution/               script that turns tests/truth into an oracle submission (grader self-check)
execution/              cloud runbook, harness (run_agent.py, deadline guard, container tools), freeze_contract.py
traces/                 the two trials: transcripts, tool logs, submissions, scratch work, verifier output
SCORES.md  SOURCES.md  NOTICE.md
```

## Reproducing the grade

```
python3 tests/grade.py --reference-root tests --submission-dir traces/astra/run/artifacts/results/submission --out /tmp/astra
python3 tests/grade.py --reference-root tests --submission-dir traces/fable/run/artifacts/results/submission --out /tmp/fable
```
Requires pymatgen, spglib, gemmi, RDKit and networkx (the solver image in `environment/Dockerfile` has them). Expected with the shipped (asymmetric) grader: `0.095556` and `0.157778`. The recorded rewards in `traces/<model>/verifier/reward.txt` (`0.477778`, `0.211111`) are under the original zero-floor rule; see Disclosures.
