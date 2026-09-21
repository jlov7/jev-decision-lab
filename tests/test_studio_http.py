import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from jev_lab import economics, server


class StudioHTTPTests(unittest.TestCase):
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

    def request(self, path, body=None, token=True):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Lab-Token"] = server.TOKEN
        req = urllib.request.Request(
            self.base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req) as response:
            return json.load(response)

    def test_catalog_offline_and_economics_defaults(self):
        with patch("jev_lab.provider.live") as live:
            result = self.request("/api/studio")
            self.assertEqual(len(result["patterns"]), 8)
            self.assertEqual(result["economics_defaults"], economics.DEFAULTS)
            live.assert_not_called()

    def test_preview_and_study_are_offline(self):
        with patch("jev_lab.provider.live") as live:
            preview = self.request(
                "/api/studio-preview", {"pattern_id": "citation", "variant": "adverse"}
            )
            self.assertEqual(preview["model_calls"], 0)
            self.assertFalse(preview["code_checks"][0]["result"])
            plan = self.request("/api/studio-study", {"pattern_id": "citation"})
            self.assertEqual(plan["status"], "UNRUN")
            live.assert_not_called()

    def test_economics_requires_token_and_rejects_extra_fields(self):
        body = {"assumptions": economics.DEFAULTS}
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.request("/api/economics", body, False)
        self.assertEqual(err.exception.code, 403)
        self.assertEqual(self.request("/api/economics", body)["kind"], "assumption_only")
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.request("/api/economics", dict(body, extra=1))
        self.assertEqual(err.exception.code, 400)

    def test_live_does_not_fallback(self):
        with (
            patch("jev_lab.provider.live_enabled", return_value=False),
            patch("jev_lab.provider.live") as live,
        ):
            with self.assertRaises(urllib.error.HTTPError) as err:
                self.request(
                    "/api/studio-run",
                    {"pattern_id": "citation", "variant": "routine", "consent": True},
                )
            self.assertEqual(err.exception.code, 403)
            live.assert_not_called()

    def test_start_studio_scripts_and_styles_in_manifest(self):
        for path in ("/studio.js", "/studio.css", "/evidence.js"):
            with urllib.request.urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
        with urllib.request.urlopen(self.base) as response:
            html = response.read().decode()
        self.assertIn('id="start"', html)
        self.assertIn('id="studio"', html)
        self.assertIn('id="lessonRun"', html)
