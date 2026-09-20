"""Received but refused outputs retain observed cost; no extra provider calls."""

import json
import os
import unittest
from unittest.mock import patch

from test_baselines import Completed, FakeOpener, completion, envelope
from test_llm_arm import GOOD, FakeClient, FakeResponse

from jev_lab import comparator, engine, llm_arm, provider


class ProviderFailureEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.request = engine.request_for(engine.case_by_id("S02"))

    def test_claude_refusal_and_malformed_output_retain_usage_and_cost(self):
        for response in (
            FakeResponse(GOOD, stop_reason="max_tokens"),
            FakeResponse({**GOOD, "owner": []}),
        ):
            with (
                self.subTest(response=response),
                patch.dict(os.environ, {"JEV_ALLOW_LIVE": "1", "ANTHROPIC_API_KEY": "test-only"}),
                patch.object(llm_arm, "BUDGET", provider.CallBudget(2)),
            ):
                client = FakeClient(response)
                with self.assertRaises(engine.LiveValidationError) as caught:
                    llm_arm.ClaudeArm(client=client).call(self.request)
                self.assertEqual(caught.exception.provenance["usage"]["input_tokens"], 410)
                self.assertGreater(caught.exception.provenance["estimated_cost_usd"], 0)
                self.assertEqual(len(client.messages.calls), 1)
                self.assertEqual(
                    caught.exception.response["content"][0]["text"], response.content[0].text
                )

    def test_openai_refusal_and_invalid_shapes_retain_raw_and_cost(self):
        examples = [
            completion(refusal="declined"),
            completion(finish="length"),
            completion(data={**GOOD, "owner": {}}),
            {**completion(), "choices": []},
        ]
        for payload in examples:
            with (
                self.subTest(payload=payload),
                patch.dict(os.environ, {"JEV_ALLOW_LIVE": "1", "OPENAI_API_KEY": "test-only"}),
                patch.object(llm_arm, "BUDGET", provider.CallBudget(2)),
            ):
                opener = FakeOpener(payload)
                with self.assertRaises(engine.LiveValidationError) as caught:
                    llm_arm.OpenAIArm(opener=opener).call(self.request)
                self.assertEqual(caught.exception.response["provider_envelope"], payload)
                self.assertAlmostEqual(caught.exception.provenance["estimated_cost_usd"], 0.00016)
                self.assertEqual(len(opener.requests), 1)

    def test_cli_error_and_nonzero_exit_retain_subscription_basis(self):
        for payload, code in (
            (envelope(is_error=True), 0),
            (envelope(), 1),
            (envelope(structured_output=None), 0),
        ):
            with (
                self.subTest(code=code, payload=payload),
                patch.object(llm_arm, "claude_code_path", return_value="/usr/bin/claude"),
                patch.object(llm_arm, "BUDGET", provider.CallBudget(2)),
            ):

                def runner(*args, payload=payload, code=code, **kwargs):
                    return Completed(json.dumps(payload), code)

                with self.assertRaises(engine.LiveValidationError) as caught:
                    llm_arm.ClaudeCodeArm(runner=runner).call(self.request)
                self.assertEqual(caught.exception.provenance["billing"], "subscription")
                self.assertIsNone(caught.exception.provenance["estimated_cost_usd"])
                self.assertEqual(caught.exception.provenance["list_price_equivalent_usd"], 0.0714)
                self.assertEqual(llm_arm.BUDGET.used, 1)

    def test_comparator_retains_failure_provenance_and_does_not_deny_attempt(self):
        with (
            patch.dict(os.environ, {"JEV_ALLOW_LIVE": "1", "OPENAI_API_KEY": "test-only"}),
            patch.object(llm_arm, "BUDGET", provider.CallBudget(2)),
        ):
            result = comparator.compare(
                ["S02"], [llm_arm.OpenAIArm(opener=FakeOpener(completion(refusal="no")))]
            )
        failure = result["arms"][0]["failures"][0]
        self.assertEqual(failure["provenance"]["kind"], "live_openai")
        self.assertEqual(result["arms"][0]["cost_summary"]["known_attempts"], 1)
        self.assertFalse(any("no authenticated call was made" in w for w in result["warnings"]))
