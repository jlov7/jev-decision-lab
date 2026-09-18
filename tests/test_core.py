import copy
import json
import os
import unittest
from unittest.mock import patch

try:
    from jev_lab import engine, metrics, provider, strategy
except ImportError:
    engine = provider = metrics = strategy = None


class ImplementationExists(unittest.TestCase):
    def test_required_modules_exist(self):
        self.assertIsNotNone(engine, "Recovered implementation must be present and importable")


@unittest.skipIf(engine is None, "implementation pending")
class ContractTests(unittest.TestCase):
    def setUp(self):
        self.case = engine.case_by_id("S02")
        self.request = engine.request_for(self.case)
        self.response = provider.replay("S02")

    def test_contract(self):
        self.assertEqual(engine.validate(self.request, self.response), self.response)

    def test_all_cases(self):
        self.assertEqual(len(engine.cases()), 12)
        for c in engine.cases():
            self.assertEqual(len(engine.run(c["id"])["response"]["answers"]), 6)

    def test_no_gold_leak(self):
        self.case["expected_owner"] = "injected"
        self.case["teaching_note"] = "hidden"
        self.assertNotIn("expected_owner", json.dumps(engine.request_for(self.case)))
        self.assertNotIn("teaching_note", json.dumps(engine.request_for(self.case)))

    def test_model_identity_required(self):
        self.response.pop("model")
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_pinned_model_mismatch_rejected(self):
        self.response["model"] = "jev-other"
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response, live=True)

    def test_answer_ids_exact(self):
        self.response["answers"]["extra"] = {"type": "noul", "noul": 0.5}
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_answer_type_exact(self):
        self.response["answers"]["owner"]["type"] = "noul"
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_probability_sum(self):
        self.response["answers"]["owner"]["probabilities"]["operations"] = 0.1
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_options_exact(self):
        self.response["answers"]["owner"]["probabilities"]["invented"] = 0.0
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_argmax(self):
        self.response["answers"]["owner"]["choice"] = "quality"
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_bad_numbers(self):
        for value in [float("nan"), float("inf"), True, -0.1, 1.1, "0.9", None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                engine.number(value)

    def test_score_mean(self):
        self.response["answers"]["severity"]["score"] = 2
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_missing_score_distribution(self):
        self.response["answers"]["severity"].pop("probabilities")
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_score_legend(self):
        self.response["answers"]["severity"]["legend"]["0"] = "wrong"
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_negative_usage(self):
        self.response["usage"]["input_tokens"] = -1
        with self.assertRaises(ValueError):
            engine.validate(self.request, self.response)

    def test_noul_no_confidence(self):
        self.assertNotIn("confidence", self.response["answers"]["sufficient"])

    def test_case_unknown(self):
        with self.assertRaises(ValueError):
            engine.run("UNKNOWN")

    def test_mode_unknown(self):
        with self.assertRaises(ValueError):
            engine.run("S02", "fake-live")


@unittest.skipIf(engine is None, "implementation pending")
class PolicyTests(unittest.TestCase):
    def test_replay_no_network(self):
        with patch("urllib.request.build_opener") as opener:
            r = engine.run("S02")
            opener.assert_not_called()
        self.assertEqual(r["provenance"]["kind"], "synthetic_replay")
        self.assertIsNone(r["provenance"]["latency_ms"])
        self.assertIsNone(r["provenance"]["estimated_cost_usd"])
        self.assertEqual(r["provenance"]["model_calls"], 0)

    def test_consent_required(self):
        with self.assertRaises(PermissionError):
            engine.run("S02", "live", consent=False)

    def test_boolean_consent_not_string(self):
        with self.assertRaises(PermissionError):
            engine.run("S02", "live", consent="true")

    def test_live_disabled_reported_before_consent(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PermissionError) as caught:
                engine.run("S02", "live", consent=True)
            self.assertIn("Live mode disabled", str(caught.exception))
            with self.assertRaises(PermissionError) as caught:
                engine.run("S02", "live", consent=False)
            self.assertIn("Live mode disabled", str(caught.exception))

    def test_critical_reads_top_severity_level(self):
        case = engine.case_by_id("S01")
        response = copy.deepcopy(engine.run("S01")["response"])
        sev = response["answers"]["severity"]
        sev["probabilities"] = {"0": 0.1, "1": 0.1, "2": 0.1, "3": 0.1, "4": 0.6}
        sev["legend"] = {str(i): f"level {i}" for i in range(5)}
        sev["score"] = 3.0
        self.assertEqual(engine.decide(case, response)["critical_probability"], 0.6)
        sev["probabilities"] = {"0": 0.2, "1": 0.3, "2": 0.5}
        sev["legend"] = {str(i): f"level {i}" for i in range(3)}
        sev["score"] = 1.3
        self.assertEqual(engine.decide(case, response)["critical_probability"], 0.5)

    def test_stale_overrides(self):
        r = engine.reconsider(engine.run("S02"), 0.5, "stale")
        self.assertEqual(r["decision"]["route"], "REFRESH_EVIDENCE")

    def test_unverified_overrides(self):
        r = engine.reconsider(engine.run("S02"), 0.5, "unverified")
        self.assertEqual(r["decision"]["route"], "VERIFY_SOURCE")

    def test_critical_before_repair(self):
        self.assertEqual(engine.run("S01")["decision"]["route"], "HUMAN_REVIEW")

    def test_mandatory(self):
        self.assertEqual(engine.run("S03")["decision"]["route"], "HUMAN_REVIEW")

    def test_conflict_requests_evidence(self):
        self.assertEqual(engine.run("T03")["decision"]["route"], "REQUEST_EVIDENCE")

    def test_threshold(self):
        self.assertEqual(engine.run("S02", threshold=0.99)["decision"]["route"], "HUMAN_REVIEW")

    def test_replay_no_extra_call(self):
        r = engine.run("S02")
        with patch("jev_lab.provider.live") as live:
            r2 = engine.reconsider(r, 0.99)
            live.assert_not_called()
        self.assertEqual(r["response"], r2["response"])
        self.assertEqual(r2["additional_model_calls"], 0)

    def test_hash_and_tamper(self):
        r = engine.run("S02")
        h = r.pop("receipt_hash")
        self.assertEqual(engine.digest(r), h)
        r["decision"]["route"] = "OTHER"
        self.assertNotEqual(engine.digest(r), h)

    def test_tampered_reconsider_rejected(self):
        r = engine.run("S02")
        r["decision"]["route"] = "OTHER"
        with self.assertRaises(ValueError):
            engine.reconsider(r, 0.8)

    def test_unknown_variant(self):
        with self.assertRaises(ValueError):
            engine.reconsider(engine.run("S02"), 0.8, "invented")

    def test_s04_default_still_routes_to_the_wrong_team(self):
        r = engine.run("S04")
        self.assertEqual(r["decision"]["route"], "ROUTE_TO_TEAM")
        self.assertEqual(r["decision"]["inconsistencies"][0]["kind"], "issue_owner_mismatch")

    def test_strict_heads_hold_s04_without_another_model_call(self):
        r = engine.reconsider(engine.run("S04"), 0.5, "strict")
        self.assertEqual(r["decision"]["route"], "HUMAN_REVIEW")
        self.assertEqual(r["additional_model_calls"], 0)
        r = engine.run("S04")
        a = r["response"]["answers"]["owner"]
        self.assertGreater(a["probabilities"][a["choice"]], 0.95)
        self.assertNotEqual(a["choice"], engine.load("labels")["S04"]["expected_owner"])

    def test_policy_metadata_not_in_model_request(self):
        self.assertNotIn(
            "mandatory_review", json.dumps(engine.request_for(engine.case_by_id("S02")))
        )


@unittest.skipIf(engine is None, "implementation pending")
class BeforeActionTests(unittest.TestCase):
    def setUp(self):
        self.receipt = engine.run("S02")
        self.current = {
            "state_unchanged": True,
            "source_fresh": True,
            "approval_current": True,
            "permission_granted": True,
        }

    def test_allowed_is_simulation_only(self):
        r = strategy.action_preview(self.receipt, self.current)
        self.assertEqual(r["result"], "SIMULATED_RECOMMENDATION")
        self.assertEqual(r["external_actions"], 0)

    def test_each_false_blocks(self):
        for key in self.current:
            c = dict(self.current)
            c[key] = False
            with self.subTest(key=key):
                self.assertEqual(strategy.action_preview(self.receipt, c)["result"], "HOLD")

    def test_missing_is_not_permission(self):
        self.current.pop("permission_granted")
        self.assertEqual(strategy.action_preview(self.receipt, self.current)["result"], "HOLD")

    def test_truthy_string_not_permission(self):
        self.current["permission_granted"] = "yes"
        with self.assertRaises(ValueError):
            strategy.action_preview(self.receipt, self.current)

    def test_prior_hold_cannot_be_overridden(self):
        self.assertEqual(strategy.action_preview(engine.run("S03"), self.current)["result"], "HOLD")

    def test_tampered_receipt(self):
        self.receipt["case_id"] = "S01"
        with self.assertRaises(ValueError):
            strategy.action_preview(self.receipt, self.current)

    def test_garden_numeric_uses_code(self):
        self.assertEqual(strategy.garden("calculate", True, False)["lane"], "deterministic")

    def test_garden_judgment_local_constraint(self):
        r = strategy.garden("classify", False, False)
        self.assertFalse(r["hosted_jev_eligible"])

    def test_garden_unknown_no_default(self):
        with self.assertRaises(ValueError):
            strategy.garden("unknown", True, False)


@unittest.skipIf(engine is None, "implementation pending")
class MetricsTests(unittest.TestCase):
    def test_perfect(self):
        m = metrics.classification([({"a": 1.0, "b": 0.0}, "a")])
        self.assertEqual(m["brier"], 0)
        self.assertEqual(m["ece_10"], 0)

    def test_brier(self):
        self.assertAlmostEqual(
            metrics.classification([({"a": 0.75, "b": 0.25}, "a")])["brier"], 0.125
        )

    def test_empty(self):
        self.assertIsNone(metrics.classification([])["accuracy"])

    def test_no_coverage_is_not_no_error(self):
        self.assertIsNone(
            metrics.classification([({"a": 0.7, "b": 0.3}, "a")])["risk_coverage"][-1]["error_rate"]
        )

    def test_duplicate(self):
        r = engine.run("S02")
        with self.assertRaises(ValueError):
            metrics.evaluate([r, r], engine.load("labels"))

    def test_mixed_provenance(self):
        a = engine.run("S01")
        b = engine.run("S02")
        b["provenance"]["kind"] = "live_typesafe"
        with self.assertRaises(ValueError):
            metrics.evaluate([a, b], engine.load("labels"))

    def test_unknown_gold(self):
        with self.assertRaises(ValueError):
            metrics.classification([({"a": 1.0}, "b")])
