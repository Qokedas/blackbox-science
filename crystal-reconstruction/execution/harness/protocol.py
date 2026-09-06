"""Qokedas provider protocol. No benchmark-specific policy or credentials on disk."""
from __future__ import annotations

import asyncio
import copy
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

SYSTEM_PROMPT = """You are working on a Qokedas scientific benchmark trial. Complete the objective in the supplied instructions and write the requested final deliverables to the specified paths. The task container has no network access. You have the same bash, write_file, and view_image tools throughout the trial. Use the supplied data and resources. You have a fixed wall-clock budget; API calls and tools count toward it. Save useful work and final deliverables as you proceed, since the container is frozen when the trial ends. Only final submitted artifacts are evaluated. Be accurate, and do not invent evidence or results. Your final response ends the trial; any background processes are frozen at that point."""

TOOL_DEFINITIONS = [
    {"name": "bash", "description": "Run a bash command in the offline task container, starting in /app. The timeout includes process execution and is capped by the remaining trial time. Output may be truncated, explicitly marked. Processes may not continue after the trial ends.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "timeout_s": {"type": ["integer", "null"], "description": "1–3600 seconds, or null for 600 seconds."}}, "required": ["command", "timeout_s"], "additionalProperties": False}},
    {"name": "write_file", "description": "Write UTF-8 text to an absolute path inside the task container. Creates parent directories. Maximum 10 MiB per call.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}},
    {"name": "view_image", "description": "View an image at an absolute path inside the task container, up to 256 MiB on disk. The common renderer fits it within 1568 pixels and returns PNG or JPEG. Original files are unchanged.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
]


class DeadlineExpired(Exception):
    pass


class InfrastructureError(Exception):
    pass


class ModelResourceLimit(Exception):
    def __init__(self, finish_reason):
        super().__init__("Completed provider response exhausted its output cap inside a tool payload")
        self.finish_reason = finish_reason


class ProviderError(InfrastructureError):
    def __init__(self, message: str, status: int = 0, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class Deadline:
    def __init__(self, seconds: float, deadline_epoch: float | None = None):
        self.started_epoch = time.time()
        self.started_mono = time.monotonic()
        self.seconds = max(0.0, min(seconds, deadline_epoch - self.started_epoch)) if deadline_epoch is not None else max(0.0, seconds)
        self.epoch = self.started_epoch + self.seconds
        self.end = self.started_mono + self.seconds

    def remaining(self) -> float:
        return max(0.0, self.end - time.monotonic())

    async def bound(self, awaitable, cap: float | None = None):
        remaining = self.remaining()
        if remaining <= 0:
            if hasattr(awaitable, "close"):
                awaitable.close()
            raise DeadlineExpired("Absolute trial deadline reached")
        timeout = remaining if cap is None else min(remaining, cap)
        try:
            return await asyncio.wait_for(awaitable, timeout)
        except asyncio.TimeoutError as exc:
            if self.remaining() <= 0.01:
                raise DeadlineExpired("Absolute trial deadline reached") from exc
            raise


class Recorder:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "provider").mkdir(exist_ok=True)
        self.counter = 0

    def event(self, kind: str, **fields):
        record = {"utc_epoch": time.time(), "event": kind, **fields}
        with (self.directory / "trajectory.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def json(self, relative: str, value):
        target = self.directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(target)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Any


@dataclass
class ToolResult:
    text: str
    error: bool = False
    image_base64: str | None = None
    media_type: str | None = None


@dataclass
class Turn:
    raw: dict
    calls: list[ToolCall]
    text: str
    finish_reason: str
    usage: dict
    input_tokens: int
    refusal: bool = False
    unusable_tool_arguments: bool = False


class Provider:
    """Stateless native histories, never previous_response_id or server tools."""
    def __init__(self, provider: str, model: str, key: str, recorder: Recorder,
                 client: httpx.AsyncClient | None = None, max_output: int = 64000,
                 request_timeout: float = 3600, max_attempts: int = 4):
        if provider not in ("openai", "anthropic"):
            raise ValueError("Unknown provider")
        self.provider, self.model, self.key, self.recorder = provider, model, key, recorder
        # Quiet high-effort reasoning is allowed; the entire request is still bounded
        # by request_timeout and the absolute trial deadline.
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(connect=30, read=None, write=120, pool=30))
        self.owns_client = client is None
        self.max_output = max_output
        self.request_timeout = request_timeout
        self.max_attempts = max_attempts
        self.usage_records = []
        self.pending: list[str] = []

    async def close(self):
        if self.owns_client:
            await self.client.aclose()

    def user(self, text: str):
        return {"role": "user", "content": text}

    def payload(self, history: list) -> dict:
        if self.provider == "openai":
            return {"model": self.model, "instructions": SYSTEM_PROMPT, "input": history,
                    "tools": [{"type": "function", "name": t["name"], "description": t["description"], "parameters": t["input_schema"], "strict": True} for t in TOOL_DEFINITIONS],
                    "reasoning": {"effort": "max"}, "max_output_tokens": self.max_output,
                    "store": False, "include": ["reasoning.encrypted_content"], "stream": True}
        return {"model": self.model, "system": SYSTEM_PROMPT, "messages": history,
                "tools": [{**t, "strict": True} for t in TOOL_DEFINITIONS],
                "max_tokens": self.max_output, "thinking": {"type": "adaptive"},
                "output_config": {"effort": "max"}, "stream": True}

    async def _stream(self, payload: dict, stem: str) -> dict:
        if self.provider == "openai":
            url = "https://api.openai.com/v1/responses"
            headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        else:
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": self.key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        raw = None
        partial_json: dict[int, str] = {}
        complete = False
        event_path = self.recorder.directory / (stem + ".events.jsonl")
        async with self.client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", "replace")
                self.recorder.json(stem + ".error.json", {"status": response.status_code, "body": body})
                raise ProviderError(f"HTTP {response.status_code}: {body[:3000]}", response.status_code,
                                    response.status_code in (408, 409, 429, 500, 502, 503, 504, 529))
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    event = json.loads(data)
                except ValueError as exc:
                    raise ProviderError("Malformed provider SSE JSON") from exc
                with event_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                kind = event.get("type")
                if kind in ("error", "response.failed"):
                    error = event.get("error", event.get("response", {}).get("error", {}))
                    code = error.get("type", error.get("code", ""))
                    raise ProviderError(json.dumps(error), retryable=code in ("overloaded_error", "api_error", "server_error", "rate_limit_error"))
                if self.provider == "openai":
                    if kind in ("response.completed", "response.incomplete"):
                        raw = event["response"]
                        complete = True
                        break
                elif kind == "message_start":
                    raw = copy.deepcopy(event["message"])
                elif kind == "content_block_start":
                    if raw is None:
                        raise ProviderError("Content before message_start")
                    index = event["index"]
                    while len(raw["content"]) <= index:
                        raw["content"].append({})
                    raw["content"][index] = copy.deepcopy(event["content_block"])
                elif kind == "content_block_delta":
                    index, delta = event["index"], event["delta"]
                    block = raw["content"][index]
                    field = {"text_delta": "text", "thinking_delta": "thinking", "signature_delta": "signature"}.get(delta["type"])
                    if field:
                        block[field] = block.get(field, "") + delta[field]
                    elif delta["type"] == "input_json_delta":
                        partial_json[index] = partial_json.get(index, "") + delta["partial_json"]
                    else:
                        raise ProviderError("Unrecognized content delta: " + delta["type"])
                elif kind == "content_block_stop":
                    index = event["index"]
                    if index in partial_json:
                        try:
                            raw["content"][index]["input"] = json.loads(partial_json[index])
                        except ValueError:
                            # Retain the exact partial JSON separately; do not manufacture
                            # a completed tool-input object or decide before the terminal event.
                            raw["content"][index].pop("input", None)
                            raw.setdefault("_harness_incomplete_tool_json", {})[str(index)] = partial_json[index]
                elif kind == "message_delta":
                    raw.update(copy.deepcopy(event.get("delta", {})))
                    raw.setdefault("usage", {}).update(event.get("usage", {}))
                elif kind == "message_stop":
                    complete = True
                    break
        if not complete or raw is None:
            raise ProviderError("Provider stream ended without a complete terminal event", retryable=True)
        self.recorder.json(stem + ".response.json", raw)
        return raw

    async def call(self, history: list, deadline: Deadline, purpose: str = "trial") -> Turn:
        if self.pending:
            raise InfrastructureError("Unresolved tool calls cannot be sent to the provider")
        payload = self.payload(history)
        self.recorder.counter += 1
        call_number = self.recorder.counter
        # Native request payloads contain trial data and encrypted reasoning, never headers/keys.
        self.recorder.json(f"provider/{call_number:05d}.request.json", payload)
        for attempt in range(1, self.max_attempts + 1):
            stem = f"provider/{call_number:05d}.{attempt}"
            self.recorder.event("api_start", call=call_number, attempt=attempt, purpose=purpose, remaining_seconds=deadline.remaining())
            try:
                raw = await deadline.bound(self._stream(payload, stem), self.request_timeout)
                break
            except (httpx.TransportError, asyncio.TimeoutError) as exc:
                error = ProviderError(type(exc).__name__ + ": " + str(exc), retryable=True)
            except ProviderError as exc:
                error = exc
            self.recorder.event("api_error", call=call_number, attempt=attempt, error=str(error), retryable=error.retryable)
            if not error.retryable or attempt == self.max_attempts:
                raise error
            await deadline.bound(asyncio.sleep(min(60, 2 ** attempt)))
        turn = self.normalize(raw)
        self.usage_records.append({"call": call_number, "purpose": purpose, "usage": turn.usage})
        self.recorder.event("api_finish", call=call_number, finish_reason=turn.finish_reason, calls=[c.name for c in turn.calls], usage=turn.usage)
        return turn

    def normalize(self, raw: dict) -> Turn:
        if self.provider == "openai":
            calls, unusable = [], False
            for item in raw.get("output", []):
                if item.get("type") != "function_call":
                    continue
                arguments = item.get("arguments")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except ValueError:
                        unusable = True
                else:
                    unusable = True
                calls.append(ToolCall(item["call_id"], item["name"], arguments))
            content = [c for x in raw.get("output", []) if x.get("type") == "message" for c in x.get("content", [])]
            text = "\n".join(c.get("text", "") for c in content if c.get("type") == "output_text")
            refusal = any(c.get("type") == "refusal" for c in content) or (raw.get("incomplete_details") or {}).get("reason") == "content_filter"
            finish = raw.get("status", "unknown")
            if finish == "incomplete":
                finish = (raw.get("incomplete_details") or {}).get("reason", "incomplete")
            usage = raw.get("usage", {}) or {}
            return Turn(raw, calls, text, finish, usage, usage.get("input_tokens", 0), refusal, unusable)
        content = raw.get("content", [])
        calls = [ToolCall(x["id"], x["name"], x.get("input")) for x in content if x.get("type") == "tool_use"]
        text = "\n".join(x.get("text", "") for x in content if x.get("type") == "text")
        usage = raw.get("usage", {})
        input_tokens = sum(usage.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        return Turn(raw, calls, text, raw.get("stop_reason", "unknown"), usage, input_tokens, raw.get("stop_reason") == "refusal", bool(raw.get("_harness_incomplete_tool_json")))

    def append_turn(self, history: list, turn: Turn):
        if turn.unusable_tool_arguments:
            raise InfrastructureError("Unusable native tool JSON cannot be appended to model history")
        if self.pending:
            raise InfrastructureError("Cannot append a turn while tools are unresolved")
        if self.provider == "openai":
            # Includes encrypted reasoning, original message phase, and all function calls.
            history.extend(copy.deepcopy(turn.raw.get("output", [])))
        else:
            history.append({"role": "assistant", "content": copy.deepcopy(turn.raw["content"])})
        self.pending = [call.id for call in turn.calls]
        if len(set(self.pending)) != len(self.pending):
            raise InfrastructureError("Provider returned duplicate tool call IDs")

    def append_results(self, history: list, results: list[tuple[ToolCall, ToolResult]]):
        if [call.id for call, _ in results] != self.pending:
            raise InfrastructureError("All tool results must match the pending calls in order")
        blocks = []
        for call, result in results:
            if self.provider == "openai":
                content = [{"type": "input_text", "text": ("Tool error: " if result.error else "") + result.text}]
                if result.image_base64:
                    content.append({"type": "input_image", "image_url": f"data:{result.media_type};base64,{result.image_base64}", "detail": "high"})
                history.append({"type": "function_call_output", "call_id": call.id, "output": content})
            else:
                content = [{"type": "text", "text": result.text}]
                if result.image_base64:
                    content.append({"type": "image", "source": {"type": "base64", "media_type": result.media_type, "data": result.image_base64}})
                blocks.append({"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": result.error})
        if self.provider == "anthropic":
            history.append({"role": "user", "content": blocks})
        self.pending = []
