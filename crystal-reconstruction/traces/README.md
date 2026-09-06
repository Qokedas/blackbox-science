# Traces: the two paired trials of 2026-09-06

One run per model, same frozen package (see `provenance.json` in each folder, identical `package_files` hashes), same solver image `pxrd-solver:v2`, 4 CPUs, 16 GiB, no network, eight-hour budget, one VM each.

| folder | model | API calls | tool calls | context compactions | wall clock | score |
|---|---|---:|---:|---:|---|---:|
| `fable/` | Fable 5.1 (`claude-fable-5-1`) | 454 | 449 | 4 | 7.25 h, stopped itself | 0.211111 |
| `astra/` | GPT-6 Astra (`gpt-6-astra`) | 1 139 | 1 241 | 21 | 8.00 h, deadline | 0.477778 |

## What is in each folder

- `transcript.md`, `transcript.jsonl`: the model's visible text, every tool call with its full input, and every tool result, in order, with elapsed hours. Rebuilt verbatim from the provider response bodies and the harness event log by `build_transcript.py`. Hidden reasoning is not available from either provider (Anthropic thinking blocks came back null; OpenAI reasoning items are encrypted) and is marked as such.
- `trajectory_summary.md`: harness-generated digest, including the grader ledger and the compaction handoff notes the model wrote to itself.
- `run/trajectory.jsonl`: raw harness event log (API start/finish, tool start/result, compactions, container lifecycle).
- `run/tools/`: stdout and stderr of every tool call, numbered.
- `run/instruction.md`, `run/system_prompt.txt`, `run/run_manifest.json`, `run/deadline_guard.json`, `run/input_provenance.json`: exactly what the model was given and how the run was bounded.
- `run/artifacts/results/submission/`: the final deliverables as graded. This is the folder `tests/grade.py` scored.
- `run/artifacts/work/`: the model's own scratch space (scripts it wrote, logs, plots, intermediate CIFs, notes). Fable's is complete (8 MB). Astra's is trimmed of solver bulk to stay within repository limits: GSAS-II project files (`*.xml`), GALLOP `structure.json` dumps, `*.npz`/`*.npy` arrays and intermediate `*.xye` patterns were removed (about 950 MB); all scripts, logs, CIFs, plots and JSON summaries are kept.
- `verifier/score_breakdown.json`, `verifier/reward.txt`: the frozen grader's output at container freeze. `result.json`, `status.json`, `job.json`, `harness.log`: trial bookkeeping.
- `run/trial_record.json`, `run/usage.json`: per-call token usage and timing.

Not included: raw provider request and response bodies (1.3 GB; they contain the full conversation state at every call and are redundant with the transcript), and the two infrastructure-failed first attempts that never reached a model call (documented in `execution/README.md`).

## Where to look for clarithromycin (`X238783d`)

- Fable: `fable/run/artifacts/work/X238783d/` holds peak picking, three indexing logs and one Le Bail fit; the cell JSON is in `fable/run/artifacts/results/submission/X238783d.json`; no CIF was written. Search `fable/transcript.md` for `X238783d` to see the indexing, the Le Bail check, the cell submission at about 5.7 h and the "JSON only" decision in its handoff notes.
- Astra: `astra/run/artifacts/work/X238783d/` holds indexing, Pawley extraction, `gallop20.log` and `gallop25.log` (the two searches), refinement fits and `candidates.json`; the submitted structure is `astra/run/artifacts/results/submission/X238783d.cif`. The grader's verdict for it is in `astra/verifier/score_breakdown.json`.
