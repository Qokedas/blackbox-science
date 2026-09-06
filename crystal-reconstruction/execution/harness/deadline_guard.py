#!/usr/bin/env python3
"""Independent Qokedas container deadline guard; no API/provider access."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path


def docker(*arguments):
    result = subprocess.run(["docker", *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[:3000])
    return result.stdout


def inspect_owned(container: str, trial: str):
    state = json.loads(docker("inspect", container))[0]
    if state.get("Config", {}).get("Labels", {}).get("qokedas.trial") != trial:
        raise RuntimeError("Deadline guard refuses a container without its exact trial label")
    return state["State"]


def write_record(path: Path, record: dict):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--deadline-epoch", type=float, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *unused: stop.set())
    signal.signal(signal.SIGINT, lambda *unused: stop.set())
    record = {"author": "Qokedas", "container_id": args.container, "trial_id": args.trial_id,
              "deadline_epoch": args.deadline_epoch, "pid": os.getpid()}
    target = Path(args.out)
    try:
        # Bind the exact immutable ID and campaign label before any model call starts.
        inspect_owned(args.container, args.trial_id)
        remaining = max(0, args.deadline_epoch - time.time())
        record["armed_epoch"] = time.time()
        print(json.dumps({"ready": True, "pid": os.getpid()}), flush=True)
        if stop.wait(remaining):
            record.update(status="cancelled_after_parent_freeze", finished_epoch=time.time())
            write_record(target, record)
            return 0
        record["freeze_requested_epoch"] = time.time()
        state = inspect_owned(args.container, args.trial_id)
        if not state.get("Running"):
            method = "already_stopped"
        elif state.get("Paused"):
            method = "already_paused"
        else:
            try:
                docker("pause", args.container)
                method = "pause"
            except Exception:
                # Another authorized watchdog may have paused it concurrently.
                state = inspect_owned(args.container, args.trial_id)
                if state.get("Paused") or not state.get("Running"):
                    method = "already_paused_or_stopped"
                else:
                    docker("kill", args.container)
                    method = "kill"
        record.update(status="frozen", method=method, freeze_confirmed_epoch=time.time())
        write_record(target, record)
        return 0
    except Exception as exc:
        record.update(status="infrastructure_failure", error=type(exc).__name__ + ": " + str(exc), finished_epoch=time.time())
        write_record(target, record)
        print(json.dumps({"ready": False, "error": record["error"]}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
