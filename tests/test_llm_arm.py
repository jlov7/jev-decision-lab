import json
import os
import unittest
from unittest.mock import patch

from jev_lab import adapters, engine, llm_arm


class FakeBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class FakeResponse:
    def __init__(self, data, model="claude-haiku-4-5", stop_reason="end_turn", usage=(410, 38)):
        self.content = [FakeBlock(json.dumps(data))]
        self.model = model
        self.stop_reason = stop_reason
        self.usage = FakeUsage(*usage)
        self._request_id = "req_test"


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


GOOD = {
    "issue": "routine",
    "owner": "operations",
    "severity": 0,
    "sufficient": True,
    "contradiction": False,
    "next_evidence": "none",
}

LIVE_ENV = {"JEV_ALLOW_LIVE": "1", "ANTHROPIC_API_KEY": "test-only-not-real"}


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.request = engine.request_for(engine.case_by_id("S02"))

    def test_schema_mirrors_the_three_primitives(self):
        schema = llm_arm.schema_for(self.request["questions"])
        props = schema["properties"]
        self.assertEqual(
            props["owner"]["enum"], list(self.request["questions"]["owner"]["criteria"])
        )
        self.assertEqual(props["severity"]["enum"], [0, 1, 2, 3])
        self.assertEqual(props["sufficient"], {"type": "boolean"})
        self.assertEqual(set(schema["required"]), set(self.request["questions"]))
        self.assertFalse(schema["additionalProperties"])

    def test_prompt_carries_state_and_questions_but_never_labels(self):
        prompt = llm_arm.prompt_for(self.request)
        self.assertIn("delivered on time", prompt)
        self.assertIn("Which team should investigate", prompt)
        labels = engine.load("labels")
        for entry in labels.values():
            self.assertNotIn(entry["teaching_note"], prompt)
        self.assertNotIn("expected_owner", prompt)
        self.assertNotIn("teaching_note", prompt)


class GatingTests(unittest.TestCase):
    def setUp(self):
        self.request = engine.request_for(engine.case_by_id("S02"))

    def test_refuses_before_sending_when_not_enabled(self):
        client = FakeClient(FakeResponse(GOOD))
        with patch.dict(os.environ, {"JEV_ALLOW_LIVE": "", "ANTHROPIC_API_KEY": ""}):
            with self.assertRaises(PermissionError):
                llm_arm.ClaudeArm(client=client).call(self.request, "S02")
        self.assertEqual(client.messages.calls, [])

    def test_registry_builds_the_claude_arm(self):
        arm = adapters.build("claude")
        self.assertEqual((arm.name, arm.kind, arm.live), ("claude", "live_anthropic", True))

    def test_model_comes_from_environment_with_a_pinned_default(self):
        with patch.dict(os.environ, {"JEV_COMPARE_MODEL": ""}):
            self.assertEqual(llm_arm.model_name(), llm_arm.DEFAULT_MODEL)
        with patch.dict(os.environ, {"JEV_COMPARE_MODEL": "claude-opus-5"}):
            self.assertEqual(llm_arm.model_name(), "claude-opus-5")


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.request = engine.request_for(engine.case_by_id("S02"))

    def call(self, response):
        client = FakeClient(response)
        with patch.dict(os.environ, LIVE_ENV):
            result = llm_arm.ClaudeArm(client=client).call(self.request, "S02")
        return client, result

    def test_structured_output_is_requested_without_retries(self):
        client, _ = self.call(FakeResponse(GOOD))
        (kwargs,) = client.messages.calls
        self.assertEqual(kwargs["model"], llm_arm.DEFAULT_MODEL)
        self.assertEqual(kwargs["output_config"]["format"]["type"], "json_schema")
        self.assertIn("owner", kwargs["output_config"]["format"]["schema"]["properties"])
        self.assertNotIn("thinking", kwargs)

    def test_answers_are_minimal_decisions_with_no_invented_distribution(self):
        _, result = self.call(FakeResponse(GOOD))
        records = result["normalized"]["records"]
        self.assertEqual(result["normalized"]["wire_schema"], "anthropic_structured_output")
        self.assertEqual(records["owner"]["answer"], "operations")
        self.assertIsNone(records["owner"]["distribution"])
        self.assertIn("category only", records["owner"]["distribution_note"])
        self.assertEqual(records["severity"]["answer"], 0)
        self.assertEqual(records["sufficient"]["answer"], 1.0)
        self.assertEqual(records["contradiction"]["answer"], 0.0)
        self.assertIsNone(records["sufficient"]["distribution"])
        self.assertIsNone(records["owner"]["provider_confidence"])

    def test_provenance_records_model_usage_latency_and_dated_price(self):
        _, result = self.call(FakeResponse(GOOD))
        p = result["provenance"]
        self.assertEqual(p["kind"], "live_anthropic")
        self.assertEqual(p["model"], "claude-haiku-4-5")
        self.assertEqual(p["usage"], {"input_tokens": 410, "output_tokens": 38})
        self.assertAlmostEqual(p["estimated_cost_usd"], 410 / 1e6 * 1.0 + 38 / 1e6 * 5.0)
        self.assertEqual(p["price_as_of"], llm_arm.PRICE_AS_OF)
        self.assertIsInstance(p["latency_ms"], float)
        self.assertEqual(p["model_calls"], 1)
        self.assertFalse(p["live_verified"])

    def test_unknown_model_price_is_unknown_not_zero(self):
        _, result = self.call(FakeResponse(GOOD, model="claude-experimental-x"))
        self.assertIsNone(result["provenance"]["estimated_cost_usd"])

    def test_truncated_output_fails_closed(self):
        with self.assertRaises(ValueError):
            self.call(FakeResponse(GOOD, stop_reason="max_tokens"))

    def test_refusal_fails_closed(self):
        with self.assertRaises(ValueError):
            self.call(FakeResponse(GOOD, stop_reason="refusal"))

    def test_choice_outside_criteria_fails_closed(self):
        bad = dict(GOOD, owner="finance")
        with self.assertRaises(ValueError):
            self.call(FakeResponse(bad))

    def test_score_outside_levels_fails_closed(self):
        bad = dict(GOOD, severity=7)
        with self.assertRaises(ValueError):
            self.call(FakeResponse(bad))

    def test_missing_question_fails_closed(self):
        bad = {k: v for k, v in GOOD.items() if k != "issue"}
        with self.assertRaises(ValueError):
            self.call(FakeResponse(bad))

    def test_boolean_must_be_boolean(self):
        bad = dict(GOOD, sufficient="yes")
        with self.assertRaises(ValueError):
            self.call(FakeResponse(bad))


if __name__ == "__main__":
    unittest.main()
