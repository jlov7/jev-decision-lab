import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from jev_lab import adapters, engine, llm_arm, provider, showcase

GOOD = {
    "issue": "routine",
    "owner": "operations",
    "severity": 0,
    "sufficient": True,
    "contradiction": False,
    "next_evidence": "none",
}


def envelope(data=GOOD, **over):
    env = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 3,
        "duration_api_ms": 4100,
        "session_id": "s-test",
        "total_cost_usd": 0.0714,
        "usage": {"input_tokens": 20, "output_tokens": 344, "cache_read_input_tokens": 32944, "cache_creation_input_tokens": 33184},
        "modelUsage": {"claude-haiku-4-5": {"costUSD": 0.0714}},
        "result": json.dumps(data),
        "structured_output": data,
    }
    env.update(over)
    return env


class Completed:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


class ClaudeCodeArmTests(unittest.TestCase):
    def setUp(self):
        self.request = engine.request_for(engine.case_by_id("S02"))
        self.calls = []

    def runner_for(self, completed):
        def run(argv, **kwargs):
            self.calls.append((argv, kwargs))
            return completed

        return run

    def test_argv_is_a_list_with_no_shell_and_the_schema(self):
        with patch.object(llm_arm, "claude_code_path", return_value="/usr/bin/claude"), patch.object(
            provider, "MAX_INPUT_BYTES", 16000
        ), patch.object(llm_arm, "BUDGET", provider.CallBudget(5)):
            arm = llm_arm.ClaudeCodeArm(runner=self.runner_for(Completed(json.dumps(envelope()))))
            result = arm.call(self.request, "S02")
        argv, kwargs = self.calls[0]
        self.assertEqual(argv[0], "/usr/bin/claude")
        self.assertIn("-p", argv)
        self.assertIn("--json-schema", argv)
        self.assertIn("--disallowedTools", argv)
        self.assertIn("--no-session-persistence", argv)
        self.assertFalse(kwargs["shell"])
        schema = json.loads(argv[argv.index("--json-schema") + 1])
        self.assertEqual(set(schema["properties"]), set(self.request["questions"]))
        self.assertNotIn("teaching_note", argv[argv.index("-p") + 1])
        self.assertEqual(result["normalized"]["records"]["owner"]["answer"], "operations")
        self.assertEqual(result["provenance"]["billing"], "subscription")
        self.assertIsNone(result["provenance"]["estimated_cost_usd"])
        self.assertAlmostEqual(result["provenance"]["list_price_equivalent_usd"], 0.0714)
        self.assertEqual(result["provenance"]["model"], "claude-haiku-4-5")
        self.assertEqual(result["provenance"]["usage"]["output_tokens"], 344)

    def test_refuses_when_the_command_is_unavailable(self):
        with patch.object(llm_arm, "claude_code_path", return_value=None):
            with self.assertRaises(PermissionError):
                llm_arm.ClaudeCodeArm(runner=self.runner_for(Completed("{}"))).call(self.request, "S02")
        self.assertEqual(self.calls, [])

    def test_opt_out_and_override_paths(self):
        with patch.dict(os.environ, {"JEV_ALLOW_CLAUDE_CODE": "0"}):
            self.assertIsNone(llm_arm.claude_code_path())
        with patch.dict(os.environ, {"JEV_ALLOW_CLAUDE_CODE": "1", "JEV_CLAUDE_CLI": "/definitely/not/here"}):
            self.assertIsNone(llm_arm.claude_code_path())

    def test_error_envelopes_fail_closed(self):
        bad = [
            json.dumps(envelope(is_error=True, subtype="error_during_execution")),
            json.dumps(envelope(structured_output=None)),
            json.dumps({"type": "something_else"}),
            "not json at all",
            json.dumps(envelope(structured_output={**GOOD, "owner": "marketing"})),
        ]
        for stdout in bad:
            with self.subTest(stdout=stdout[:40]), patch.object(
                llm_arm, "claude_code_path", return_value="/usr/bin/claude"
            ), patch.object(llm_arm, "BUDGET", provider.CallBudget(5)):
                with self.assertRaises(ValueError):
                    llm_arm.ClaudeCodeArm(runner=self.runner_for(Completed(stdout))).call(self.request, "S02")

    def test_not_logged_in_is_reported_in_plain_words(self):
        env = envelope(is_error=True, structured_output=None, result="Not logged in · Please run /login", terminal_reason="api_error")
        with patch.object(llm_arm, "claude_code_path", return_value="/usr/bin/claude"), patch.object(
            llm_arm, "BUDGET", provider.CallBudget(5)
        ):
            with self.assertRaises(ValueError) as caught:
                llm_arm.ClaudeCodeArm(runner=self.runner_for(Completed(json.dumps(env), 1))).call(self.request, "S02")
        self.assertIn("Not logged in", str(caught.exception))
        self.assertIn("sign in", str(caught.exception))

    def test_nonzero_exit_without_output_is_a_runtime_error(self):
        with patch.object(llm_arm, "claude_code_path", return_value="/usr/bin/claude"), patch.object(
            llm_arm, "BUDGET", provider.CallBudget(5)
        ):
            with self.assertRaises(RuntimeError) as caught:
                llm_arm.ClaudeCodeArm(runner=self.runner_for(Completed("", 1, "Not logged in"))).call(
                    self.request, "S02"
                )
        self.assertIn("Not logged in", str(caught.exception))


class FakeHTTPResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.requests = payload, error, []

    def open(self, request, timeout=None):
        self.requests.append(request)
        if self.error:
            raise self.error
        return FakeHTTPResponse(json.dumps(self.payload).encode())


def completion(data=GOOD, finish="stop", refusal=None, model="gpt-5-mini"):
    return {
        "id": "chatcmpl-test",
        "model": model,
        "choices": [{"finish_reason": finish, "message": {"content": json.dumps(data), "refusal": refusal}}],
        "usage": {"prompt_tokens": 400, "completion_tokens": 30},
    }


class OpenAIArmTests(unittest.TestCase):
    ENV = {"JEV_ALLOW_LIVE": "1", "OPENAI_API_KEY": "sk-test-not-real-0123456789"}

    def setUp(self):
        self.request = engine.request_for(engine.case_by_id("S02"))

    def test_strict_schema_request_and_priced_provenance(self):
        opener = FakeOpener(completion())
        with patch.dict(os.environ, self.ENV), patch.object(llm_arm, "BUDGET", provider.CallBudget(5)):
            result = llm_arm.OpenAIArm(opener=opener).call(self.request, "S02")
        sent = json.loads(opener.requests[0].data)
        self.assertEqual(sent["model"], "gpt-5-mini")
        self.assertTrue(sent["response_format"]["json_schema"]["strict"])
        self.assertEqual(set(sent["response_format"]["json_schema"]["schema"]["properties"]), set(self.request["questions"]))
        self.assertIn("max_completion_tokens", sent)
        self.assertNotIn("teaching_note", json.dumps(sent))
        self.assertEqual(opener.requests[0].get_header("Authorization"), "Bearer sk-test-not-real-0123456789")
        p = result["provenance"]
        self.assertEqual(p["model"], "gpt-5-mini")
        self.assertAlmostEqual(p["estimated_cost_usd"], 400 / 1e6 * 0.25 + 30 / 1e6 * 2.0)
        self.assertEqual(p["price_as_of"], llm_arm.OPENAI_PRICE_AS_OF)
        self.assertEqual(result["normalized"]["records"]["sufficient"]["answer"], 1.0)

    def test_refuses_before_sending_without_key_or_flag(self):
        opener = FakeOpener(completion())
        with patch.dict(os.environ, {"JEV_ALLOW_LIVE": "", "OPENAI_API_KEY": ""}):
            with self.assertRaises(PermissionError):
                llm_arm.OpenAIArm(opener=opener).call(self.request, "S02")
        self.assertEqual(opener.requests, [])

    def test_refusal_truncation_and_bad_json_fail_closed(self):
        for payload in (completion(refusal="no"), completion(finish="length"), {"choices": [{"finish_reason": "stop", "message": {"content": "nope"}}]}, {"error": "x"}):
            with self.subTest(payload=str(payload)[:40]), patch.dict(os.environ, self.ENV), patch.object(
                llm_arm, "BUDGET", provider.CallBudget(5)
            ):
                with self.assertRaises(ValueError):
                    llm_arm.OpenAIArm(opener=FakeOpener(payload)).call(self.request, "S02")

    def test_http_error_is_retained_without_the_key(self):
        err = urllib.error.HTTPError("u", 400, "Bad", {}, io.BytesIO(b'{"error":"model missing sk-test-not-real-0123456789"}'))
        with patch.dict(os.environ, self.ENV), patch.object(llm_arm, "BUDGET", provider.CallBudget(5)):
            with self.assertRaises(RuntimeError) as caught:
                llm_arm.OpenAIArm(opener=FakeOpener(error=err)).call(self.request, "S02")
        self.assertIn("400", str(caught.exception))
        self.assertNotIn("sk-test-not-real", str(caught.exception))

    def test_unknown_model_price_is_unknown_not_zero(self):
        with patch.dict(os.environ, {**self.ENV, "JEV_OPENAI_MODEL": "gpt-future"}), patch.object(
            llm_arm, "BUDGET", provider.CallBudget(5)
        ):
            result = llm_arm.OpenAIArm(opener=FakeOpener(completion(model="gpt-future"))).call(self.request, "S02")
        self.assertIsNone(result["provenance"]["estimated_cost_usd"])


class RegistryAndBudgetTests(unittest.TestCase):
    def test_registry_knows_the_new_arms(self):
        self.assertIn("claude-code", adapters.ARM_NAMES)
        self.assertIn("openai", adapters.ARM_NAMES)
        self.assertTrue({"claude-code", "openai"} <= adapters.LIVE_ARMS)
        self.assertEqual(adapters.build("claude-code").kind, "live_claude_code")
        self.assertEqual(adapters.build("openai").kind, "live_openai")

    def test_generative_arms_share_the_compare_budget(self):
        with patch.object(llm_arm, "claude_code_path", return_value="/usr/bin/claude"), patch.dict(
            os.environ, {"JEV_ALLOW_LIVE": "1", "OPENAI_API_KEY": "sk-test-not-real-0123456789", "TYPESAFE_API_KEY": "", "ANTHROPIC_API_KEY": ""}
        ), patch.object(llm_arm, "BUDGET", provider.CallBudget(5)):
            with self.assertRaises(RuntimeError) as caught:
                showcase.prepare_arms(["claude-code", "openai"], 3, consent=True)
            self.assertIn("generative baseline", str(caught.exception))
            arms = showcase.prepare_arms(["claude-code", "openai", "replay"], 2, consent=True)
            self.assertEqual(llm_arm.BUDGET.used, 4)
            self.assertEqual([a.name for a in arms], ["claude-code", "openai", "replay"])

    def test_config_reports_each_baseline(self):
        with patch.object(llm_arm, "claude_code_path", return_value="/usr/bin/claude"):
            self.assertTrue(llm_arm.arm_enabled("claude-code"))
        with patch.dict(os.environ, {"JEV_ALLOW_LIVE": "", "OPENAI_API_KEY": ""}):
            self.assertFalse(llm_arm.arm_enabled("openai"))
        self.assertFalse(llm_arm.arm_enabled("rules"))


if __name__ == "__main__":
    unittest.main()
