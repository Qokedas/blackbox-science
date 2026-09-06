# Qokedas shared trial harness

One objective, one fresh container, one final artifact set. This host runner gives Fable 5.1 and GPT-6 Astra the same offline `bash`, `write_file` and `view_image` tools, exact task instructions, output-token cap and wall-clock budget. It does not grade answers or choose checkpoints. The parent campaign freezes the dataset/scorer provenance and grades the collected final files afterward.

```bash
python run_agent.py \
  --provider openai --model gpt-6-astra \
  --instruction /input/instruction.md --image qokedas-task:trial \
  --trial-id unique-trial-id --out /output/trial \
  --budget-seconds 28800 --cpus 4 --memory 20g \
  --submission /app/results/answer.json \
  --artifact /app/results --provenance /output/ready.json
```

For Fable, use `--provider anthropic --model claude-fable-5-1`. Credentials come from host-only `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`; no credential is written into the run logs, passed to a Docker subprocess environment, mounted into the container or sent as task content. Install [requirements.txt](requirements.txt) on the host. Python 3.10+ is supported; Docker and the image's `/app`, `bash`, `timeout` and `python3` must be available. The caller supplies the benchmark's declared memory limit (16g for this task, per `task.toml`).

Both scientific-trial providers use reasoning effort `max` and a 64,000 output-token cap. Fable requests adaptive thinking. Astra uses the Responses API, `store=false`, encrypted reasoning and native function outputs. Every native output item is retained, including Astra reasoning and message phase, and Fable thinking/signatures. A completed provider response that exhausts the common output cap inside unusable tool JSON ends as resource_limit_incomplete_tool for either provider: existing final files are frozen and graded, and no tool input or assistant history is fabricated. An unfinished transport stream or malformed completed response without an output-limit reason remains infrastructure failure. No unsupported-model fallback, effort downgrade, refusal nudge, answer hint or missing-submission retry is applied. These formats follow the official [Astra model specification](https://developers.openai.com/api/docs/models/gpt-6-astra), [Responses reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning), [Responses function-calling guidance](https://developers.openai.com/api/docs/guides/function-calling), [Fable model specification](https://platform.claude.com/docs/en/models/fable-5-1/overview), [effort guidance](https://platform.claude.com/docs/en/build-with-claude/effort), [preserved thinking guidance](https://platform.claude.com/docs/en/build-with-claude/preserved-thinking) and [tool-result format](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls).

## Time and resource policy

The timer starts after Docker readiness and immediately before the first API request. Provisioning, input restoration and image building happen before the trial. The absolute 28,800-second deadline includes all API requests, retries, tools and context maintenance. `--deadline-epoch` can shorten this deadline. Before the first API call, an independent host process verifies the exact container ID and trial label and arms the absolute deadline. It has a scrubbed environment and survives main-runner termination. This process pauses the container even if the main event loop stalls; a second asynchronous watchdog cancels in-flight model/tool work. Both use the same deadline; natural completion and refusal also freeze it immediately. Pausing stops every process, including background jobs. A failed pause triggers a checked kill fallback. The requested and confirmed freeze timestamps expose any Docker scheduling delay. Failure to freeze is infrastructure failure, never a claimed valid timed result.

Artifact collection and container deletion occur after freezing and may extend host cleanup time. They give the model no additional working time. A supervisor should also impose a VM lifetime/cleanup deadline, because complete host failure can defeat any process running on that host. Killing only the main runner does not stop the independent guard. The campaign owns VM shutdown and deletion. The runner removes its Docker container.

Docker uses `--network none`, no host mounts, no Docker socket, no added capabilities, `no-new-privileges`, a 4,096 process limit and 2g shared memory. CPU and RAM are supplied by the campaign. `bash` has a requested 1–3,600 second timeout (600 by default), always capped by remaining trial time. Tool calls in one response execute in order. The container freeze is authoritative at the absolute deadline even if a command is still stopping.

`write_file` accepts up to 10 MiB of UTF-8 text per call. `view_image` reads up to 256 MiB, fits the image within 1,568 pixels, and returns PNG or JPEG at quality 90 when the PNG exceeds 300 KB. These common limits are disclosed in the tools. The source image is unchanged. Image decoding runs off the event loop so it cannot prevent the deadline watchdog from freezing the container. Bash returns up to 30,000 bytes per stream; each raw stdout/stderr log retains up to 32 MiB and records truncation explicitly. The runner does not silently claim that a truncated log is complete.

API calls have a one-hour per-request cap, bounded by the absolute deadline; connect and write timeouts also apply. Quiet streamed reasoning has no separate short read timeout; the one-hour/absolute deadline still bounds it. Up to four attempts are allowed for transient connection failures, rate limits and selected server statuses, with bounded backoff inside the trial budget. Authentication, unknown model and other 400 responses are infrastructure failures without retry. There is no claim that disconnected API attempts are free or that their usage is fully observed.

## Context maintenance

After complete tool-result batches, the runner requests the model's own factual handoff at 160,000 input tokens, 24 image results or 10 MiB of encoded images. The same tools, system prompt, effort and output cap remain attached to the summarization request. All tool calls must be resolved before another API request. If a handoff request itself returns tools, those calls receive results before asking again. If a clean native response reaches its output cap with nonempty, non-refusal text, the full native history is retained and a corrective request asks for a new complete, concise, self-contained handoff. The combined limit is three handoff attempts, all within the original deadline. A missing, refused, unknown-status or still-truncated handoff cannot replace context. Exhausted attempts are infrastructure failure; the runner does not fabricate a summary or silently discard context.

A successful handoff starts a fresh conversation containing the exact original instruction and the model's own summary. Old thinking/signatures are not transplanted into a changed prefix. This is a disclosed common resource policy rather than extra scientific assistance. Native output-limit or pause responses receive a technical continuation; final responses and refusals end the trial without checking whether the answer is good.

## Artifacts and status contract

The output directory must be empty. A run is never resumed or overwritten. `--submission` can be repeated for files or directories. `/app/results/answer.json` maps to `artifacts/results/answer.json`; paths outside `/app` map under `artifacts/container/`. Files get SHA-256 hashes; directory submissions get a sorted file manifest and a SHA-256 of its canonical JSON. Symlinks do not count as valid submissions. Only paths declared by `--submission` are selected, regardless of other checkpoint files in the collected artifact roots.

An absent artifact root is recorded as missing. For Docker's ambiguous `No such container:path` spelling, the runner first verifies the exact container ID still exists before treating the requested source path as absent. Missing required final output remains model nonsubmission; an unavailable container or other copy failure remains infrastructure failure.

| File | Purpose |
|---|---|
| `run_manifest.json` | Frozen pre-request trial ID, exact instruction/system/tool hashes, harness source hashes, immutable Docker image ID, resource limits and deadline. |
| `instruction.md`, `system_prompt.txt` | Exact model-visible instruction and common system prompt. |
| `input_provenance.json` | Parent's supplied provenance JSON, copied byte-for-byte and hash-bound. Its scientific truth and scorer binding are validated by the parent campaign. |
| `trajectory.jsonl` | Append-only API/tool/context/freeze events. |
| `provider/` | Native request bodies, every received SSE event and complete native responses. No headers or API credentials. |
| `tools/` | Bounded raw stdout/stderr; returned truncation and saved-log truncation are recorded separately. |
| `artifacts/` | Final frozen artifact roots. |
| `trial_record.json` | Final termination, infrastructure errors, freeze record, explicit selected artifact paths and hashes. |
| `deadline_guard.json` | Independent container-ID/label binding, guard outcome and observed freeze timestamps. |
| `usage.json` | Provider-native usage for completed responses, including handoffs. Disconnected/failed-request usage may be unobserved. |

Exit 0 means execution completed with `termination` equal to `model_finished`, `model_refusal`, `deadline` or `resource_limit_incomplete_tool`. A missing/partial submission is still a valid model outcome, recorded as `submission_status=missing_or_partial`; the parent grades it under the frozen task contract. Exit 2 means infrastructure failure (including unreadable inputs, provider errors, failed freeze/collection or failed cleanup). `termination` preserves the original model/deadline result even if later cleanup fails. This runner never emits a scientific score. Infrastructure failures must not be turned into model zeros.

## Verification

```bash
python -m unittest -v test_harness test_recovery
```

The offline suite exercises native reasoning/image protocols, tool adjacency, deadline cancellation, refusal, compaction, model identity, bounded retries, credential isolation, artifact paths, directory manifests and freeze failure. It calls no real provider and loads no benchmark data.

The recovery tests also compare native request traces with the original frozen runner for ordinary tool work and a successful first handoff under both providers. Those valid paths are unchanged; replacement trials nevertheless carry this corrected package's distinct harness hash. [docker_missing_path_integration.py](docker_missing_path_integration.py) validates the missing-path case using a synthetic container only.

An explicitly authorized provider smoke uses a simulated restricted bash command and no Docker or benchmark data:

```bash
python run_agent.py --smoke --provider openai --model gpt-6-astra \
  --trial-id protocol-smoke --out /tmp/empty-smoke-output --budget-seconds 180
```

Smoke mode keeps effort max but has a separate 4,096 output-token cap, configurable with `--smoke-max-output`; it cannot produce a scientific score. The parent has confirmed both real providers complete this roundtrip. [docker_integration.py](docker_integration.py) separately tests natural-finish and deadline freezing against a synthetic container, including a delayed background write and directory collection. It never calls a model.
