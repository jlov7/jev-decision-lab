import copy
import os
import unittest
from unittest.mock import patch

from jev_lab import engine, llm_arm, provider, showcase

LIVE_ENV = {"JEV_ALLOW_LIVE": "1", "TYPESAFE_API_KEY": "test-only-not-real"}
ALL_IDS = [c["id"] for c in engine.cases()]


def live_fixture(request, prepaid=None):
    """Stand-in for provider.live: the authored fixture relabelled as the pinned model."""
    case_id = next(c["id"] for c in engine.cases() if c["state"] == request["state"])
    response = copy.deepcopy(provider.replay(case_id))
    response["model"] = request["model"]
    response["usage"] = {"input_tokens": 500, "output_tokens": 40}
    provenance = {
        "kind": "live_typesafe",
        "model_calls": 1,
        "latency_ms": 123.4,
        "usage": response["usage"],
        "estimated_cost_usd": 500 / 1e6 * provider.PRICE_PER_MILLION_INPUT,
        "price_per_million_input_usd": provider.PRICE_PER_MILLION_INPUT,
        "price_as_of": "2026-09-17",
        "warning": "test",
    }
    return response, provenance


class BurstTests(unittest.TestCase):
    def test_replay_burst_runs_every_case_with_no_latency_claim(self):
        result = showcase.burst(ALL_IDS, mode="replay")
        self.assertEqual(result["kind"], "synthetic_replay")
        self.assertEqual(result["summary"]["succeeded"], 12)
        self.assertEqual(result["summary"]["failed"], 0)
        self.assertIsNone(result["summary"]["latency_ms"]["p50"])
        self.assertIsNone(result["summary"]["estimated_cost_usd"])
        self.assertEqual(result["summary"]["model_calls"], 0)
        routes = {r["case_id"]: r["receipt"]["decision"]["route"] for r in result["results"]}
        self.assertEqual(routes["S04"], "ROUTE_TO_TEAM")
        self.assertEqual(routes["S01"], "HUMAN_REVIEW")

    def test_duplicate_or_unknown_case_is_rejected_before_any_call(self):
        with self.assertRaises(ValueError):
            showcase.burst(["S01", "S01"])
        with self.assertRaises(ValueError):
            showcase.burst(["S01", "NOPE"])
        with self.assertRaises(ValueError):
            showcase.burst([])

    def test_live_burst_needs_consent_and_configuration(self):
        with patch.dict(os.environ, {"JEV_ALLOW_LIVE": "", "TYPESAFE_API_KEY": ""}):
            with self.assertRaises(PermissionError):
                showcase.burst(["S01"], mode="live", consent=False)
            with self.assertRaises(PermissionError):
                showcase.burst(["S01"], mode="live", consent=True)

    def test_live_burst_summarises_latency_tokens_and_cost(self):
        with (
            patch.dict(os.environ, LIVE_ENV),
            patch("jev_lab.provider.live", side_effect=live_fixture),
            patch.object(provider, "BUDGET", provider.CallBudget(50)),
        ):
            result = showcase.burst(ALL_IDS, mode="live", consent=True)
        s = result["summary"]
        self.assertEqual(result["kind"], "live_typesafe")
        self.assertEqual((s["succeeded"], s["failed"]), (12, 0))
        self.assertEqual(s["model_calls"], 12)
        self.assertAlmostEqual(s["latency_ms"]["p50"], 123.4)
        self.assertAlmostEqual(s["latency_ms"]["max"], 123.4)
        self.assertEqual(s["input_tokens"], 12 * 500)
        self.assertAlmostEqual(
            s["estimated_cost_usd"], 12 * 500 / 1e6 * provider.PRICE_PER_MILLION_INPUT
        )
        self.assertGreater(result["wall_ms"], 0)
        self.assertEqual(s["models"], ["jev-1.13.0"])

    def test_live_burst_refuses_when_the_attempt_budget_cannot_cover_it(self):
        with (
            patch.dict(os.environ, LIVE_ENV),
            patch.object(provider, "BUDGET", provider.CallBudget(3)),
            patch("jev_lab.provider.live", side_effect=live_fixture) as live,
        ):
            with self.assertRaises(RuntimeError):
                showcase.burst(ALL_IDS, mode="live", consent=True)
        self.assertEqual(live.call_count, 0)

    def test_one_failure_is_retained_and_does_not_stop_the_burst(self):
        def flaky(request, prepaid=None):
            if "wrong team" in request["state"]["message"] or request["state"][
                "message"
            ].startswith("The carrier delivered on time. Receiving"):
                raise RuntimeError(
                    "TypeSafe HTTP 529: Provider overloaded. No replay fallback was used."
                )
            return live_fixture(request)

        with (
            patch.dict(os.environ, LIVE_ENV),
            patch("jev_lab.provider.live", side_effect=flaky),
            patch.object(provider, "BUDGET", provider.CallBudget(50)),
        ):
            result = showcase.burst(["S02", "S04"], mode="live", consent=True)
        by_id = {r["case_id"]: r for r in result["results"]}
        self.assertTrue(by_id["S02"]["ok"])
        self.assertFalse(by_id["S04"]["ok"])
        self.assertIn("529", by_id["S04"]["error"])
        self.assertTrue(by_id["S04"]["cost_unknown"])
        self.assertEqual((result["summary"]["succeeded"], result["summary"]["failed"]), (1, 1))


class PlaygroundRequestTests(unittest.TestCase):
    def good(self):
        return {
            "state": "Synthetic: the invoice total is 12% above the approved purchase order.",
            "questions": {
                "team": {
                    "type": "choice",
                    "instructions": "Which team should look at this?",
                    "criteria": {
                        "finance": "Invoices and payments",
                        "procurement": "Purchase terms",
                    },
                },
                "severity": {
                    "type": "score",
                    "instructions": "How serious is this?",
                    "criteria": ["Trivial", "Material", "Critical"],
                },
                "needs_review": {"type": "noul", "instructions": "Does a person need to review?"},
            },
        }

    def test_valid_request_is_built_with_the_pinned_model(self):
        g = self.good()
        request = showcase.playground_request(g["state"], g["questions"])
        self.assertEqual(request["model"], engine.request_for(engine.cases()[0])["model"])
        self.assertEqual(set(request["questions"]), {"team", "severity", "needs_review"})

    def test_state_limits(self):
        g = self.good()
        with self.assertRaises(ValueError):
            showcase.playground_request("", g["questions"])
        with self.assertRaises(ValueError):
            showcase.playground_request("x" * (showcase.MAX_STATE_CHARS + 1), g["questions"])
        with self.assertRaises(ValueError):
            showcase.playground_request(42, g["questions"])

    def test_question_shape_is_validated(self):
        g = self.good()
        bad = copy.deepcopy(g["questions"])
        bad["team"]["type"] = "essay"
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], bad)
        bad = copy.deepcopy(g["questions"])
        bad["team"]["criteria"] = {"only": "one option"}
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], bad)
        bad = copy.deepcopy(g["questions"])
        bad["severity"]["criteria"] = ["one"]
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], bad)
        bad = copy.deepcopy(g["questions"])
        bad["Bad Key!"] = bad.pop("team")
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], bad)
        bad = copy.deepcopy(g["questions"])
        bad["team"]["instructions"] = ""
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], bad)
        bad = copy.deepcopy(g["questions"])
        bad["team"]["surprise"] = "field"
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], bad)
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], {})
        too_many = {
            f"q{i}": g["questions"]["needs_review"] for i in range(showcase.MAX_QUESTIONS + 1)
        }
        with self.assertRaises(ValueError):
            showcase.playground_request(g["state"], too_many)

    def test_playground_is_live_only_and_consented(self):
        g = self.good()
        with patch.dict(os.environ, {"JEV_ALLOW_LIVE": "", "TYPESAFE_API_KEY": ""}):
            with self.assertRaises(PermissionError):
                showcase.playground(g["state"], g["questions"], consent=True)
        with patch.dict(os.environ, LIVE_ENV), self.assertRaises(PermissionError):
            showcase.playground(g["state"], g["questions"], consent=False)

    def test_playground_returns_validated_response_with_provenance(self):
        g = self.good()

        def fake_live(request, prepaid=None):
            response = {
                "model": request["model"],
                "answers": {
                    "team": {
                        "type": "choice",
                        "choice": "finance",
                        "probabilities": {"finance": 0.8, "procurement": 0.2},
                        "confidence": 0.6,
                    },
                    "severity": {
                        "type": "score",
                        "score": 1.1,
                        "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2},
                        "confidence": 0.5,
                        "legend": {"0": "Trivial", "1": "Material", "2": "Critical"},
                    },
                    "needs_review": {"type": "noul", "noul": 0.66},
                },
                "usage": {"input_tokens": 210, "output_tokens": 30},
            }
            return response, {
                "kind": "live_typesafe",
                "model_calls": 1,
                "latency_ms": 88.0,
                "usage": response["usage"],
                "estimated_cost_usd": 210 / 1e6 * provider.PRICE_PER_MILLION_INPUT,
                "price_per_million_input_usd": provider.PRICE_PER_MILLION_INPUT,
                "price_as_of": "2026-09-17",
                "warning": "test",
            }

        with (
            patch.dict(os.environ, LIVE_ENV),
            patch("jev_lab.provider.live", side_effect=fake_live),
        ):
            result = showcase.playground(g["state"], g["questions"], consent=True)
        self.assertEqual(result["response"]["answers"]["team"]["choice"], "finance")
        self.assertEqual(result["provenance"]["kind"], "live_typesafe")
        self.assertEqual(result["request_hash"], engine.digest(result["request"]))
        self.assertIn("No policy", result["warning"])


class CompareTests(unittest.TestCase):
    def test_replay_compare_adds_side_by_side_rows_and_labels(self):
        report = showcase.compare(["replay"], ["S01", "S04"], consent=False)
        self.assertEqual(report["cases"], ["S01", "S04"])
        self.assertEqual(report["expected_owner"], {"S01": "operations", "S04": "quality"})
        arm = report["arms"][0]
        rows = {row["case_id"]: row for row in arm["cases"]}
        self.assertEqual(rows["S04"]["answers"]["owner"], "operations")
        self.assertIsNone(rows["S04"]["latency_ms"])
        self.assertFalse(report["ranked"])

    def test_live_arm_requires_consent_before_any_call(self):
        with patch("jev_lab.provider.live") as live, self.assertRaises(PermissionError):
            showcase.compare(["native"], ["S01"], consent=False)
        self.assertEqual(live.call_count, 0)

    def test_unknown_arm_is_rejected(self):
        with self.assertRaises(ValueError):
            showcase.compare(["replay", "mystery"], ["S01"], consent=False)

    def test_missing_claude_sdk_does_not_hold_native_slots(self):
        env = {**LIVE_ENV, "ANTHROPIC_API_KEY": "test-only-not-real"}
        native_budget = provider.CallBudget(20)
        claude_budget = provider.CallBudget(20)
        with (
            patch.dict(os.environ, env),
            patch("jev_lab.llm_arm.sdk_available", return_value=False),
            patch.object(provider, "BUDGET", native_budget),
            patch.object(llm_arm, "BUDGET", claude_budget),
            self.assertRaises(PermissionError),
        ):
            showcase.prepare_arms(["native", "claude"], 4, consent=True)
        self.assertEqual(native_budget.used, 0)
        self.assertEqual(claude_budget.used, 0)


if __name__ == "__main__":
    unittest.main()
