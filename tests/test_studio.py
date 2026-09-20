"""Decision Studio is an experiment designer, never authored model evidence."""

import copy
import json
import unittest
from unittest.mock import patch

from jev_lab import engine, showcase

try:
    from jev_lab import economics, studio
except ImportError:
    economics = studio = None


class StudioTests(unittest.TestCase):
    def test_implementation_exists(self):
        self.assertIsNotNone(studio)

    @unittest.skipIf(studio is None, "implementation pending")
    def test_all_sixteen_previews_are_valid_and_offline(self):
        with patch("jev_lab.provider.live") as live:
            patterns = studio.catalog()
            self.assertEqual(len(patterns), 8)
            for p in patterns:
                for variant in ("routine", "adverse"):
                    with self.subTest(pattern=p["id"], variant=variant):
                        preview = studio.preview(p["id"], variant)
                        req = preview["request"]
                        self.assertEqual(set(req), {"model", "state", "questions"})
                        self.assertEqual(
                            req, showcase.playground_request(req["state"], req["questions"])
                        )
                        self.assertEqual(preview["model_calls"], 0)
                        self.assertIsNone(preview["response"])
                        self.assertEqual(preview["request_hash"], engine.digest(req))
                        for key in ("expected", "teaching_note", "label", "policy_facts"):
                            self.assertNotIn(key, req)
            live.assert_not_called()

    @unittest.skipIf(studio is None, "implementation pending")
    def test_invalid_pattern_and_variant_rejected(self):
        for pattern, variant in (
            ("../provider", "routine"),
            ("citation", "live"),
            (None, "routine"),
        ):
            with self.subTest(pattern=pattern), self.assertRaises(ValueError):
                studio.preview(pattern, variant)

    @unittest.skipIf(studio is None, "implementation pending")
    def test_catalog_is_detached(self):
        c = studio.catalog()
        c[0]["name"] = "tampered"
        self.assertNotEqual(studio.catalog()[0]["name"], "tampered")

    @unittest.skipIf(studio is None, "implementation pending")
    def test_extraction_candidates_are_verbatim_source_spans(self):
        p = studio.preview("extraction", "adverse")
        state = json.loads(p["request"]["state"])
        for candidate in state["candidates"].values():
            self.assertEqual(
                state["text"][candidate["start"] : candidate["end"]], candidate["text"]
            )
        self.assertIn("none", p["request"]["questions"]["selection"]["criteria"])

    @unittest.skipIf(studio is None, "implementation pending")
    def test_study_is_a_plan_not_a_result(self):
        for p in studio.catalog():
            plan = studio.study(p["id"])
            self.assertEqual(plan["status"], "UNRUN")
            self.assertIsNone(plan["results"])
            self.assertIn("held_out", plan)
            self.assertIn("falsifier", plan)
            self.assertGreaterEqual(len(plan["baselines"]), 3)
            self.assertIn("human_review_minutes", plan["measurements"])

    @unittest.skipIf(studio is None, "implementation pending")
    def test_live_uses_existing_explicit_consent_path(self):
        with patch(
            "jev_lab.studio.showcase.playground", side_effect=PermissionError("consent")
        ) as live:
            with self.assertRaises(PermissionError):
                studio.run("citation", "routine", False)
            self.assertFalse(live.call_args.args[2])


class EconomicsTests(unittest.TestCase):
    def test_implementation_exists(self):
        self.assertIsNotNone(economics)

    @unittest.skipIf(economics is None, "implementation pending")
    def test_case_conservation_and_all_attempt_billing(self):
        a = copy.deepcopy(economics.DEFAULTS)
        a.update(volume=100, failure_rate=0.2, auto_share=0.75, model_cost_per_attempt=0.01)
        r = economics.calculate(a)
        self.assertEqual(
            r["cases"], {"attempted": 100, "failed": 20, "automated": 60, "reviewed": 40}
        )
        self.assertEqual(r["costs"]["model"], 1)
        self.assertEqual(r["kind"], "assumption_only")
        self.assertEqual(a["volume"], 100)

    @unittest.skipIf(economics is None, "implementation pending")
    def test_review_is_not_assumed_perfect(self):
        a = dict(economics.DEFAULTS, volume=100, auto_share=0, reviewer_error_rate=0.1)
        r = economics.calculate(a)
        self.assertEqual(r["errors"]["reviewed"], 10)
        self.assertEqual(r["errors"]["automated"], 0)
        self.assertIsNone(r["break_even_auto_error_rate"])

    @unittest.skipIf(economics is None, "implementation pending")
    def test_capacity_is_not_savings(self):
        r = economics.calculate(dict(economics.DEFAULTS, review_capacity_hours=0))
        self.assertFalse(r["capacity"]["feasible"])
        self.assertGreater(r["capacity"]["shortfall_hours"], 0)
        self.assertEqual(r["status"], "REVIEW_CAPACITY_SHORTFALL")

    @unittest.skipIf(economics is None, "implementation pending")
    def test_strict_numeric_input_and_complete_schema(self):
        for key, value in (
            ("failure_rate", True),
            ("failure_rate", "0.1"),
            ("auto_share", float("nan")),
            ("volume", 1.5),
            ("hourly_cost", float("inf")),
            ("auto_error_rate", 1.01),
            ("error_loss", -1),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                economics.calculate(dict(economics.DEFAULTS, **{key: value}))
        for a in ({}, dict(economics.DEFAULTS, unknown=1)):
            with self.assertRaises(ValueError):
                economics.calculate(a)

    @unittest.skipIf(economics is None, "implementation pending")
    def test_zero_loss_extremes_and_sensitivity(self):
        a = dict(economics.DEFAULTS, failure_rate=1, error_loss=0)
        before = copy.deepcopy(a)
        r = economics.calculate(a)
        self.assertEqual(r["cases"]["automated"], 0)
        self.assertIsNone(r["break_even_auto_error_rate"])
        self.assertEqual(len(r["sensitivity"]), 4)
        self.assertEqual(a, before)
        json.dumps(r, allow_nan=False)
