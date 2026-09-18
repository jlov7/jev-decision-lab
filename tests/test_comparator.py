import unittest

try:
    from jev_lab import adapters, comparator
except ImportError:
    comparator = None


class AlwaysFails:
    name, kind, live, pinned_version, live_verified = (
        "broken_arm",
        "live_broken",
        True,
        "v0",
        False,
    )
    tracks = ("minimal_decision", "comparable_distribution")

    def call(self, request, case_id=None):
        raise RuntimeError("transport refused; no fallback was used")


@unittest.skipIf(comparator is None, "comparator pending")
class ComparatorTests(unittest.TestCase):
    def arms(self):
        return [adapters.build("replay")]

    def test_replay_arm_is_evaluated_without_network(self):
        report = comparator.compare(["S01", "S02"], self.arms())
        arm = report["arms"][0]
        self.assertEqual((arm["attempts"], arm["succeeded"], arm["failed"]), (2, 2, 0))
        self.assertEqual(arm["failures"], [])

    def test_every_failure_is_retained_with_its_cost_uncertainty(self):
        report = comparator.compare(["S01", "S02"], [AlwaysFails()])
        arm = report["arms"][0]
        self.assertEqual((arm["attempts"], arm["succeeded"], arm["failed"]), (2, 0, 2))
        self.assertEqual(len(arm["failures"]), 2)
        self.assertEqual(sorted(f["case_id"] for f in arm["failures"]), ["S01", "S02"])
        self.assertTrue(all("no fallback" in f["error"].lower() for f in arm["failures"]))
        self.assertTrue(all(f["cost_unknown"] for f in arm["failures"]))

    def test_a_failing_arm_does_not_stop_the_other_arm(self):
        report = comparator.compare(["S01"], [AlwaysFails(), adapters.build("replay")])
        self.assertEqual(report["arms"][0]["failed"], 1)
        self.assertEqual(report["arms"][1]["succeeded"], 1)

    def test_arms_are_never_pooled_into_one_evaluation(self):
        report = comparator.compare(["S01", "S02"], [adapters.build("replay"), AlwaysFails()])
        for arm in report["arms"]:
            self.assertEqual(
                arm["tracks"]["comparable_distribution"]["pooled_with_other_arms"],
                False,
            )
        self.assertEqual({a["kind"] for a in report["arms"]}, {"synthetic_replay", "live_broken"})

    def test_replay_arm_supplies_distribution_metrics(self):
        track = comparator.compare(["S01", "S02"], self.arms())["arms"][0]["tracks"][
            "comparable_distribution"
        ]
        self.assertTrue(track["available"])
        self.assertEqual(track["metrics"]["n"], 2)
        self.assertIn("owner", track["metric_scope"])

    def test_planted_s04_is_not_scored_in_distribution_metrics(self):
        arm = comparator.compare(["S01", "S04"], self.arms())["arms"][0]
        self.assertEqual({row["case_id"] for row in arm["cases"]}, {"S01", "S04"})
        track = arm["tracks"]["comparable_distribution"]
        self.assertTrue(track["available"])
        self.assertEqual(track["metrics"]["n"], 1)

    def test_arm_without_distributions_reports_unavailable_not_zero(self):
        report = comparator.compare(["S01", "S02"], [AlwaysFails()])
        track = report["arms"][0]["tracks"]["comparable_distribution"]
        self.assertFalse(track["available"])
        self.assertIsNone(track["metrics"])
        self.assertTrue(track["reason"])

    def test_minimal_decision_track_is_reported_separately_from_distributions(self):
        arm = comparator.compare(["S01", "S02"], self.arms())["arms"][0]
        self.assertEqual(arm["tracks"]["minimal_decision"]["answered"], 2)
        self.assertEqual(set(arm["tracks"]), {"minimal_decision", "comparable_distribution"})

    def test_report_does_not_rank_arms_or_claim_accuracy(self):
        report = comparator.compare(["S01", "S02"], [adapters.build("replay")])
        self.assertFalse(report["ranked"])
        blob = str(report).lower()
        for forbidden in ("winner", "best arm", "outperforms"):
            self.assertNotIn(forbidden, blob)

    def test_report_records_verification_boundary(self):
        report = comparator.compare(["S01"], [adapters.build("native")])
        arm = report["arms"][0]
        self.assertFalse(arm["live_verified"])
        self.assertTrue(any("not" in w.lower() and "live" in w.lower() for w in report["warnings"]))

    def test_verified_live_arm_changes_the_live_warning(self):
        class VerifiedLive(AlwaysFails):
            name, kind, live_verified = "native_stub", "live_typesafe", True

            def call(self, request, case_id=None):
                result = adapters.build("replay").call(request, case_id)
                result["provenance"] = dict(result["provenance"], live_verified=True)
                return result

        report = comparator.compare(["S01", "S02"], [VerifiedLive(), adapters.build("replay")])
        by_name = {a["name"]: a for a in report["arms"]}
        self.assertTrue(by_name["native_stub"]["live_verified"])
        self.assertFalse(by_name["replay"]["live_verified"])
        live_warnings = [w for w in report["warnings"] if "authenticated" in w.lower()]
        self.assertEqual(len(live_warnings), 1)
        self.assertIn("native_stub", live_warnings[0])
        self.assertNotIn(comparator.NO_LIVE_WARNING, report["warnings"])

    def test_native_validation_failure_keeps_the_answer_and_its_cost(self):
        import copy
        import os
        from unittest.mock import patch

        from jev_lab import provider

        def malformed(request, prepaid=None):
            response = copy.deepcopy(provider.replay("S02"))
            response["model"] = request["model"]
            response["usage"] = {"input_tokens": 500, "output_tokens": 40}
            response["answers"]["owner"]["probabilities"]["operations"] = 0.5
            return response, {"kind": "live_typesafe", "model_calls": 1, "latency_ms": 90.0, "usage": response["usage"], "estimated_cost_usd": 0.000021}

        env = {"JEV_ALLOW_LIVE": "1", "TYPESAFE_API_KEY": "test-key-not-real-0123456789"}
        with patch.dict(os.environ, env), patch("jev_lab.provider.live", side_effect=malformed), patch.object(provider, "BUDGET", provider.CallBudget(5)):
            report = comparator.compare(["S02"], [adapters.build("native")])
        arm = report["arms"][0]
        self.assertEqual((arm["succeeded"], arm["failed"]), (0, 1))
        failure = arm["failures"][0]
        self.assertIn("sum to one", failure["error"])
        self.assertEqual(failure["provider_response"]["answers"]["owner"]["probabilities"]["operations"], 0.5)
        self.assertFalse(failure["cost_unknown"])
        self.assertAlmostEqual(failure["estimated_cost_usd"], 0.000021)

    def test_unknown_case_is_rejected_before_any_call(self):
        with self.assertRaises(ValueError):
            comparator.compare(["NOPE"], self.arms())

    def test_empty_arm_list_is_rejected(self):
        with self.assertRaises(ValueError):
            comparator.compare(["S01"], [])
