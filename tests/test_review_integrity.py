"""Regression tests for errors ordinary happy-path tests did not catch."""

import copy
import unittest
from unittest.mock import patch

from jev_lab import adapters, comparator, engine, metrics, probes, showcase


class IntegrityTests(unittest.TestCase):
    def test_mixed_returned_models_are_not_pooled(self):
        rows = [engine.run("S01"), engine.run("S02")]
        rows[1]["response"]["model"] = "different-version"
        with self.assertRaisesRegex(ValueError, "version|model"):
            metrics.evaluate(rows, engine.load("labels"))

    def test_mixed_question_contracts_are_not_pooled(self):
        rows = [engine.run("S01"), engine.run("S02")]
        rows[1]["question_version"] = "changed-contract"
        with self.assertRaisesRegex(ValueError, "contract|question"):
            metrics.evaluate(rows, engine.load("labels"))

    def test_no_successful_probe_is_not_stable(self):
        failed = [{"ok": False, "error": "timeout"}] * 3
        with patch.object(probes, "_run_many", return_value=failed):
            r = probes.probe("S02", 3)
        self.assertIsNone(r["route_stable"])
        self.assertFalse(r["complete"])

    def test_partial_probe_is_not_stable_or_fully_priced(self):
        r = engine.run("S02")
        r["provenance"]["estimated_cost_usd"] = 0.01
        results = [{"ok": True, "receipt": r}, {"ok": False, "error": "timeout"}]
        with patch.object(probes, "_run_many", return_value=results):
            value = probes.probe("S02", 2)
        self.assertIsNone(value["route_stable"])
        self.assertIsNone(value["estimated_cost_usd"])

    def test_probe_retains_but_does_not_pool_version_drift(self):
        a, b = engine.run("S02"), engine.run("S02")
        b["response"]["model"] = "changed"
        with patch.object(
            probes, "_run_many", return_value=[{"ok": True, "receipt": x} for x in (a, b)]
        ):
            r = probes.probe("S02", 2)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["spread"], {})
        self.assertEqual(len(r["receipts"]), 2)

    def test_noul_is_in_widest_probability_range(self):
        a, b = engine.run("S02"), engine.run("S02")
        b["response"]["answers"]["sufficient"]["noul"] = 0.1
        with patch.object(
            probes, "_run_many", return_value=[{"ok": True, "receipt": x} for x in (a, b)]
        ):
            r = probes.probe("S02", 2)
        self.assertEqual(r["widest_option_range"]["question"], "sufficient")

    def test_ablation_tracks_the_baseline_owner_not_a_new_argmax(self):
        a = engine.run("S02")
        b = copy.deepcopy(a)
        owner = a["response"]["answers"]["owner"]["choice"]
        other = next(k for k in a["response"]["answers"]["owner"]["probabilities"] if k != owner)
        b["response"]["answers"]["owner"]["choice"] = other
        b["response"]["answers"]["owner"]["probabilities"] = {
            k: (0.9 if k == other else 0.1 if k == owner else 0)
            for k in a["response"]["answers"]["owner"]["probabilities"]
        }
        results = [{"ok": True, "receipt": x} for x in (a, b, a)]
        with patch.object(probes, "_run_many", return_value=results):
            r = probes.ablate("S02")
        expected = 0.1 - a["response"]["answers"]["owner"]["probabilities"][owner]
        self.assertAlmostEqual(r["variants"][1]["deltas"]["owner_probability"], expected)
        self.assertEqual(r["variants"][1]["delta_owner_label"], owner)

    def test_known_failed_call_cost_is_retained_in_summary(self):
        class Invalid:
            name, kind, live, pinned_version, live_verified = (
                "invalid",
                "live_typesafe",
                True,
                "test",
                False,
            )

            def call(self, request, case_id=None):
                raise engine.LiveValidationError(
                    "invalid wire response",
                    {"model": "test"},
                    {"estimated_cost_usd": 0.02, "billing": "api"},
                )

        r = comparator.compare(["S01", "S02"], [Invalid()])["arms"][0]
        self.assertAlmostEqual(r["cost_summary"]["total_cost_usd"], 0.04)
        self.assertEqual(r["cost_summary"]["attempts"], 2)

    def test_live_s04_is_not_excluded_as_a_planted_replay(self):
        class LiveLike:
            name, kind, live, pinned_version, live_verified = (
                "test",
                "live_typesafe",
                True,
                "test",
                False,
            )

            def call(self, request, case_id=None):
                value = adapters.build("replay").call(request, case_id)
                value["provenance"]["kind"] = "live_typesafe"
                return value

        r = comparator.compare(["S04"], [LiveLike()])["arms"][0]
        self.assertTrue(r["tracks"]["comparable_distribution"]["available"])
        self.assertEqual(r["tracks"]["comparable_distribution"]["metrics"]["n"], 1)

    def test_duplicate_arms_rejected_before_build_or_budget(self):
        with patch.object(adapters, "build") as build:
            with self.assertRaises(ValueError):
                showcase.prepare_arms(["replay", "replay"], 2)
        build.assert_not_called()
