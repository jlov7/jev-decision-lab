import unittest

from jev_lab import adapters, engine, showcase


class RulesArmTests(unittest.TestCase):
    def test_registry_builds_rules(self):
        arm = adapters.build("rules")
        self.assertEqual((arm.name, arm.kind, arm.live), ("rules", "deterministic_rules", False))

    def test_s02_delay_keyword_over_escalates_to_operations(self):
        case = engine.case_by_id("S02")
        result = adapters.build("rules").call(engine.request_for(case), "S02")
        self.assertEqual(result["normalized"]["records"]["owner"]["answer"], "operations")
        self.assertEqual(result["normalized"]["records"]["issue"]["answer"], "delivery")
        self.assertIsNone(result["normalized"]["records"]["owner"]["distribution"])
        self.assertEqual(result["provenance"]["model_calls"], 0)

    def test_s04_specification_words_select_quality(self):
        case = engine.case_by_id("S04")
        result = adapters.build("rules").call(engine.request_for(case), "S04")
        self.assertEqual(result["normalized"]["records"]["owner"]["answer"], "quality")
        self.assertEqual(result["normalized"]["records"]["issue"]["answer"], "quality")

    def test_no_distribution_is_fabricated(self):
        case = engine.case_by_id("S02")
        records = adapters.build("rules").call(engine.request_for(case), "S02")["normalized"][
            "records"
        ]
        self.assertTrue(all(row["distribution"] is None for row in records.values()))


class PlantedCompareTests(unittest.TestCase):
    def test_compare_marks_s04_as_planted_error(self):
        report = showcase.compare(["replay", "rules"], ["S02", "S04"], consent=False)
        self.assertEqual(report["planted_error"]["S04"], True)
        self.assertEqual(report["planted_error"]["S02"], False)
        rows = {
            arm["name"]: {row["case_id"]: row for row in arm["cases"]} for arm in report["arms"]
        }
        self.assertEqual(rows["replay"]["S04"]["answers"]["owner"], "operations")
        self.assertEqual(rows["rules"]["S04"]["answers"]["owner"], "quality")
        self.assertEqual(rows["rules"]["S02"]["answers"]["owner"], "operations")
        self.assertTrue(any("planted" in w.lower() for w in report["warnings"]))
        replay = next(arm for arm in report["arms"] if arm["name"] == "replay")
        self.assertEqual(replay["tracks"]["comparable_distribution"]["metrics"]["n"], 1)


class PlaygroundSizeTests(unittest.TestCase):
    def test_oversized_playground_is_rejected_before_a_provider_call(self):
        questions = {
            f"q{i}": {
                "type": "noul",
                "instructions": "I" * 1500,
                "criteria": {"true": "T" * 200, "false": "F" * 200},
            }
            for i in range(8)
        }
        with self.assertRaises(ValueError) as caught:
            showcase.playground_request("S" * 6000, questions)
        self.assertIn("ceiling", str(caught.exception).lower())
