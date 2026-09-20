import copy
import unittest
from unittest.mock import patch

from jev_lab import adapters, comparator, economics, engine, evidence, metrics, probes


class CohortTests(unittest.TestCase):
    def test_duplicate_cases_cannot_inflate_calibration_sample(self):
        a = engine.run("S01")
        with self.assertRaisesRegex(ValueError, "Repeated|Duplicate|duplicate"):
            metrics.evaluate([a, copy.deepcopy(a)], engine.load("labels"))

    def test_large_out_of_range_integers_are_validation_errors(self):
        with self.assertRaises(ValueError):
            economics.calculate(dict(economics.DEFAULTS, volume=10**500))
        with self.assertRaises(ValueError):
            engine.number(10**500)

    def test_comparison_retains_audit_records_and_common_denominator(self):
        class PartlyFailed:
            name, kind, live, pinned_version, live_verified = (
                "partial",
                "synthetic_replay",
                False,
                "fixture",
                False,
            )

            def call(self, request, case_id=None):
                if case_id == "S02":
                    raise RuntimeError("fixture timeout")
                return adapters.build("replay").call(request, case_id)

        r = comparator.compare(["S01", "S02"], [adapters.build("replay"), PartlyFailed()])
        self.assertEqual(r["paired"]["case_ids"], ["S01"])
        self.assertEqual(r["paired"]["requested"], 2)
        for arm in r["arms"]:
            row = arm["cases"][0]
            self.assertIn("task_request", row)
            self.assertIn("provider_response", row)
            record = {k: v for k, v in row.items() if k != "record_hash"}
            self.assertEqual(row["record_hash"], engine.digest(record))
            self.assertEqual(arm["paired_owner_agreement"]["denominator"], 1)

    def test_cost_bases_have_separate_subtotals(self):
        r = evidence.costs(
            [
                {"estimated_cost_usd": 1, "billing": "api"},
                {"estimated_cost_usd": 2, "billing": "subscription"},
            ]
        )
        self.assertIsNone(r["total_cost_usd"])
        self.assertEqual(r["by_billing_basis"], {"api": 1, "subscription": 2})

    def test_ablation_reference_does_not_cross_model_versions(self):
        probes.MEASURED_RANGE.clear()
        self.addCleanup(probes.MEASURED_RANGE.clear)
        a, b = engine.run("S02"), engine.run("S02")
        for x in (a, b):
            x["provenance"]["kind"] = "live_typesafe"
            x["response"]["model"] = "version-a"
        b["response"]["answers"]["sufficient"]["noul"] = 0.2
        with (
            patch.object(probes, "_hold"),
            patch.object(
                probes, "_run_many", return_value=[{"ok": True, "receipt": x} for x in (a, b)]
            ),
        ):
            probes.probe("S02", 2, mode="live", consent=True)
        changed = copy.deepcopy(a)
        changed["response"]["model"] = "version-b"
        with (
            patch.object(probes, "_hold"),
            patch.object(probes, "_run_many", return_value=[{"ok": True, "receipt": changed}] * 3),
        ):
            r = probes.ablate("S02", mode="live", consent=True)
        self.assertEqual(r["noise_floor"], probes.NOISE_FLOOR)
