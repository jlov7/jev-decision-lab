import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from jev_lab import engine, provider


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            "os.environ", {"JEV_ALLOW_LIVE": "1", "TYPESAFE_API_KEY": "test-only-not-a-real-key"}
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.b = patch.object(provider, "BUDGET", provider.CallBudget(20))
        self.b.start()
        self.addCleanup(self.b.stop)
        self.payload = engine.request_for(engine.case_by_id("S02"))

    def test_headers_endpoint_usage(self):
        reply = provider.replay("S02")
        reply["model"] = "jev-1.13.0"
        reply["usage"] = {"input_tokens": 2000, "output_tokens": 100}
        connection = MagicMock()
        connection.__enter__.return_value.read.return_value = json.dumps(reply).encode()
        opener = MagicMock()
        opener.open.return_value = connection
        with patch("urllib.request.build_opener", return_value=opener):
            result, meta = provider.live(self.payload)
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, provider.ENDPOINT)
        self.assertEqual(req.get_header("Authorization"), "Bearer test-only-not-a-real-key")
        self.assertEqual(json.loads(req.data), self.payload)
        self.assertAlmostEqual(meta["estimated_cost_usd"], 0.000084)
        self.assertEqual(meta["kind"], "live_typesafe")
        self.assertEqual(provider.BUDGET.used, 1)

    def test_live_disabled(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(PermissionError):
            provider.live(self.payload)

    def test_hold_does_not_double_count_prepaid_live_calls(self):
        budget = provider.CallBudget(5)
        prepaid = budget.hold(2)
        self.assertEqual(budget.used, 2)
        prepaid.consume()
        prepaid.consume()
        self.assertEqual(budget.used, 2)
        with self.assertRaises(RuntimeError):
            prepaid.consume()
        b = provider.CallBudget(1)
        b.reserve()
        with self.assertRaises(RuntimeError):
            b.reserve()

    def test_invalid_budget(self):
        for n in [0, 101, True, "20"]:
            with self.assertRaises(ValueError):
                provider.CallBudget(n)

    def test_oversize_not_sent(self):
        self.payload["state"] = "x" * provider.MAX_INPUT_BYTES
        with patch("urllib.request.build_opener") as opener:
            with self.assertRaises(ValueError):
                provider.live(self.payload)
            opener.assert_not_called()
        self.assertEqual(provider.BUDGET.used, 0)

    def test_422_body_is_surfaced_without_retry(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError(
            provider.ENDPOINT, 422, "bad", {}, io.BytesIO(b'{"error":"questions.owner.criteria"}')
        )
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(RuntimeError) as e:
                provider.live(self.payload)
        self.assertIn("422", str(e.exception))
        self.assertIn("questions.owner.criteria", str(e.exception))
        self.assertEqual(opener.open.call_count, 1)

    def test_401_body_is_not_echoed(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError(
            provider.ENDPOINT, 401, "bad", {}, io.BytesIO(b"test-only-not-a-real-key")
        )
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(RuntimeError) as e:
                provider.live(self.payload)
        self.assertIn("401", str(e.exception))
        self.assertNotIn("test-only", str(e.exception))
        self.assertEqual(opener.open.call_count, 1)

    def test_timeout_no_fallback(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError()
        with (
            patch("urllib.request.build_opener", return_value=opener),
            patch.object(provider, "replay") as fallback,
        ):
            with self.assertRaises(RuntimeError):
                provider.live(self.payload)
            fallback.assert_not_called()

    def test_no_redirect(self):
        self.assertIsNone(
            provider.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")
        )

    def test_invalid_json(self):
        connection = MagicMock()
        connection.__enter__.return_value.read.return_value = b"not json"
        opener = MagicMock()
        opener.open.return_value = connection
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ValueError):
                provider.live(self.payload)

    def test_inconsistent_heads(self):
        r = provider.replay("T03")
        a = r["answers"]["next_evidence"]
        a["choice"] = "none"
        a["probabilities"] = {k: float(k == "none") for k in a["probabilities"]}
        self.assertEqual(engine.decide(engine.case_by_id("T03"), r)["route"], "HUMAN_REVIEW")
