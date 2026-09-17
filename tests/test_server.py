import json
import threading
import unittest
import urllib.error
import urllib.request

try:
    from jev_lab import server
except ImportError:
    server = None


class ServerExists(unittest.TestCase):
    def test_server_implemented(self):
        self.assertIsNotNone(server)


@unittest.skipIf(server is None, "server pending")
class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = server.make_server(0)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.http.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=2)

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as r:
            return json.load(r)

    def post(self, path, body, token=None, origin=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Lab-Token"] = token
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(
            self.base + path, data=json.dumps(body).encode(), headers=headers
        )
        with urllib.request.urlopen(req) as r:
            return json.load(r)

    def token(self):
        return self.get("/api/config")["session_token"]

    def test_token_required(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post("/api/run", {"case_id": "S01"})
        self.assertEqual(e.exception.code, 403)

    def test_cross_origin_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post("/api/run", {"case_id": "S01"}, self.token(), "https://evil.example")
        self.assertEqual(e.exception.code, 403)

    def test_replay_reconsider(self):
        t = self.token()
        r = self.post("/api/run", {"case_id": "S02"}, t)
        s = self.post(
            "/api/reconsider",
            {"receipt_id": r["receipt_id"], "threshold": 0.99, "variant": "stale"},
            t,
        )
        self.assertEqual(s["decision"]["route"], "REFRESH_EVIDENCE")
        self.assertEqual(s["additional_model_calls"], 0)

    def test_fabricated_receipt_not_accepted(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.post("/api/reconsider", {"receipt_id": "fake", "threshold": 0.8}, self.token())

    def test_config_no_key(self):
        self.assertNotIn("TYPESAFE_API_KEY", json.dumps(self.get("/api/config")))

    def test_no_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.base + "/../data/labels.json")

    def test_synthetic_eval(self):
        r = self.post("/api/evaluate", {}, self.token())
        self.assertEqual(r["overall"]["n"], 12)
        self.assertEqual(r["provenance"], "synthetic_replay")

    def test_action_preview_hold(self):
        t = self.token()
        r = self.post("/api/run", {"case_id": "S02"}, t)
        p = self.post("/api/action-preview", {"receipt_id": r["receipt_id"], "current": {}}, t)
        self.assertEqual(p["result"], "HOLD")
        self.assertEqual(p["external_actions"], 0)

    def test_garden(self):
        r = self.post(
            "/api/garden",
            {"task": "calculate", "allow_cloud": False, "consequence_high": True},
            self.token(),
        )
        self.assertEqual(r["lane"], "deterministic")

    def test_arbitrary_state_cannot_be_sent(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.post("/api/run", {"case_id": "S02", "state": "client confidential"}, self.token())


@unittest.skipIf(server is None, "server pending")
class ShowcaseEndpointTests(ServerTests):
    def test_burst_replay_stores_receipts(self):
        r = self.post("/api/burst", {"mode": "replay"}, self.token())
        self.assertEqual(r["summary"]["succeeded"], 12)
        self.assertEqual(r["kind"], "synthetic_replay")
        first = r["results"][0]
        self.assertIn("receipt_id", first)
        self.assertNotIn("receipt", first)
        self.assertEqual(first["route"], "HUMAN_REVIEW")

    def test_burst_live_unconfigured_is_403_not_replay(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post("/api/burst", {"mode": "live", "consent": True}, self.token())
        self.assertEqual(e.exception.code, 403)

    def test_playground_unconfigured_is_403(self):
        body = {
            "state": "synthetic text",
            "questions": {"q": {"type": "noul", "instructions": "Is it fine?"}},
            "consent": True,
        }
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post("/api/playground", body, self.token())
        self.assertEqual(e.exception.code, 403)

    def test_playground_bad_shape_is_400(self):
        body = {
            "state": "synthetic text",
            "questions": {"q": {"type": "essay", "instructions": "x"}},
            "consent": True,
        }
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post("/api/playground", body, self.token())
        self.assertEqual(e.exception.code, 400)

    def test_compare_replay_arm(self):
        r = self.post(
            "/api/compare", {"arms": ["replay"], "case_ids": ["S01", "S02"]}, self.token()
        )
        self.assertEqual([a["name"] for a in r["arms"]], ["replay"])
        self.assertEqual(r["expected_owner"]["S01"], "operations")

    def test_config_reports_compare_state_without_secrets(self):
        c = self.get("/api/config")
        self.assertIn("compare_enabled", c)
        self.assertIn("compare_model", c)
        self.assertNotIn("ANTHROPIC_API_KEY", json.dumps(c))

    def test_favicon_ico_is_served(self):
        with urllib.request.urlopen(self.base + "/favicon.ico") as r:
            self.assertEqual(r.headers["Content-Type"], "image/svg+xml")

    def test_receipt_lookup_returns_the_stored_run(self):
        t = self.token()
        r = self.post("/api/run", {"case_id": "S02"}, t)
        looked = self.post("/api/receipt", {"receipt_id": r["receipt_id"]}, t)
        self.assertEqual(looked["case_id"], "S02")
        self.assertEqual(looked["receipt_id"], r["receipt_id"])
        self.assertEqual(looked["receipt_hash"], r["receipt_hash"])

    def test_favicon_served(self):
        with urllib.request.urlopen(self.base + "/favicon.svg") as r:
            self.assertEqual(r.headers["Content-Type"], "image/svg+xml")

    def test_live_stylesheet_is_served(self):
        with urllib.request.urlopen(self.base + "/live.css") as r:
            self.assertEqual(r.headers["Content-Type"], "text/css; charset=utf-8")

    def test_live_script_is_served(self):
        with urllib.request.urlopen(self.base + "/live.js") as r:
            self.assertEqual(r.headers["Content-Type"], "text/javascript; charset=utf-8")

    def test_unknown_receipt_is_400(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post("/api/receipt", {"receipt_id": "missing"}, self.token())
        self.assertEqual(caught.exception.code, 400)

    def test_cases_include_teaching_notes(self):
        payload = self.get("/api/cases")
        s04 = next(c for c in payload["cases"] if c["id"] == "S04")
        self.assertTrue(s04["planted_error"])
        self.assertIn("wrong", s04["teaching_note"].lower())
        config = self.get("/api/config")
        self.assertIn("rules", config["arms"])
        self.assertEqual(config["lab_version"], "0.3.1")
        self.assertEqual(config["http_body_limit"], 16384)
