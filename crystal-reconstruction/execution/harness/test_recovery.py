"""Synthetic correction tests; no provider, scientific data or Docker service access."""
import asyncio
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from container_tools import DockerTools
from protocol import Deadline, DeadlineExpired, InfrastructureError, ModelResourceLimit, Provider, Recorder, ToolResult
from run_agent import COMPACTION_PROMPT, COMPACTION_RETRY_PROMPT, compact


def response(provider, text="complete self-contained synthetic handoff", finish=None, calls=None, tokens=20, refusal=False):
    if provider == "openai":
        finish = finish or "completed"
        output = [{"type": "reasoning", "id": "synthetic-reasoning", "summary": [], "encrypted_content": "synthetic-opaque-placeholder"}]
        if calls:
            output += [{"type": "function_call", "id": "synthetic-item", "call_id": cid, "name": name, "arguments": args} for cid, name, args in calls]
        else:
            output.append({"type": "message", "id": "synthetic-message", "role": "assistant", "status": "completed" if finish == "completed" else "incomplete",
                           "phase": "final_answer" if finish == "completed" else "commentary",
                           "content": [{"type": "refusal", "refusal": "synthetic refusal"}] if refusal else [{"type": "output_text", "text": text, "annotations": []}]})
        return {"id": "synthetic-response", "status": "incomplete" if finish == "max_output_tokens" else finish,
                "incomplete_details": {"reason": finish} if finish == "max_output_tokens" else None,
                "output": output, "usage": {"input_tokens": tokens, "output_tokens": 64000 if finish == "max_output_tokens" else 30}}
    content = ([{"type": "tool_use", "id": cid, "name": name, "input": json.loads(args)} for cid, name, args in calls]
               if calls else [{"type": "text", "text": text}])
    return {"id": "synthetic-message", "type": "message", "role": "assistant", "model": "fixture", "content": content,
            "stop_reason": "refusal" if refusal else finish or ("tool_use" if calls else "end_turn"),
            "usage": {"input_tokens": tokens, "output_tokens": 64000 if finish == "max_tokens" else 30}}


def stream(provider, raw):
    if provider == "openai":
        events = [{"type": "response.incomplete" if raw["status"] == "incomplete" else "response.completed", "response": raw}]
    else:
        events = [{"type": "message_start", "message": raw}, {"type": "message_stop"}]
    return "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()


class Tools:
    def __init__(self):
        self.calls = []

    async def execute(self, call, deadline):
        self.calls.append((call.name, call.arguments))
        return ToolResult("synthetic tool observation")


class FixedDeadline:
    """Deterministic remaining-time strings for a request-trace equivalence test."""
    def remaining(self):
        return 100.0

    async def bound(self, awaitable, cap=None):
        return await awaitable


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.count = 0

    def provider(self, name, replies, delay_after_first=0):
        self.count += 1
        recorder = Recorder(Path(self.temp.name) / str(self.count))
        requests = []
        iterator = iter(replies)
        async def handler(request):
            requests.append(json.loads(request.content))
            if len(requests) > 1 and delay_after_first:
                await asyncio.sleep(delay_after_first)
            raw = next(iterator)
            return httpx.Response(200, content=stream(name, raw), headers={"content-type": "text/event-stream"})
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(client.aclose)
        return Provider(name, "fixture", "not-a-real-key", recorder, client=client), requests, recorder

    async def successful_retry(self, name):
        cap = "max_output_tokens" if name == "openai" else "max_tokens"
        first = response(name, "unfinished synthetic handoff", cap)
        provider, requests, recorder = self.provider(name, [first, response(name)])
        history = [provider.user("EXACT OBJECTIVE\n")]
        fresh = await compact(provider, Tools(), history, "EXACT OBJECTIVE\n", Deadline(2), recorder)
        self.assertEqual(len(requests), 2)
        field = "input" if name == "openai" else "messages"
        self.assertEqual(requests[1][field][0], {"role": "user", "content": "EXACT OBJECTIVE\n"})
        self.assertEqual(requests[1][field][1]["content"], COMPACTION_PROMPT)
        self.assertEqual(requests[1][field][-1]["content"], COMPACTION_RETRY_PROMPT)
        if name == "openai":
            self.assertEqual(requests[1][field][2:-1], first["output"])
            self.assertTrue(all(r["max_output_tokens"] == 64000 and r["reasoning"]["effort"] == "max" for r in requests))
        else:
            self.assertEqual(requests[1][field][2]["content"], first["content"])
            self.assertTrue(all(r["max_tokens"] == 64000 and r["output_config"]["effort"] == "max" for r in requests))
        self.assertEqual(requests[0]["tools"], requests[1]["tools"])
        self.assertFalse(provider.pending)
        self.assertEqual(len(fresh), 2)
        self.assertEqual(fresh[0]["content"], "EXACT OBJECTIVE\n")
        self.assertIn("complete self-contained synthetic handoff", fresh[1]["content"])
        self.assertNotIn("unfinished synthetic handoff", fresh[1]["content"])

    async def test_openai_retry_preserves_native_history_and_replaces_only_after_complete_handoff(self):
        await self.successful_retry("openai")

    async def test_anthropic_retry_preserves_native_history_and_replaces_only_after_complete_handoff(self):
        await self.successful_retry("anthropic")

    async def test_three_capped_handoffs_stop_without_fourth_call_or_history_loss(self):
        for name, cap in (("openai", "max_output_tokens"), ("anthropic", "max_tokens")):
            with self.subTest(provider=name):
                provider, requests, recorder = self.provider(name, [response(name, "partial " + str(i), cap) for i in range(3)] + [response(name)])
                history = [provider.user("EXACT OBJECTIVE")]
                with self.assertRaisesRegex(InfrastructureError, "three handoff attempts"):
                    await compact(provider, Tools(), history, "EXACT OBJECTIVE", Deadline(2), recorder)
                self.assertEqual(len(requests), 3)
                self.assertEqual(history[0]["content"], "EXACT OBJECTIVE")
                serialized = json.dumps(history)
                self.assertTrue(all("partial " + str(i) in serialized for i in range(3)))
                self.assertEqual(serialized.count(COMPACTION_RETRY_PROMPT), 2)

    async def test_empty_refusal_pause_or_unknown_status_is_not_a_complete_handoff(self):
        for kwargs in ({"text": ""}, {"refusal": True}, {"finish": "pause_turn"}, {"finish": "unrecognized"}):
            with self.subTest(case=kwargs):
                provider, requests, recorder = self.provider("openai", [response("openai", **kwargs)])
                with self.assertRaisesRegex(InfrastructureError, "complete handoff"):
                    await compact(provider, Tools(), [], "objective", Deadline(2), recorder)
                self.assertEqual(len(requests), 1)

    async def test_retry_remains_inside_original_deadline(self):
        provider, requests, recorder = self.provider("openai", [response("openai", "partial", "max_output_tokens"), response("openai")], delay_after_first=1)
        deadline = Deadline(0.03)
        original_epoch = deadline.epoch
        with self.assertRaises(DeadlineExpired):
            await compact(provider, Tools(), [], "objective", deadline, recorder)
        self.assertEqual(len(requests), 2)
        self.assertEqual(deadline.epoch, original_epoch)
        self.assertEqual(deadline.remaining(), 0)

    async def test_tool_on_second_attempt_is_resolved_before_third_handoff_request(self):
        tool_response = response("openai", calls=[("synthetic-call", "bash", '{"command":"true","timeout_s":1}')])
        provider, requests, recorder = self.provider("openai", [response("openai", "partial", "max_output_tokens"), tool_response, response("openai")])
        tools = Tools()
        await compact(provider, tools, [], "objective", Deadline(2), recorder)
        self.assertEqual(len(requests), 3)
        self.assertEqual(len(tools.calls), 1)
        self.assertEqual(requests[2]["input"][-2]["type"], "function_call_output")
        self.assertEqual(requests[2]["input"][-2]["call_id"], "synthetic-call")
        self.assertEqual(requests[2]["input"][-1]["content"], COMPACTION_PROMPT)

    async def test_capped_unusable_tool_json_does_not_enter_text_retry(self):
        raw = response("openai", finish="max_output_tokens", calls=[("synthetic-call", "bash", '{"command":')])
        provider, requests, recorder = self.provider("openai", [raw])
        with self.assertRaises(ModelResourceLimit):
            await compact(provider, Tools(), [], "objective", Deadline(2), recorder)
        self.assertEqual(len(requests), 1)

    async def collect_case(self, detail, inspect_code=0, inspect_id="synthetic-container", required_missing=False):
        recorder = Recorder(Path(self.temp.name) / ("collect-" + str(self.count)))
        self.count += 1
        tools = DockerTools("synthetic-image", recorder, 4, "16g", "fixture")
        tools.container = "synthetic-container"
        tools.frozen = True
        calls = []
        async def command(argv, timeout):
            calls.append(argv)
            if argv[1] == "inspect":
                return inspect_code, (inspect_id + "\n").encode(), b""
            if argv[-2].endswith(":/app/notes"):
                return 1, b"", detail.encode()
            target = Path(argv[-1]); target.mkdir(parents=True)
            (target / "answer.txt").write_text("synthetic final answer")
            return 0, b"", b""
        with patch("container_tools.command", command):
            result = await tools.collect(["/app/notes", "/app/results"], ["/app/notes" if required_missing else "/app/results/answer.txt"])
        return result, calls

    async def test_missing_optional_path_with_exact_live_container_is_not_an_infrastructure_error(self):
        result, calls = await self.collect_case("Error: No such container:path: synthetic-container:/app/notes\n")
        self.assertEqual(result["collection_errors"], [])
        self.assertTrue(result["submissions"][0]["present"])
        self.assertEqual(sum(c[1] == "inspect" for c in calls), 1)

    async def test_missing_required_submission_is_recorded_absent_without_infrastructure_error(self):
        result, _ = await self.collect_case("Error: No such container:path: synthetic-container:/app/notes\n", required_missing=True)
        self.assertEqual(result["collection_errors"], [])
        self.assertFalse(result["submissions"][0]["present"])

    async def test_missing_container_identity_mismatch_and_other_docker_errors_remain_failures(self):
        exact = "Error: No such container:path: synthetic-container:/app/notes\n"
        for detail, code, identity in ((exact, 1, ""), (exact, 0, "other-container"),
                                       ("Cannot connect to Docker daemon", 0, "synthetic-container"),
                                       ("Error: No such container:path: synthetic-container:/other\n", 0, "synthetic-container")):
            with self.subTest(error=detail, inspect_code=code, identity=identity):
                result, _ = await self.collect_case(detail, code, identity)
                self.assertEqual(len(result["collection_errors"]), 1)

    async def test_valid_normal_and_successful_first_compaction_request_traces_equal_original(self):
        # Original harness stays read-only; import its runner against byte-identical protocol.
        original_path = Path(__file__).resolve().parents[1] / "original_harness/run_agent.py"
        spec = importlib.util.spec_from_file_location("original_frozen_run_agent", original_path)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        import run_agent as corrected
        self.assertEqual(original.COMPACTION_PROMPT, corrected.COMPACTION_PROMPT)
        self.assertEqual(original.CONTINUATION_PROMPT, corrected.CONTINUATION_PROMPT)
        for name in ("openai", "anthropic"):
            for should_compact in (False, True):
                with self.subTest(provider=name, compaction=should_compact):
                    replies = [response(name, calls=[("c1", "bash", '{"command":"true","timeout_s":1}')], tokens=2000 if should_compact else 20), response(name)]
                    if should_compact:
                        replies.append(response(name, "synthetic final answer"))
                    observed = []
                    for module in (original, corrected):
                        provider, requests, recorder = self.provider(name, copy.deepcopy(replies))
                        tools = Tools()
                        result = await module.agent_loop(provider, tools, "EXACT OBJECTIVE\n", FixedDeadline(), recorder, compact_tokens=1000)
                        observed.append((requests, tools.calls, result))
                    self.assertEqual(observed[0], observed[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
