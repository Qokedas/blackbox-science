#!/usr/bin/env python3
"""Explicit synthetic Docker integration; never calls a provider or loads benchmark data."""
from __future__ import annotations

import argparse
import asyncio
import tempfile
import time
from pathlib import Path

from container_tools import DockerTools, command
from protocol import Deadline, Recorder, ToolCall, ToolResult, Turn
from run_agent import run_session


class SyntheticProvider:
    pending = []

    def __init__(self, command_text, block_main=False):
        self.command_text = command_text
        self.count = 0
        self.block_main = block_main

    def user(self, text):
        return {"role": "user", "content": text}

    async def call(self, history, deadline, purpose="trial"):
        self.count += 1
        if self.count == 1:
            return Turn({}, [ToolCall("synthetic", "bash", {"command": self.command_text, "timeout_s": 20})], "", "completed", {}, 1)
        if self.block_main:
            time.sleep(1.5)  # The independent process must enforce the deadline here.
        return Turn({}, [], "synthetic complete", "completed", {}, 1)

    def append_turn(self, history, turn):
        self.pending = [c.id for c in turn.calls]

    def append_results(self, history, results):
        assert [c.id for c, _ in results] == self.pending
        assert not any(r.error for _, r in results), [r.text for _, r in results]
        self.pending = []


async def check(image, out: Path, deadline_case: bool, block_main: bool = False):
    recorder = Recorder(out)
    tools = DockerTools(image, recorder, 1, "512m", "synthetic-harness-test")
    try:
        await tools.start()
        command_text = "mkdir -p /app/results/assignments; printf final > /app/results/final.txt; printf assignment > /app/results/assignments/a.txt; (sleep 2; printf late > /app/results/final.txt) >/dev/null 2>&1 </dev/null &"
        if deadline_case and not block_main:
            command_text += " sleep 10"
        budget = 0.8 if deadline_case else 10
        result = await run_session(SyntheticProvider(command_text, block_main), tools, "Synthetic infrastructure test only.", Deadline(budget), recorder)
        assert result["termination"] == ("deadline" if deadline_case else "model_finished"), result
        assert tools.frozen
        if block_main:
            guard = tools.freeze_record["independent_guard"]
            assert guard["status"] == "frozen", guard
            assert guard["freeze_confirmed_epoch"] < tools.freeze_record["requested_epoch"], "Independent guard did not freeze before main resumed"
        # Wait past the background write time: paused tasks must not modify the final file.
        await asyncio.sleep(2.3)
        artifacts = await tools.collect(["/app/results"], ["/app/results/final.txt", "/app/results/assignments"])
        assert not artifacts["collection_errors"], artifacts
        assert all(item["present"] for item in artifacts["submissions"]), artifacts
        assert (out / "artifacts/results/final.txt").read_text() == "final", "Late background mutation escaped freeze"
        recorder.json("integration_result.json", {"passed": True, "termination": result["termination"], "freeze": tools.freeze_record, "artifacts": artifacts})
    finally:
        if tools.container:
            await tools.freeze("test_cleanup")
            await tools.remove()


async def main(args):
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Synthetic integration output must be empty")
    out.mkdir(parents=True, exist_ok=True)
    await check(args.image, out / "natural", False)
    await check(args.image, out / "deadline", True)
    await check(args.image, out / "blocked-event-loop", True, True)
    print("PASS: natural completion, deadline and independent guard during blocked event loop freeze all background writes; final files and directory manifests collected.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", required=True, help="An explicitly prepared synthetic image with /app, bash, timeout, python3")
    p.add_argument("--out", required=True)
    asyncio.run(main(p.parse_args()))
