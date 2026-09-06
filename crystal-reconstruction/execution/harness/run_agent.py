#!/usr/bin/env python3
"""Qokedas common, offline-container, paired-provider scientific trial runner."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

from container_tools import DockerTools, artifact_relative, sha256
from protocol import Deadline, DeadlineExpired, InfrastructureError, ModelResourceLimit, Provider, Recorder, SYSTEM_PROMPT, TOOL_DEFINITIONS, ToolCall, ToolResult

AUTHOR = "Qokedas"
COMPACTION_PROMPT = """The harness is starting a fresh context to keep this same trial within its context budget. Write a concise factual handoff for yourself: the objective, work actually completed, relevant files and commands, remaining uncertainties, and the next steps you intended. Preserve concrete observations and submission paths. Do not invent progress or supply a retrospective score. Do not call tools in this handoff. This is context maintenance, not the final trial response. The original task instructions will be supplied unchanged with your handoff."""
COMPACTION_RETRY_PROMPT = """Your preceding context-maintenance handoff reached the response output limit before it finished. The complete conversation is still available. Write a new, complete, concise, self-contained handoff in this response; do not merely continue the cut-off text. Summarize the objective, completed work, relevant files, remaining uncertainties and intended next steps. Refer to saved files rather than repeating long transcripts. Preserve concrete observations and submission paths without inventing progress. Do not call tools. This is context maintenance, not the final trial response."""
CONTINUATION_PROMPT = "The previous response reached a technical output limit or provider pause. Continue the same task from the preserved state, within the remaining trial time."
SMOKE_INSTRUCTION = "This is a protocol smoke test, not a benchmark. Call bash exactly once with command 'printf qokedas-smoke' and timeout_s 1. After seeing its output, reply 'smoke complete' without another tool call."


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def image_pressure(history: list) -> tuple[int, int]:
    count, size = 0, 0

    def walk(value):
        nonlocal count, size
        if isinstance(value, dict):
            if value.get("type") in ("image", "input_image"):
                count += 1
                size += len(value.get("image_url", value.get("source", {}).get("data", "")))
            else:
                for item in value.values():
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(history)
    return count, size


async def complete_tools(provider: Provider, tools, history: list, calls: list[ToolCall], deadline: Deadline, recorder: Recorder):
    results = []
    for call in calls:
        if deadline.remaining() <= 0:
            raise DeadlineExpired()
        result = await tools.execute(call, deadline)
        result.text += f"\nRemaining trial time: {max(0, int(deadline.remaining()))} seconds."
        recorder.event("tool_result", call_id=call.id, name=call.name, text=result.text, error=result.error,
                       image_media_type=result.media_type, image_bytes_base64=len(result.image_base64 or ""))
        results.append((call, result))
    # Never issue an API call with a partially resolved batch, even during compaction.
    provider.append_results(history, results)


def require_replayable(turn):
    if turn.unusable_tool_arguments:
        if turn.finish_reason in ("max_tokens", "max_output_tokens"):
            raise ModelResourceLimit(turn.finish_reason)
        raise InfrastructureError("Completed response contained malformed native tool JSON without an output-limit finish reason")


async def compact(provider: Provider, tools, history: list, instruction: str, deadline: Deadline, recorder: Recorder) -> list:
    if provider.pending:
        raise InfrastructureError("Cannot compact with pending tool calls")
    history.append(provider.user(COMPACTION_PROMPT))
    for attempt in range(3):
        turn = await provider.call(history, deadline, purpose="compaction")
        if deadline.remaining() <= 0:
            raise DeadlineExpired()
        require_replayable(turn)
        provider.append_turn(history, turn)
        if turn.calls:
            await complete_tools(provider, tools, history, turn.calls, deadline, recorder)
            history.append(provider.user(COMPACTION_PROMPT))
            continue
        if not turn.refusal and turn.text.strip() and turn.finish_reason in ("max_tokens", "max_output_tokens"):
            recorder.event("compaction_handoff_truncated", attempt=attempt + 1, finish_reason=turn.finish_reason,
                           visible_characters=len(turn.text), history_items=len(history))
            if attempt < 2:
                history.append(provider.user(COMPACTION_RETRY_PROMPT))
                continue
            raise InfrastructureError("Compaction exhausted three handoff attempts at the output limit; full native history retained")
        if turn.refusal or not turn.text.strip() or turn.finish_reason not in ("completed", "end_turn", "stop_sequence"):
            raise InfrastructureError("Compaction did not produce a complete handoff; no history was silently dropped")
        recorder.event("context_compacted", handoff=turn.text, previous_messages=len(history))
        # Fresh conversation: no old thinking block or signed prefix is replayed out of context.
        return [provider.user(instruction), provider.user("Your own handoff from the preceding context of this same trial:\n\n" + turn.text)]
    raise InfrastructureError("Compaction repeatedly returned tools instead of a handoff")


async def agent_loop(provider: Provider, tools, instruction: str, deadline: Deadline, recorder: Recorder,
                     compact_tokens: int = 160000, max_turns: int = 10000):
    history = [provider.user(instruction)]
    for number in range(max_turns):
        turn = await provider.call(history, deadline)
        if deadline.remaining() <= 0:
            raise DeadlineExpired()
        require_replayable(turn)
        provider.append_turn(history, turn)
        if turn.calls:
            await complete_tools(provider, tools, history, turn.calls, deadline, recorder)
            images, image_bytes = image_pressure(history)
            if turn.input_tokens >= compact_tokens or images >= 24 or image_bytes >= 10 * 1024 * 1024:
                history = await compact(provider, tools, history, instruction, deadline, recorder)
            continue
        if turn.refusal:
            return {"termination": "model_refusal", "finish_reason": turn.finish_reason, "final_text": turn.text, "turns": number + 1}
        if turn.finish_reason in ("max_tokens", "max_output_tokens", "incomplete", "pause_turn"):
            history.append(provider.user(CONTINUATION_PROMPT))
            if turn.input_tokens >= compact_tokens:
                history = await compact(provider, tools, history, instruction, deadline, recorder)
            continue
        if turn.finish_reason not in ("completed", "end_turn", "stop_sequence"):
            raise InfrastructureError("Unknown provider finish reason: " + turn.finish_reason)
        return {"termination": "model_finished", "finish_reason": turn.finish_reason, "final_text": turn.text, "turns": number + 1}
    raise InfrastructureError("Infrastructure turn guard exceeded")


async def run_session(provider: Provider, tools, instruction: str, deadline: Deadline, recorder: Recorder,
                      compact_tokens: int = 160000, max_turns: int = 10000):
    """Freeze before collecting or cancelling work, at natural finish and absolute expiry."""
    async def watch():
        await asyncio.sleep(deadline.remaining())
        recorder.event("absolute_deadline_reached", deadline_epoch=deadline.epoch)
        await tools.freeze("deadline")
        return {"termination": "deadline", "finish_reason": None, "final_text": None}

    if hasattr(tools, "arm_deadline"):
        try:
            await tools.arm_deadline(deadline)
        except DeadlineExpired:
            await tools.freeze("deadline")
            return {"termination": "deadline", "finish_reason": None, "final_text": None}
        except BaseException:
            await tools.freeze("deadline_guard_setup_failure")
            raise
    agent = asyncio.create_task(agent_loop(provider, tools, instruction, deadline, recorder, compact_tokens, max_turns))
    watchdog = asyncio.create_task(watch())
    try:
        done, _ = await asyncio.wait({agent, watchdog}, return_when=asyncio.FIRST_COMPLETED)
        if watchdog in done:
            result = watchdog.result()  # A freeze failure is infrastructure failure.
            agent.cancel()
            await asyncio.gather(agent, return_exceptions=True)
            return result
        try:
            result = agent.result()
        except DeadlineExpired:
            result = {"termination": "deadline", "finish_reason": None, "final_text": None}
        except ModelResourceLimit as exc:
            result = {"termination": "resource_limit_incomplete_tool", "finish_reason": exc.finish_reason, "final_text": None}
        await tools.freeze(result["termination"])
        return result
    finally:
        # Also freeze on exceptions and external cancellation before ending the watchdog.
        try:
            await tools.freeze("session_exit")
        finally:
            for task in (agent, watchdog):
                if not task.done():
                    task.cancel()
            await asyncio.gather(agent, watchdog, return_exceptions=True)


class SmokeTools:
    """The only accepted smoke command is simulated. No host shell is executed."""
    def __init__(self):
        self.calls = []
        self.frozen = False

    async def execute(self, call: ToolCall, deadline: Deadline):
        if self.frozen:
            raise InfrastructureError("Smoke tool called after freeze")
        self.calls.append({"name": call.name, "arguments": call.arguments})
        if call.name == "bash" and call.arguments == {"command": "printf qokedas-smoke", "timeout_s": 1}:
            return ToolResult("Exit code: 0\nstdout:\nqokedas-smoke\nstderr:\n")
        return ToolResult("Smoke mode permits only its specified simulated bash command.", True)

    async def freeze(self, reason):
        self.frozen = True


async def main_async(args) -> int:
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory must be empty; never overwrite or resume a trial")
    out.mkdir(parents=True, exist_ok=True)
    os.chmod(out, 0o700)
    recorder = Recorder(out)
    key_name = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
    key = os.environ.get(key_name)
    if not key:
        recorder.json("trial_record.json", {"trial_id": args.trial_id, "execution_status": "infrastructure_failure", "error": "Missing host credential " + key_name})
        return 2
    provider = Provider(args.provider, args.model, key, recorder, max_output=args.smoke_max_output if args.smoke else 64000)
    tools = SmokeTools() if args.smoke else DockerTools(args.image, recorder, args.cpus, args.memory, args.trial_id)
    record = {"schema": "qokedas.host_trial.v1", "author": AUTHOR, "trial_id": args.trial_id,
              "mode": "provider_smoke" if args.smoke else "scientific_trial", "execution_status": "running",
              "provider": args.provider, "model": args.model, "reasoning_effort": "max",
              "max_output_tokens": provider.max_output, "budget_seconds": args.budget_seconds,
              "scientific_score": None, "grading_performed": False}
    errors = []
    exit_code = 0
    try:
        instruction_bytes = SMOKE_INSTRUCTION.encode() if args.smoke else Path(args.instruction).read_bytes()
        instruction = instruction_bytes.decode("utf-8")
        (out / "instruction.md").write_bytes(instruction_bytes)
        (out / "system_prompt.txt").write_text(SYSTEM_PROMPT, encoding="utf-8")
        record["instruction_sha256"] = hashlib.sha256(instruction_bytes).hexdigest()
        record["system_prompt_sha256"] = digest_text(SYSTEM_PROMPT)
        record["tool_definitions_sha256"] = digest_text(json.dumps(TOOL_DEFINITIONS, sort_keys=True))
        record["harness_source_sha256"] = {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
        if args.provenance:
            provenance_bytes = Path(args.provenance).read_bytes()
            json.loads(provenance_bytes)
            (out / "input_provenance.json").write_bytes(provenance_bytes)
            record["input_provenance_sha256"] = hashlib.sha256(provenance_bytes).hexdigest()
        if not args.smoke:
            await tools.start()
            record.update({"docker_image_id": tools.image_id, "container_id": tools.container, "cpus": args.cpus, "memory": args.memory, "network": "none"})
        deadline = Deadline(args.budget_seconds, args.deadline_epoch)
        record.update({"started_epoch": deadline.started_epoch, "deadline_epoch": deadline.epoch, "effective_budget_seconds": deadline.seconds,
                       "expected_submissions": [{"container_path": path, "artifact_path": str(artifact_relative(path))} for path in args.submission]})
        recorder.json("run_manifest.json", record)
        recorder.json("trial_record.json", record)
        recorder.event("trial_started", **record)
        result = await run_session(provider, tools, instruction, deadline, recorder, max_turns=6 if args.smoke else 10000)
        record.update(result)
        if args.smoke:
            record["smoke_tool_calls"] = tools.calls
            record["smoke_passed"] = len(tools.calls) == 1 and tools.calls[0] == {"name": "bash", "arguments": {"command": "printf qokedas-smoke", "timeout_s": 1}} and result["termination"] == "model_finished" and "smoke complete" in (result["final_text"] or "").lower()
            if not record["smoke_passed"]:
                raise InfrastructureError("Provider smoke did not complete the required tool roundtrip")
    except (Exception, asyncio.CancelledError) as exc:
        errors.append({"type": type(exc).__name__, "message": str(exc)})
        recorder.event("infrastructure_failure", **errors[-1])
        exit_code = 2
        record.setdefault("termination", "infrastructure_failure")
    finally:
        if not args.smoke and tools.container:
            try:
                await tools.freeze(record.get("termination", "infrastructure_failure"))
                record["freeze"] = tools.freeze_record
                roots = args.artifact or ["/app/results"]
                roots = roots + [p for p in args.submission if not any(p == r or p.startswith(r + "/") for r in roots)]
                record["artifacts"] = await tools.collect(roots, args.submission)
                if record["artifacts"]["collection_errors"]:
                    raise InfrastructureError("Artifact collection failed; see artifacts.collection_errors")
                record["submission_status"] = "present" if all(x["present"] for x in record["artifacts"]["submissions"]) else "missing_or_partial"
            except Exception as exc:
                errors.append({"type": type(exc).__name__, "message": str(exc)})
                exit_code = 2
            try:
                await tools.remove()
            except Exception as exc:
                errors.append({"type": type(exc).__name__, "message": str(exc)})
                exit_code = 2
        await provider.close()
        record["finished_epoch"] = time.time()
        record["execution_status"] = "infrastructure_failure" if errors else "completed"
        record["infrastructure_errors"] = errors
        recorder.json("usage.json", {"provider": args.provider, "model": args.model, "calls": provider.usage_records,
                                     "scope": "Usage returned by completed provider responses, including compaction. Failed or disconnected requests may incur unreported usage; no fabricated cost estimate."})
        recorder.json("trial_record.json", record)
        recorder.event("trial_closed", execution_status=record["execution_status"], termination=record.get("termination"), submission_status=record.get("submission_status"))
    print(json.dumps({"trial_id": args.trial_id, "execution_status": record["execution_status"], "termination": record.get("termination"), "submission_status": record.get("submission_status"), "record": str(out / "trial_record.json")}))
    return exit_code


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", choices=("openai", "anthropic"), required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--instruction")
    p.add_argument("--image")
    p.add_argument("--out", required=True)
    p.add_argument("--trial-id", required=True)
    p.add_argument("--budget-seconds", type=float, default=28800)
    p.add_argument("--deadline-epoch", type=float)
    p.add_argument("--cpus", type=float, default=4)
    p.add_argument("--memory", default="20g")
    p.add_argument("--submission", action="append", default=[])
    p.add_argument("--artifact", action="append", default=[])
    p.add_argument("--provenance", help="Frozen parent campaign input/scorer provenance JSON, copied verbatim into the run")
    p.add_argument("--smoke", action="store_true", help="Explicit non-benchmark provider test with a simulated, restricted tool; no Docker or grading")
    p.add_argument("--smoke-max-output", type=int, default=4096)
    return p


def main():
    p = parser()
    args = p.parse_args()
    if not args.smoke and (not args.instruction or not args.image or not args.submission):
        p.error("Scientific trials require --instruction, --image, and at least one --submission")
    if not 0 < args.budget_seconds <= 86400 or args.cpus <= 0:
        p.error("budget-seconds must be positive and no greater than 86400; cpus must be positive")
    for path in args.submission + args.artifact:
        try:
            artifact_relative(path)
        except ValueError as exc:
            p.error(str(exc))
    # SIGTERM follows the same freeze/collect cleanup path as Ctrl-C.
    def interrupt(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupt)
    try:
        return asyncio.run(main_async(args))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
