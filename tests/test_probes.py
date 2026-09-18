import copy
import os
import threading
import unittest
from unittest.mock import patch

from jev_lab import engine, probes, provider

LIVE_ENV = {"JEV_ALLOW_LIVE": "1", "TYPESAFE_API_KEY": "test-key-not-real-0123456789"}
CALLS = {"n": 0}
COUNT_LOCK = threading.Lock()


def jittery(request, prepaid=None):
    """Fixture answers with a small, deterministic wobble on the owner head."""
    with COUNT_LOCK:
        CALLS["n"] += 1
        n = CALLS["n"]
    case_id = next(
        c["id"] for c in engine.cases() if c["state"]["message"] == request["state"]["message"]
    )
    response = copy.deepcopy(provider.replay(case_id))
    response["model"] = request["model"]
    response["usage"] = {"input_tokens": 500, "output_tokens": 40}
    owner = response["answers"]["owner"]
    top = owner["choice"]
    other = next(k for k in owner["probabilities"] if k != top)
    wobble = 0.01 * (n % 3)  # 0, 0.01, 0.02
    owner["probabilities"][top] = round(owner["probabilities"][top] - wobble, 4)
    owner["probabilities"][other] = round(owner["probabilities"][other] + wobble, 4)
    # ablation: fewer evidence items lowers sufficiency so the effect is visible
    dropped = 2 - len(request["state"]["evidence"])
    response["answers"]["sufficient"]["noul"] = round(
        max(0.0, response["answers"]["sufficient"]["noul"] - 0.2 * dropped), 4
    )
    provenance = {
        "kind": "live_typesafe",
        "model_calls": 1,
        "latency_ms": 100.0 + n,
        "usage": response["usage"],
        "estimated_cost_usd": 0.000021,
        "price_per_million_input_usd": provider.PRICE_PER_MILLION_INPUT,
        "price_as_of": "2026-09-17",
        "warning": "test",
    }
    return response, provenance


class ProbeTests(unittest.TestCase):
    def test_replay_probe_has_zero_range_and_says_so(self):
        result = probes.probe("S02", 3, mode="replay")
        self.assertEqual((result["succeeded"], result["failed"]), (3, 0))
        self.assertTrue(result["route_stable"])
        self.assertEqual(result["widest_option_range"]["range"], 0)
        self.assertIn("same authored fixture", result["warning"])
        self.assertIsNone(result["latency_ms"]["p50"])

    def test_repeats_are_bounded(self):
        for bad in (1, 9, 0, -2, True, 2.5, "4"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                probes.probe("S02", bad)

    def test_live_probe_reports_spread_and_holds_slots_first(self):
        CALLS["n"] = 0
        with (
            patch.dict(os.environ, LIVE_ENV),
            patch("jev_lab.provider.live", side_effect=jittery),
            patch.object(provider, "BUDGET", provider.CallBudget(50)),
        ):
            result = probes.probe("S02", 6, mode="live", consent=True)
            self.assertEqual(provider.BUDGET.used, 6)
        self.assertEqual(result["succeeded"], 6)
        owner = result["spread"]["owner"]
        self.assertEqual(owner["type"], "choice")
        self.assertAlmostEqual(owner["options"]["operations"]["range"], 0.02)
        self.assertEqual(result["widest_option_range"]["question"], "owner")
        self.assertEqual(result["spread"]["sufficient"]["value"]["range"], 0)
        self.assertEqual(sum(result["routes"].values()), 6)
        self.assertAlmostEqual(result["estimated_cost_usd"], 6 * 0.000021)
        self.assertIn("call-to-call variation", result["warning"])

    def test_live_probe_refuses_before_sending_without_slots_or_consent(self):
        with patch.dict(os.environ, LIVE_ENV), patch("jev_lab.provider.live") as live:
            with patch.object(provider, "BUDGET", provider.CallBudget(3)):
                with self.assertRaises(RuntimeError):
                    probes.probe("S02", 4, mode="live", consent=True)
            with self.assertRaises(PermissionError):
                probes.probe("S02", 2, mode="live", consent=False)
        self.assertEqual(live.call_count, 0)


class AblationTests(unittest.TestCase):
    def test_replay_ablation_runs_baseline_plus_one_per_evidence(self):
        result = probes.ablate("S02", mode="replay")
        self.assertEqual(result["requested"], 3)
        self.assertEqual([v["label"] for v in result["variants"]], ["baseline", "without S02-E1", "without S02-E2"])
        self.assertIsNone(result["most_influential"])
        self.assertTrue(all(v["deltas"]["sufficient"] == 0 for v in result["variants"][1:]))

    def test_variants_are_edited_copies_and_the_original_case_is_untouched(self):
        before = copy.deepcopy(engine.case_by_id("S02"))
        result = probes.ablate("S02", mode="replay")
        self.assertEqual(engine.case_by_id("S02"), before)
        sent = result["variants"][1]["receipt"]["request"]["state"]["evidence"]
        self.assertEqual([e["id"] for e in sent], ["S02-E2"])
        self.assertNotEqual(result["variants"][1]["receipt"]["case_hash"], result["variants"][0]["receipt"]["case_hash"])

    def test_live_ablation_marks_movement_above_the_noise_floor(self):
        CALLS["n"] = 0
        with (
            patch.dict(os.environ, LIVE_ENV),
            patch("jev_lab.provider.live", side_effect=jittery),
            patch.object(provider, "BUDGET", provider.CallBudget(50)),
        ):
            result = probes.ablate("S02", mode="live", consent=True)
            self.assertEqual(provider.BUDGET.used, 3)
        self.assertTrue(result["baseline_ok"])
        for v in result["variants"][1:]:
            self.assertAlmostEqual(v["deltas"]["sufficient"], -0.2)
            self.assertTrue(v["above_noise"])
        self.assertIn(result["most_influential"], {"S02-E1", "S02-E2"})

    def test_publish_swaps_receipts_for_ids(self):
        stored = []

        def store(receipt):
            stored.append(receipt)
            return dict(receipt, receipt_id=f"id{len(stored)}")

        result = probes.publish(probes.probe("S04", 2, mode="replay"), store)
        self.assertNotIn("receipts", result)
        self.assertEqual([r["receipt_id"] for r in result["rows"]], ["id1", "id2"])
        result = probes.publish(probes.ablate("S04", mode="replay"), store)
        self.assertTrue(all("receipt" not in v and v["receipt_id"] for v in result["variants"]))
        self.assertEqual(len(stored), 5)


if __name__ == "__main__":
    unittest.main()
