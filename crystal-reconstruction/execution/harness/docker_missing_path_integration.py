#!/usr/bin/env python3
"""Synthetic Docker missing-path validation; no provider call or scientific input."""
import argparse
import asyncio
import json
from pathlib import Path

from container_tools import DockerTools, command
from protocol import Deadline, Recorder, ToolCall


async def check(image, out):
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use a fresh synthetic validation output directory")
    recorder = Recorder(out)
    tools = DockerTools(image, recorder, 1, "512m", "recovery-synthetic-missing-path")
    result = None
    try:
        await tools.start()
        created = await tools.execute(ToolCall("synthetic-write", "bash", {
            "command": "mkdir -p /app/results; printf synthetic-final > /app/results/answer.txt", "timeout_s": 10}), Deadline(30))
        assert not created.error, created.text
        await tools.freeze("synthetic_validation")
        code, _, stderr = await command(["docker", "cp", tools.container + ":/app/notes", str(out / "missing-probe")], 10)
        assert code != 0
        inspect_code, inspect_stdout, _ = await command(["docker", "inspect", "--format", "{{.Id}}", tools.container], 10)
        assert inspect_code == 0 and inspect_stdout.decode().strip() == tools.container
        artifacts = await tools.collect(["/app/notes", "/app/results"], ["/app/results/answer.txt", "/app/notes"])
        assert artifacts["collection_errors"] == [], artifacts["collection_errors"]
        assert artifacts["submissions"][0]["present"] is True
        assert artifacts["submissions"][1]["present"] is False
        assert (out / "artifacts/results/answer.txt").read_text() == "synthetic-final"
        version_code, version, _ = await command(["docker", "version", "--format", "{{.Server.Version}}"], 10)
        assert version_code == 0
        result = {"author": "Qokedas", "mode": "synthetic_infrastructure_validation", "passed": True,
                  "docker_server_version": version.decode().strip(), "container_id": tools.container,
                  "missing_path_error": stderr.decode().strip(), "exact_container_verified": True,
                  "declared_present_file_collected": True, "declared_absent_path_recorded_missing": True,
                  "collection_errors": [], "provider_calls": 0, "scientific_inputs": 0}
    finally:
        if tools.container:
            await tools.freeze("synthetic_cleanup")
            await tools.remove()
    result["synthetic_container_removed"] = True
    recorder.json("result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    asyncio.run(check(args.image, args.out))
