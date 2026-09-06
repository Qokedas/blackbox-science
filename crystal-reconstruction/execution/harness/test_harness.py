"""Offline tests: mocked provider protocols, deadlines, completion and artifact safety."""
from __future__ import annotations

import asyncio
import base64
import copy
import io
import json
import os
import tempfile
import time
import unittest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image

from container_tools import DockerTools, artifact_relative, check_docker_error, clean_env, render_image
from protocol import Deadline, DeadlineExpired, InfrastructureError, Provider, ProviderError, Recorder, ToolCall, ToolResult, Turn
from run_agent import COMPACTION_PROMPT, SmokeTools, agent_loop, compact, main_async, parser, run_session


def sse(*events):
    return "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()


def astra(output=None, status="completed", **extra):
    return {"id": "resp_1", "status": status, "incomplete_details": None, "output": output or [{"type": "message", "id": "msg_1", "role": "assistant", "phase": "final_answer", "content": [{"type": "output_text", "text": "finished", "annotations": []}]}],
            "usage": {"input_tokens": 12, "output_tokens": 3, "output_tokens_details": {"reasoning_tokens": 2}}, **extra}


class FakeProvider:
    def __init__(self, turns):
        self.turns = iter(turns)
        self.pending = []
        self.calls_seen = []
        self.histories = []
        self.provider = "openai"

    def user(self, text):
        return {"role": "user", "content": text}

    async def call(self, history, deadline, purpose="trial"):
        self.calls_seen.append(purpose)
        self.histories.append(copy.deepcopy(history))
        item = next(self.turns)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return await item()
        return item

    def append_turn(self, history, turn):
        self.pending = [c.id for c in turn.calls]
        history.append({"role": "assistant", "content": turn.text})

    def append_results(self, history, results):
        if [c.id for c, _ in results] != self.pending:
            raise AssertionError("Unresolved tool history")
        history.append({"role": "tool", "content": [r.text for _, r in results]})
        self.pending = []


def simple_turn(text="done", calls=None, finish="completed", tokens=20, refusal=False):
    return Turn({}, calls or [], text, finish, {}, tokens, refusal)


class FakeTools:
    def __init__(self, delay=0):
        self.delay = delay
        self.events = []
        self.frozen = False

    async def execute(self, call, deadline):
        self.events.append("tool_start:" + call.id)
        if self.frozen:
            raise AssertionError("Tool after freeze")
        await asyncio.sleep(self.delay)
        self.events.append("tool_end:" + call.id)
        return ToolResult("observed output")

    async def freeze(self, reason):
        if not self.frozen:
            self.events.append("freeze:" + reason)
            self.frozen = True


class HarnessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.recorder = Recorder(self.out)

    def provider(self, name, handler, **kwargs):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(client.aclose)
        return Provider(name, "exact-requested-id", "host-secret", self.recorder, client=client, **kwargs)

    async def test_responses_preserves_reasoning_phase_and_native_image_tool_output(self):
        reasoning = {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "opaque-reasoning"}
        phase_message = {"type": "message", "id": "m_1", "role": "assistant", "phase": "commentary", "content": [{"type": "output_text", "text": "looking", "annotations": []}]}
        function = {"type": "function_call", "id": "fc_1", "call_id": "call_1", "name": "view_image", "arguments": '{"path":"/app/img.png"}'}
        raw = astra([reasoning, phase_message, function])
        payloads = []

        def handler(request):
            payloads.append(json.loads(request.content))
            return httpx.Response(200, content=sse({"type": "response.completed", "response": raw if len(payloads) == 1 else astra()}))
        provider = self.provider("openai", handler)
        history = [provider.user("unchanged scientific instruction")]
        turn = await provider.call(history, Deadline(2))
        provider.append_turn(history, turn)
        provider.append_results(history, [(turn.calls[0], ToolResult("pixels", image_base64="aW1hZ2U=", media_type="image/png"))])
        await provider.call(history, Deadline(2))
        self.assertEqual(payloads[1]["input"][1:4], [reasoning, phase_message, function])
        image = payloads[1]["input"][4]["output"][1]
        self.assertEqual(image, {"type": "input_image", "image_url": "data:image/png;base64,aW1hZ2U=", "detail": "high"})
        self.assertFalse(payloads[0]["store"])
        self.assertEqual(payloads[0]["include"], ["reasoning.encrypted_content"])
        self.assertEqual(payloads[0]["reasoning"], {"effort": "max"})
        self.assertEqual(payloads[0]["model"], "exact-requested-id")
        self.assertEqual(payloads[0]["max_output_tokens"], 64000)
        self.assertNotIn("host-secret", (self.out / "provider/00001.request.json").read_text())

    async def test_claude_stream_assembles_exact_thinking_and_tools(self):
        events = [
            {"type": "message_start", "message": {"id": "msg_1", "role": "assistant", "type": "message", "content": [], "usage": {"input_tokens": 20, "output_tokens": 1}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "exact thought"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "exact-signature"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "tool_1", "name": "view_image", "input": {}}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"path":'}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '"/app/image.png"}'}},
            {"type": "content_block_stop", "index": 1},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 12}},
            {"type": "message_stop"},
        ]
        provider = self.provider("anthropic", lambda request: httpx.Response(200, content=sse(*events)))
        history = [provider.user("objective")]
        turn = await provider.call(history, Deadline(2))
        provider.append_turn(history, turn)
        self.assertEqual(history[1]["content"][0], {"type": "thinking", "thinking": "exact thought", "signature": "exact-signature"})
        provider.append_results(history, [(turn.calls[0], ToolResult("pixels", image_base64="aW1n", media_type="image/png"))])
        self.assertEqual(history[2]["content"][0]["tool_use_id"], "tool_1")
        self.assertEqual(history[2]["content"][0]["content"][1]["source"]["data"], "aW1n")
        self.assertEqual(provider.payload(history)["thinking"], {"type": "adaptive"})
        self.assertEqual(provider.payload(history)["output_config"], {"effort": "max"})
        self.assertEqual(turn.usage, {"input_tokens": 20, "output_tokens": 12})

    async def test_nonretryable_400_does_not_change_model_or_history(self):
        attempts = []
        def handler(request):
            attempts.append(json.loads(request.content))
            return httpx.Response(400, json={"error": {"message": "Unsupported model"}})
        provider = self.provider("openai", handler)
        with self.assertRaises(ProviderError):
            await provider.call([provider.user("objective")], Deadline(2))
        self.assertEqual(len(attempts), 1)

    async def test_completed_claude_output_cap_inside_tool_is_valid_resource_limit(self):
        events = [
            {"type": "message_start", "message": {"id": "m", "role": "assistant", "content": [], "usage": {}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t", "name": "write_file", "input": {}}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"path":'}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "max_tokens"}, "usage": {}},
            {"type": "message_stop"},
        ]
        provider = self.provider("anthropic", lambda request: httpx.Response(200, content=sse(*events)))
        history = [provider.user("original")]
        turn = await provider.call(history, Deadline(1))
        self.assertTrue(turn.unusable_tool_arguments)
        with self.assertRaises(InfrastructureError):
            provider.append_turn(history, turn)
        self.assertEqual(history, [{"role": "user", "content": "original"}])
        self.assertNotIn("__invalid_json__", (self.out / "provider/00001.1.events.jsonl").read_text())
        tools = FakeTools()
        result = await run_session(provider, tools, "original", Deadline(1), self.recorder)
        self.assertEqual(result["termination"], "resource_limit_incomplete_tool")
        self.assertEqual(tools.events, ["freeze:resource_limit_incomplete_tool"])

    async def test_completed_astra_output_cap_inside_tool_is_same_resource_limit(self):
        raw = astra([{"type": "function_call", "id": "f", "call_id": "c", "name": "write_file", "arguments": '{"path":'}], status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        provider = self.provider("openai", lambda request: httpx.Response(200, content=sse({"type": "response.incomplete", "response": raw})))
        tools = FakeTools()
        result = await run_session(provider, tools, "original", Deadline(1), self.recorder)
        self.assertEqual(result["termination"], "resource_limit_incomplete_tool")
        self.assertEqual(tools.events, ["freeze:resource_limit_incomplete_tool"])
        self.assertEqual(raw["output"][0]["arguments"], '{"path":')

    async def test_unfinished_sse_is_infrastructure_not_resource_limit(self):
        events = [
            {"type": "message_start", "message": {"id": "m", "role": "assistant", "content": [], "usage": {}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "t", "name": "write_file", "input": {}}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"path":'}},
            {"type": "content_block_stop", "index": 0},
        ]
        provider = self.provider("anthropic", lambda request: httpx.Response(200, content=sse(*events)), max_attempts=1)
        with self.assertRaises(ProviderError):
            await run_session(provider, FakeTools(), "original", Deadline(1), self.recorder)

    async def test_content_filter_finish_is_refusal_not_infrastructure(self):
        raw = astra(status="incomplete", incomplete_details={"reason": "content_filter"})
        provider = self.provider("openai", lambda request: httpx.Response(200, content=sse({"type": "response.incomplete", "response": raw})))
        turn = await provider.call([provider.user("instruction")], Deadline(1))
        self.assertTrue(turn.refusal)

    async def test_terminal_response_does_not_wait_for_a_lingering_connection(self):
        class LingeringStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield sse({"type": "response.completed", "response": astra()})
                await asyncio.sleep(10)
        provider = self.provider("openai", lambda request: httpx.Response(200, stream=LingeringStream()))
        turn = await provider.call([provider.user("instruction")], Deadline(0.3))
        self.assertEqual(turn.finish_reason, "completed")

    async def test_rate_limit_retry_wait_is_inside_absolute_deadline(self):
        attempts = []
        def handler(request):
            attempts.append(1)
            return httpx.Response(429, json={"error": {"message": "busy"}})
        provider = self.provider("openai", handler)
        start = time.monotonic()
        with self.assertRaises(DeadlineExpired):
            await provider.call([provider.user("objective")], Deadline(0.04))
        self.assertEqual(len(attempts), 1)
        self.assertLess(time.monotonic() - start, 0.3)

    async def test_pending_calls_cannot_be_compacted_or_sent(self):
        provider = self.provider("openai", lambda request: self.fail("No network request allowed"))
        provider.pending = ["unresolved"]
        with self.assertRaises(InfrastructureError):
            await provider.call([], Deadline(1))
        with self.assertRaises(InfrastructureError):
            await compact(provider, FakeTools(), [], "instruction", Deadline(1), self.recorder)

    async def test_all_parallel_call_results_required_in_same_order(self):
        provider = self.provider("anthropic", lambda request: self.fail())
        calls = [ToolCall("a", "bash", {}), ToolCall("b", "bash", {})]
        provider.pending = ["a", "b"]
        with self.assertRaises(InfrastructureError):
            provider.append_results([], [(calls[0], ToolResult("first"))])
        history = []
        provider.append_results(history, [(c, ToolResult(c.id)) for c in calls])
        self.assertEqual([x["tool_use_id"] for x in history[0]["content"]], ["a", "b"])
        self.assertEqual(provider.pending, [])

    async def test_natural_finish_freezes_background_work(self):
        provider, tools = FakeProvider([simple_turn()]), FakeTools()
        result = await run_session(provider, tools, "instruction", Deadline(1), self.recorder)
        self.assertEqual(result["termination"], "model_finished")
        self.assertEqual(tools.events, ["freeze:model_finished"])

    async def test_deadline_cancels_api_and_freezes(self):
        cancelled = []
        async def slow():
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append(True)
        tools = FakeTools()
        start = time.monotonic()
        result = await run_session(FakeProvider([slow]), tools, "instruction", Deadline(0.03), self.recorder)
        self.assertEqual(result["termination"], "deadline")
        self.assertTrue(cancelled)
        self.assertEqual(tools.events, ["freeze:deadline"])
        self.assertLess(time.monotonic() - start, 0.3)

    async def test_deadline_stops_tool_batch_before_later_call(self):
        calls = [ToolCall("one", "bash", {}), ToolCall("two", "bash", {})]
        tools = FakeTools(delay=10)
        provider = FakeProvider([simple_turn(calls=calls)])
        result = await run_session(provider, tools, "instruction", Deadline(0.03), self.recorder)
        self.assertEqual(result["termination"], "deadline")
        self.assertEqual(tools.events, ["tool_start:one", "freeze:deadline"])
        self.assertEqual(len(provider.calls_seen), 1)

    async def test_provider_failure_freezes_and_propagates_infrastructure(self):
        tools = FakeTools()
        with self.assertRaises(ProviderError):
            await run_session(FakeProvider([ProviderError("invalid model", 400)]), tools, "instruction", Deadline(1), self.recorder)
        self.assertTrue(tools.frozen)

    async def test_refusal_ends_without_answer_or_submission_nudge(self):
        provider = FakeProvider([simple_turn(text="cannot do this", refusal=True)])
        result = await run_session(provider, FakeTools(), "instruction", Deadline(1), self.recorder)
        self.assertEqual(result["termination"], "model_refusal")
        self.assertEqual(len(provider.calls_seen), 1)

    async def test_compaction_preserves_exact_instruction_and_only_own_handoff(self):
        calls = [ToolCall("a", "bash", {}), ToolCall("b", "bash", {})]
        provider = FakeProvider([simple_turn(calls=calls, tokens=200), simple_turn("Observed A; next inspect B."), simple_turn("finished")])
        tools = FakeTools()
        result = await agent_loop(provider, tools, "EXACT SCIENTIFIC INSTRUCTION\n", Deadline(1), self.recorder, compact_tokens=100)
        self.assertEqual(result["termination"], "model_finished")
        self.assertEqual(provider.calls_seen, ["trial", "compaction", "trial"])
        self.assertEqual(tools.events, ["tool_start:a", "tool_end:a", "tool_start:b", "tool_end:b"])
        fresh = provider.histories[2]
        self.assertEqual(fresh[0]["content"], "EXACT SCIENTIFIC INSTRUCTION\n")
        self.assertEqual(len(fresh), 2)
        self.assertIn("Observed A; next inspect B.", fresh[1]["content"])
        self.assertNotIn("reference", fresh[1]["content"])
        self.assertEqual(provider.histories[1][-1]["content"], COMPACTION_PROMPT)

    async def test_compaction_cannot_drop_unfinished_handoff(self):
        provider = FakeProvider([simple_turn("partial handoff", finish="max_output_tokens") for _ in range(3)])
        with self.assertRaises(InfrastructureError):
            await compact(provider, FakeTools(), [], "objective", Deadline(1), self.recorder)
        self.assertEqual(provider.calls_seen, ["compaction"] * 3)

    async def test_deadline_epoch_only_shortens_budget(self):
        deadline = Deadline(100, time.time() + 0.03)
        self.assertLess(deadline.remaining(), 0.04)
        await asyncio.sleep(0.04)
        with self.assertRaises(DeadlineExpired):
            await deadline.bound(asyncio.sleep(0))
        self.assertLessEqual(Deadline(0.01, time.time() + 100).seconds, 0.01)

    async def test_collect_requires_freeze_and_maps_selected_final_files(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container = "container"
        with self.assertRaises(InfrastructureError):
            await tools.collect(["/app/results"], ["/app/results/result.json"])
        tools.frozen = True
        async def cp(argv, timeout):
            target = Path(argv[-1]); target.mkdir(parents=True)
            (target / "result.json").write_text('{"final":true}')
            (target / "checkpoint.json").write_text('{"better":true}')
            return 0, b"", b""
        with patch("container_tools.command", cp):
            artifacts = await tools.collect(["/app/results"], ["/app/results/result.json"])
        self.assertEqual(len(artifacts["submissions"]), 1)
        self.assertEqual(artifacts["submissions"][0]["artifact_path"], "artifacts/results/result.json")
        self.assertTrue(artifacts["submissions"][0]["present"])
        self.assertEqual(artifacts["selection_policy"], "final_files_at_container_freeze")

    async def test_missing_artifact_is_model_nonsubmission_not_copy_infrastructure(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container, tools.frozen = "container", True
        with patch("container_tools.command", AsyncMock(return_value=(1, b"", b"Error: Could not find the file /app/results in container x"))):
            artifacts = await tools.collect(["/app/results"], ["/app/results/result.json"])
        self.assertFalse(artifacts["submissions"][0]["present"])
        self.assertEqual(artifacts["collection_errors"], [])

    async def test_directory_submission_has_deterministic_file_manifest(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container, tools.frozen = "container", True
        async def cp(argv, timeout):
            target = Path(argv[-1]); (target / "assignments").mkdir(parents=True)
            (target / "assignments/one.csv").write_text("a,b\n1,2\n")
            (target / "answers.csv").write_text("answer\n")
            return 0, b"", b""
        with patch("container_tools.command", cp):
            artifacts = await tools.collect(["/app/results"], ["/app/results/answers.csv", "/app/results/assignments"])
        directory = artifacts["submissions"][1]
        self.assertTrue(directory["present"])
        self.assertEqual(directory["type"], "directory")
        self.assertEqual(directory["files"][0]["path"], "one.csv")
        self.assertEqual(len(directory["manifest_sha256"]), 64)

    async def test_model_stderr_cannot_falsely_claim_daemon_failure(self):
        with patch("container_tools.command", AsyncMock(return_value=(0, b'{"Running":true}', b""))):
            await check_docker_error(1, "Error response from daemon: spoof", "container")
        with patch("container_tools.command", AsyncMock(return_value=(1, b"", b"daemon disconnected"))):
            with self.assertRaises(InfrastructureError):
                await check_docker_error(1, "Cannot connect to the Docker daemon", "container")

    async def test_copy_failure_is_not_missing_submission(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container, tools.frozen = "container", True
        with patch("container_tools.command", AsyncMock(return_value=(1, b"", b"Cannot connect to Docker daemon"))):
            artifacts = await tools.collect(["/app/results"], ["/app/results/result.json"])
        self.assertEqual(len(artifacts["collection_errors"]), 1)

    async def test_symlink_is_not_selected_or_hashed_as_final_submission(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container, tools.frozen = "container", True
        secret = self.out / "host-only.txt"; secret.write_text("host data")
        async def cp(argv, timeout):
            target = Path(argv[-1]); target.mkdir(parents=True)
            (target / "result.json").symlink_to(secret)
            return 0, b"", b""
        with patch("container_tools.command", cp):
            artifacts = await tools.collect(["/app/results"], ["/app/results/result.json"])
        self.assertFalse(artifacts["submissions"][0]["present"])
        self.assertNotIn("sha256", artifacts["inventory"][0])

    async def test_freeze_falls_back_to_kill_when_pause_fails(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container = "container"
        mocked = AsyncMock(side_effect=[(1, b"", b"pause error"), (0, b'{"Running":true}', b""), (0, b"", b"")])
        with patch("container_tools.command", mocked):
            await tools.freeze("deadline")
            await tools.freeze("finish")
        self.assertTrue(tools.frozen)
        self.assertEqual(tools.freeze_record["method"], "kill")
        self.assertEqual(mocked.call_count, 3)

    async def test_unfreezable_container_is_infrastructure_failure(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container = "container"
        with patch("container_tools.command", AsyncMock(return_value=(1, b"", b"daemon unavailable"))):
            with self.assertRaises(InfrastructureError):
                await tools.freeze("deadline")
        self.assertFalse(tools.frozen)

    async def test_independent_guard_fires_while_main_event_loop_is_blocked(self):
        fake_bin = self.out / "bin"; fake_bin.mkdir()
        trace = self.out / "guard-docker-trace.json"
        executable = fake_bin / "docker"
        executable.write_text("#!" + sys.executable + "\nimport os,sys,json,time\nif sys.argv[1]=='inspect':\n print(json.dumps([{'Config':{'Labels':{'qokedas.trial':'trial'}},'State':{'Running':True,'Paused':False}}]))\nelif sys.argv[1]=='pause':\n open(os.environ['HARNESS_GUARD_TRACE'],'w').write(json.dumps({'epoch':time.time(),'credentials_present':'OPENAI_API_KEY' in os.environ}))\n")
        executable.chmod(0o755)
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container = "exact-container"
        deadline = Deadline(0.8)
        try:
            with patch.dict("os.environ", {"PATH": str(fake_bin) + os.pathsep + os.environ["PATH"], "HARNESS_GUARD_TRACE": str(trace), "OPENAI_API_KEY": "secret"}):
                await tools.arm_deadline(deadline)
                time.sleep(1.1)  # Intentional: only the independent process can enforce time here.
            data = json.loads(trace.read_text())
            self.assertFalse(data["credentials_present"])
            self.assertLess(abs(data["epoch"] - deadline.epoch), 0.30)
            guard = json.loads((self.out / "deadline_guard.json").read_text())
            self.assertEqual(guard["status"], "frozen")
            self.assertEqual(guard["container_id"], "exact-container")
        finally:
            await tools.disarm_deadline()

    async def test_independent_guard_rejects_wrong_trial_label(self):
        fake_bin = self.out / "bin"; fake_bin.mkdir()
        executable = fake_bin / "docker"
        executable.write_text("#!" + sys.executable + "\nimport json\nprint(json.dumps([{'Config':{'Labels':{'qokedas.trial':'other-trial'}},'State':{'Running':True}}]))\n")
        executable.chmod(0o755)
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        tools.container = "exact-container"
        try:
            with patch.dict("os.environ", {"PATH": str(fake_bin) + os.pathsep + os.environ["PATH"]}):
                with self.assertRaises(InfrastructureError):
                    await tools.arm_deadline(Deadline(2))
        finally:
            with self.assertRaises(InfrastructureError):
                await tools.disarm_deadline()

    async def test_image_renderer_same_pixels_and_size_for_both_protocols(self):
        source = io.BytesIO(); Image.new("RGB", (3000, 1000), "red").save(source, "PNG")
        result = render_image(source.getvalue(), "/app/image.png")
        rendered = Image.open(io.BytesIO(base64.b64decode(result.image_base64)))
        self.assertEqual(rendered.size, (1568, 523))
        self.assertEqual(result.media_type, "image/png")

    async def test_host_credentials_not_in_tool_process_environment(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "secret", "ANTHROPIC_API_KEY": "other", "GOOGLE_APPLICATION_CREDENTIALS": "/host/key", "PATH": "/bin"}):
            env = clean_env()
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("GOOGLE_APPLICATION_CREDENTIALS", env)
        self.assertEqual(env["PATH"], "/bin")

    async def test_paths_cannot_escape_artifact_directory(self):
        for path in ("/app/../host", "relative", "/", "/app//results"):
            with self.assertRaises(ValueError):
                artifact_relative(path)
        self.assertEqual(str(artifact_relative("/app/results/final.json")), "artifacts/results/final.json")

    async def test_smoke_never_executes_unspecified_shell_command(self):
        tools = SmokeTools()
        result = await tools.execute(ToolCall("x", "bash", {"command": "cat /host/secret", "timeout_s": 1}), Deadline(1))
        self.assertTrue(result.error)

    async def test_raw_and_returned_output_truncation_are_separately_declared(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        with patch("container_tools.LOG_LIMIT", 128), patch("container_tools.RETURN_LIMIT", 64):
            code, out, err = await tools._logged_exec([sys.executable, "-c", "print('a'*150+'z'*150,end='')"], Deadline(2), 1)
        self.assertEqual(code, 0)
        self.assertIn("output truncated", out)
        self.assertTrue(out.startswith("a" * 32))
        self.assertTrue(out.endswith("z" * 32))
        self.assertEqual((self.out / "tools/00001.stdout").stat().st_size, 128)
        event = json.loads((self.out / "trajectory.jsonl").read_text().splitlines()[-1])
        self.assertEqual(event["streams"]["stdout"]["observed_bytes"], 300)
        self.assertTrue(event["streams"]["stdout"]["log_truncated"])
        self.assertTrue(event["streams"]["stdout"]["returned_truncated"])

    async def test_aborted_tool_keeps_explicit_partial_log_metadata(self):
        tools = DockerTools("image", self.recorder, 4, "20g", "trial")
        with self.assertRaises(asyncio.TimeoutError):
            await tools._logged_exec([sys.executable, "-c", "import time;print('started',flush=True);time.sleep(5)"], Deadline(2), 0.08)
        event = json.loads((self.out / "trajectory.jsonl").read_text().splitlines()[-1])
        self.assertEqual(event["event"], "tool_process_aborted")
        self.assertIn("stdout", event["streams"])
        self.assertIn("read_to_eof", event["streams"]["stdout"])

    async def run_mock_trial(self, turns, *, collection_errors=None, present=False, budget=1):
        class CompleteFakeProvider(FakeProvider):
            max_output = 64000
            usage_records = []
            async def close(self):
                pass

        class CompleteFakeDocker(FakeTools):
            container = None
            image_id = "sha256:frozen-image"
            freeze_record = None
            async def start(self):
                self.container = "fake-container"
            async def freeze(self, reason):
                await super().freeze(reason)
                self.freeze_record = {"reason": reason}
            async def collect(self, roots, submissions):
                assert self.frozen
                return {"submissions": [{"container_path": p, "artifact_path": str(artifact_relative(p)), "present": present} for p in submissions], "inventory": [], "collection_errors": collection_errors or []}
            async def remove(self):
                self.events.append("removed")

        destination = self.out / "mock-trial"
        instruction = self.out / "original.md"
        instruction.write_bytes(b"Exact objective.\n")
        args = parser().parse_args(["--provider", "openai", "--model", "gpt-6-astra", "--image", "image", "--instruction", str(instruction), "--out", str(destination), "--trial-id", "trial", "--submission", "/app/results/final.json", "--budget-seconds", str(budget)])
        provider, docker = CompleteFakeProvider(turns), CompleteFakeDocker()
        with patch("run_agent.Provider", return_value=provider), patch("run_agent.DockerTools", return_value=docker), patch.dict("os.environ", {"OPENAI_API_KEY": "host-secret"}), patch("builtins.print"):
            exit_code = await main_async(args)
        return exit_code, json.loads((destination / "trial_record.json").read_text()), docker

    async def test_whole_run_missing_submission_returns_zero_valid_execution(self):
        code, record, docker = await self.run_mock_trial([simple_turn()])
        self.assertEqual(code, 0)
        self.assertEqual(record["execution_status"], "completed")
        self.assertEqual(record["termination"], "model_finished")
        self.assertEqual(record["submission_status"], "missing_or_partial")
        self.assertEqual(docker.events[-1], "removed")

    async def test_whole_run_deadline_returns_zero_and_freezes(self):
        async def slow():
            await asyncio.sleep(10)
        code, record, docker = await self.run_mock_trial([slow], budget=0.02)
        self.assertEqual(code, 0)
        self.assertEqual(record["execution_status"], "completed")
        self.assertEqual(record["termination"], "deadline")
        self.assertTrue(docker.frozen)

    async def test_whole_run_collection_failure_is_nonzero_preserves_model_finish(self):
        code, record, docker = await self.run_mock_trial([simple_turn()], collection_errors=[{"error": "disk unavailable"}])
        self.assertEqual(code, 2)
        self.assertEqual(record["execution_status"], "infrastructure_failure")
        self.assertEqual(record["termination"], "model_finished")
        self.assertTrue(record["infrastructure_errors"])

    async def test_whole_run_provider_failure_is_never_model_zero(self):
        code, record, docker = await self.run_mock_trial([ProviderError("Unsupported model", 400)])
        self.assertEqual(code, 2)
        self.assertEqual(record["execution_status"], "infrastructure_failure")
        self.assertIsNone(record["scientific_score"])
        self.assertFalse(record["grading_performed"])
        self.assertTrue(docker.frozen)


if __name__ == "__main__":
    unittest.main()
