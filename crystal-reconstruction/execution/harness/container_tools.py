"""Bounded Docker tools; the agent receives no host mount, network or API key."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import os
import posixpath
import shlex
import sys
import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from protocol import Deadline, DeadlineExpired, InfrastructureError, Recorder, ToolCall, ToolResult

MAX_FILE = 10 * 1024 * 1024
MAX_IMAGE_FILE = 256 * 1024 * 1024
LOG_LIMIT = 32 * 1024 * 1024
RETURN_LIMIT = 30000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def artifact_relative(container_path: str) -> Path:
    normalized = posixpath.normpath(container_path)
    if not container_path.startswith("/") or normalized != container_path or container_path == "/":
        raise ValueError("Artifact paths must be normalized absolute paths other than /")
    if normalized == "/app":
        return Path("artifacts")
    if normalized.startswith("/app/"):
        return Path("artifacts") / normalized[5:]
    return Path("artifacts/container") / normalized.lstrip("/")


def clean_env() -> dict:
    # No API credential is even inherited by a Docker CLI child process.
    return {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))}


async def command(argv: list[str], timeout: float = 60, data: bytes | None = None) -> tuple[int, bytes, bytes]:
    process = await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE if data is not None else asyncio.subprocess.DEVNULL,
                                                  stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=clean_env())
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(data), timeout)
        return process.returncode, stdout, stderr
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise


class DockerTools:
    def __init__(self, image: str, recorder: Recorder, cpus: float, memory: str, trial_id: str):
        self.image, self.recorder, self.cpus, self.memory, self.trial_id = image, recorder, cpus, memory, trial_id
        self.container: str | None = None
        self.image_id: str | None = None
        self.frozen = False
        self.freeze_record = None
        self.freeze_lock = asyncio.Lock()
        self.tool_counter = 0
        self.guard = None
        (recorder.directory / "tools").mkdir(exist_ok=True)

    async def start(self):
        code, out, err = await command(["docker", "image", "inspect", self.image, "--format", "{{.Id}}"], 60)
        if code:
            raise InfrastructureError("Docker image unavailable: " + err.decode("utf-8", "replace"))
        self.image_id = out.decode().strip()
        code, out, err = await command(["docker", "run", "--detach", "--network", "none", "--cpus", str(self.cpus),
                                       "--memory", self.memory, "--pids-limit", "4096", "--shm-size", "2g",
                                       "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                                       "--label", "qokedas.trial=" + self.trial_id, "--entrypoint", "/bin/sh",
                                       self.image_id, "-c", "exec sleep infinity"], 120)
        if code:
            raise InfrastructureError("Docker startup failed: " + err.decode("utf-8", "replace"))
        self.container = out.decode().strip()
        # Check tools and working directory without exposing any solution/reference.
        code, out, err = await command(["docker", "exec", "-w", "/app", self.container, "/bin/sh", "-c", "command -v bash && command -v timeout && command -v python3"], 30)
        if code:
            raise InfrastructureError("Task image lacks /app, bash, timeout, or python3: " + err.decode("utf-8", "replace"))
        self.recorder.event("container_ready", container=self.container, image_id=self.image_id, network="none", cpus=self.cpus, memory=self.memory)

    async def arm_deadline(self, deadline: Deadline):
        if not self.container:
            raise InfrastructureError("Cannot arm deadline guard without a container")
        self.guard = await asyncio.create_subprocess_exec(
            sys.executable, str(Path(__file__).with_name("deadline_guard.py")),
            "--container", self.container, "--trial-id", self.trial_id,
            "--deadline-epoch", str(deadline.epoch), "--out", str(self.recorder.directory / "deadline_guard.json"),
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=clean_env(), start_new_session=True)
        line = await deadline.bound(self.guard.stdout.readline(), 20)
        try:
            status = json.loads(line)
        except ValueError as exc:
            raise InfrastructureError("Independent deadline guard did not confirm readiness") from exc
        if not status.get("ready"):
            raise InfrastructureError("Independent deadline guard failed: " + status.get("error", "unknown"))
        self.recorder.event("independent_deadline_guard_armed", pid=self.guard.pid, deadline_epoch=deadline.epoch)

    async def disarm_deadline(self):
        if self.guard:
            guard = self.guard
            if self.guard.returncode is None:
                try:
                    self.guard.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(self.guard.wait(), 20)
                except asyncio.TimeoutError:
                    self.guard.kill()
                    await self.guard.wait()
            path = self.recorder.directory / "deadline_guard.json"
            report = json.loads(path.read_text()) if path.exists() else None
            if self.freeze_record is not None:
                self.freeze_record["independent_guard"] = report
            self.guard = None
            if guard.returncode not in (0, None) or (report and report.get("status") == "infrastructure_failure"):
                raise InfrastructureError("Independent deadline guard failed; see deadline_guard.json")

    async def freeze(self, reason: str):
        async with self.freeze_lock:
            if self.frozen or not self.container:
                return
            requested = time.time()
            code, _, err = await command(["docker", "pause", self.container], 15)
            method = "pause"
            if code:
                # A stopped container is already immutable. Otherwise force-stop all tasks.
                code, out, inspect_err = await command(["docker", "inspect", "--format", "{{json .State}}", self.container], 15)
                if code:
                    raise InfrastructureError("Cannot inspect/freeze container: " + inspect_err.decode("utf-8", "replace"))
                state = json.loads(out)
                if state.get("Paused"):
                    method = "already_paused"
                elif state.get("Running"):
                    code, _, err = await command(["docker", "kill", self.container], 15)
                    if code:
                        raise InfrastructureError("Cannot freeze task container: " + err.decode("utf-8", "replace"))
                    method = "kill"
                else:
                    method = "already_stopped"
            self.frozen = True
            self.freeze_record = {"reason": reason, "requested_epoch": requested, "confirmed_epoch": time.time(), "method": method}
            self.recorder.event("container_frozen", **self.freeze_record)
            await self.disarm_deadline()

    async def remove(self):
        if self.container:
            code, _, err = await command(["docker", "rm", "--force", self.container], 30)
            if code:
                raise InfrastructureError("Container cleanup failed: " + err.decode("utf-8", "replace"))
            self.recorder.event("container_removed", container=self.container)
        await self.disarm_deadline()

    async def _logged_exec(self, argv: list[str], deadline: Deadline, timeout: float, stdin: bytes | None = None):
        self.tool_counter += 1
        stem = f"tools/{self.tool_counter:05d}"
        proc = await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
                                                   stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=clean_env())
        captures = {}

        async def drain(name, stream):
            total, head, tail = 0, bytearray(), bytearray()
            eof = False
            try:
                with (self.recorder.directory / (stem + "." + name)).open("wb") as log:
                    while True:
                        chunk = await stream.read(65536)
                        if not chunk:
                            eof = True
                            break
                        if total < LOG_LIMIT:
                            log.write(chunk[:LOG_LIMIT - total])
                        total += len(chunk)
                        if len(head) < RETURN_LIMIT // 2:
                            head.extend(chunk[:RETURN_LIMIT // 2 - len(head)])
                        tail.extend(chunk)
                        if len(tail) > RETURN_LIMIT // 2:
                            del tail[:-RETURN_LIMIT // 2]
            finally:
                raw = bytes(head) if total <= len(head) else (bytes(head) + (b"\n...[output truncated]...\n" if total > RETURN_LIMIT else b"") + bytes(tail[-max(0, min(total - len(head), RETURN_LIMIT // 2)):]))
                captures[name] = {"observed_bytes": total, "read_to_eof": eof, "log_truncated": total > LOG_LIMIT, "returned_truncated": total > RETURN_LIMIT, "path": stem + "." + name, "text": raw.decode("utf-8", "replace")}

        tasks = [asyncio.create_task(drain("stdout", proc.stdout)), asyncio.create_task(drain("stderr", proc.stderr))]

        async def execute():
            if stdin is not None:
                proc.stdin.write(stdin)
                try:
                    await proc.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                proc.stdin.close()
            await proc.wait()
            await asyncio.gather(*tasks)

        try:
            await deadline.bound(execute(), timeout)
        except BaseException:
            if proc.returncode is None:
                proc.kill()
            await proc.wait()
            await asyncio.gather(*tasks, return_exceptions=True)
            self.recorder.event("tool_process_aborted", streams={k: {a: b for a, b in v.items() if a != "text"} for k, v in captures.items()})
            raise
        self.recorder.event("tool_process", returncode=proc.returncode, streams={k: {a: b for a, b in v.items() if a != "text"} for k, v in captures.items()})
        return proc.returncode, captures["stdout"]["text"], captures["stderr"]["text"]

    async def execute(self, call: ToolCall, deadline: Deadline) -> ToolResult:
        if deadline.remaining() <= 0:
            raise DeadlineExpired()
        if self.frozen:
            raise InfrastructureError("Attempted tool execution after container freeze")
        args = call.arguments
        schema = {"bash": {"command", "timeout_s"}, "write_file": {"path", "content"}, "view_image": {"path"}}
        if call.name not in schema or not isinstance(args, dict) or set(args) != schema[call.name]:
            return ToolResult("Unknown tool or invalid argument schema.", True)
        self.recorder.event("tool_start", call_id=call.id, name=call.name, arguments=args, remaining_seconds=deadline.remaining())
        try:
            if call.name == "bash":
                requested = args["timeout_s"]
                if not isinstance(args["command"], str) or (requested is not None and (type(requested) is not int or not 1 <= requested <= 3600)):
                    return ToolResult("command must be text; timeout_s must be null or an integer from 1 to 3600.", True)
                seconds = min(requested or 600, deadline.remaining())
                argv = ["docker", "exec", "-w", "/app", self.container, "timeout", "--signal=TERM", "--kill-after=5s", str(seconds), "bash", "-lc", args["command"]]
                code, out, err = await self._logged_exec(argv, deadline, seconds + 6)
                await check_docker_error(code, err, self.container)
                return ToolResult(f"Exit code: {code}\nstdout:\n{out}\nstderr:\n{err}", code != 0)
            path = args["path"]
            if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
                return ToolResult("path must be an absolute container path.", True)
            if call.name == "write_file":
                if not isinstance(args["content"], str) or len(args["content"].encode("utf-8")) > MAX_FILE:
                    return ToolResult("content must be UTF-8 text no larger than 10 MiB.", True)
                script = "import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(sys.stdin.buffer.read())"
                code, out, err = await self._logged_exec(["docker", "exec", "-i", "-w", "/app", self.container, "python3", "-c", script, path], deadline, 120, args["content"].encode("utf-8"))
                await check_docker_error(code, err, self.container)
                return ToolResult(f"{'Written' if not code else 'Write failed'}: {path}\n{out}{err}", code != 0)
            script = f"import pathlib,sys;p=pathlib.Path(sys.argv[1]);f=p.open('rb');data=f.read({MAX_IMAGE_FILE + 1});assert len(data)<={MAX_IMAGE_FILE},'Image file exceeds 256 MiB';sys.stdout.buffer.write(data)"
            code, out, err = await deadline.bound(command(["docker", "exec", "-w", "/app", self.container, "python3", "-c", script, path], 120), 120)
            if code:
                await check_docker_error(code, err.decode("utf-8", "replace"), self.container)
                return ToolResult("Image read failed: " + err.decode("utf-8", "replace")[:RETURN_LIMIT], True)
            return await deadline.bound(asyncio.to_thread(render_image, out, path), 120)
        except asyncio.TimeoutError:
            return ToolResult("Tool exceeded its bounded timeout.", True)
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            return ToolResult(type(exc).__name__ + ": " + str(exc), True)

    async def collect(self, roots: list[str], submissions: list[str]) -> dict:
        if not self.frozen:
            raise InfrastructureError("Artifacts may only be collected from a frozen container")
        errors, copies = [], []
        # docker cp works on paused or stopped containers and does not follow symlinks by default.
        for root in sorted(set(roots), key=lambda p: (len(p), p)):
            if any(root == done or root.startswith(done + "/") for done in copies):
                continue
            relative = artifact_relative(root)
            destination = self.recorder.directory / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            code, _, err = await command(["docker", "cp", self.container + ":" + root, str(destination)], 300)
            if code:
                detail = err.decode("utf-8", "replace")
                missing = "Could not find the file" in detail or "No such file or directory" in detail
                if detail.strip() == "Error: No such container:path: " + self.container + ":" + root:
                    # Docker 20 uses this spelling for a missing source path AND for
                    # an unavailable container. Establish exact container identity.
                    inspect_code, inspect_out, _ = await command(["docker", "inspect", "--format", "{{.Id}}", self.container], 10)
                    missing = inspect_code == 0 and inspect_out.decode("utf-8", "replace").strip() == self.container
                if missing:
                    self.recorder.event("artifact_root_missing", container_path=root)
                else:
                    errors.append({"container_path": root, "error": detail})
            else:
                copies.append(root)
        inventory = []
        artifact_dir = self.recorder.directory / "artifacts"
        if artifact_dir.exists():
            for path in sorted(artifact_dir.rglob("*")):
                if path.is_symlink():
                    inventory.append({"path": str(path.relative_to(self.recorder.directory)), "type": "symlink", "valid_submission": False})
                elif path.is_file():
                    inventory.append({"path": str(path.relative_to(self.recorder.directory)), "type": "file", "size_bytes": path.stat().st_size, "sha256": sha256(path)})
        selected = []
        for source in submissions:
            relative = artifact_relative(source)
            target = self.recorder.directory / relative
            inside = [target]
            parent = target.parent
            while parent != self.recorder.directory:
                inside.append(parent)
                parent = parent.parent
            unsafe_link = any(p.is_symlink() for p in inside)
            if target.is_dir() and not unsafe_link:
                entries = [item for item in inventory if item["path"].startswith(str(relative) + "/")]
                safe = not any(item["type"] != "file" for item in entries)
                manifest = [{"path": item["path"][len(str(relative)) + 1:], "size_bytes": item["size_bytes"], "sha256": item["sha256"]} for item in entries if item["type"] == "file"]
                selected.append({"container_path": source, "artifact_path": str(relative), "present": safe, "type": "directory",
                                 "files": manifest, "size_bytes": sum(item["size_bytes"] for item in manifest),
                                 "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest() if safe else None})
            else:
                safe = target.is_file() and not unsafe_link
                selected.append({"container_path": source, "artifact_path": str(relative), "present": safe, "type": "file" if safe else None,
                                 "size_bytes": target.stat().st_size if safe else None, "sha256": sha256(target) if safe else None})
        return {"selection_policy": "final_files_at_container_freeze", "submissions": selected, "inventory": inventory, "collection_errors": errors}


async def check_docker_error(code: int, stderr: str, container: str):
    if code and any(marker in stderr for marker in ("Error response from daemon:", "Cannot connect to the Docker daemon", "Is the docker daemon running")):
        # Agent-generated stderr must not be sufficient to label a run infrastructure failure.
        inspect_code, out, _ = await command(["docker", "inspect", "--format", "{{json .State}}", container], 10)
        if inspect_code or not json.loads(out).get("Running"):
            raise InfrastructureError("Docker tool infrastructure failed: " + stderr[:3000])


def render_image(data: bytes, path: str) -> ToolResult:
    with Image.open(io.BytesIO(data)) as original:
        original.load()
        dimensions = original.size
        image = original.convert("RGB")
        image.thumbnail((1568, 1568))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        media = "image/png"
        if buffer.tell() > 300000:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90)
            media = "image/jpeg"
        return ToolResult(f"Image {path}: original {dimensions[0]}x{dimensions[1]}, displayed {image.width}x{image.height}.",
                          image_base64=base64.b64encode(buffer.getvalue()).decode("ascii"), media_type=media)
