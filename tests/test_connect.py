import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from jev_lab import provider, server

FAKE = "lab-test-key-0123456789abcdefXYZ"


class RuntimeKeyTests(unittest.TestCase):
    def setUp(self):
        provider.disconnect()
        self.addCleanup(provider.disconnect)

    def test_pasted_key_enables_live_and_is_never_echoed(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "JEV_ALLOW_LIVE": ""}):
            self.assertFalse(provider.live_enabled())
            status = provider.connect("  " + FAKE + "\n")
            self.assertEqual(status, {"source": "browser", "hint": FAKE[-4:]})
            self.assertTrue(provider.live_enabled())
            self.assertEqual(provider.api_key(), FAKE)
            self.assertNotIn(FAKE, json.dumps(provider.key_status()))
            self.assertEqual(provider._redact("token " + FAKE + " end"), "token [redacted] end")
            self.assertEqual(provider.disconnect(), {"source": None, "hint": None})
            self.assertFalse(provider.live_enabled())

    def test_malformed_keys_are_refused_without_being_stored(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "JEV_ALLOW_LIVE": ""}):
            for bad in ["short", "has a space in it 0123456789", "x" * 300, 12345, None, "tab\tkey0123456789"]:
                with self.subTest(bad=bad), self.assertRaises(ValueError) as caught:
                    provider.connect(bad)
                self.assertNotIn(str(bad), str(caught.exception))
            self.assertIsNone(provider.api_key())

    def test_terminal_key_takes_precedence_and_blocks_paste(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "env-key-0123456789abcdef", "JEV_ALLOW_LIVE": "1"}):
            self.assertEqual(provider.key_status(), {"source": "terminal", "hint": "cdef"})
            with self.assertRaises(PermissionError):
                provider.connect(FAKE)
            self.assertEqual(provider.api_key(), "env-key-0123456789abcdef")
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "env-key-0123456789abcdef", "JEV_ALLOW_LIVE": ""}):
            self.assertFalse(provider.live_enabled(), "a terminal key without JEV_ALLOW_LIVE=1 stays off")


class ConnectEndpointTests(unittest.TestCase):
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

    def setUp(self):
        provider.disconnect()
        self.addCleanup(provider.disconnect)

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as r:
            return json.load(r)

    def post(self, path, body):
        token = self.get("/api/config")["session_token"]
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-Lab-Token": token},
        )
        with urllib.request.urlopen(req) as r:
            return json.load(r)

    def test_connect_then_config_then_disconnect(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "JEV_ALLOW_LIVE": ""}):
            before = self.get("/api/config")
            self.assertFalse(before["live_enabled"])
            self.assertIsNone(before["key_source"])
            result = self.post("/api/connect", {"api_key": FAKE})
            self.assertEqual(result, {"connected": True, "source": "browser", "hint": FAKE[-4:]})
            config = self.get("/api/config")
            self.assertTrue(config["live_enabled"])
            self.assertEqual((config["key_source"], config["key_hint"]), ("browser", FAKE[-4:]))
            self.assertNotIn(FAKE, json.dumps(config))
            self.assertEqual(self.post("/api/disconnect", {})["connected"], False)
            self.assertFalse(self.get("/api/config")["live_enabled"])

    def test_bad_key_is_a_400_that_does_not_echo_it(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "JEV_ALLOW_LIVE": ""}):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post("/api/connect", {"api_key": "nope"})
            self.assertEqual(caught.exception.code, 400)
            self.assertNotIn("nope", caught.exception.read().decode())

    def test_connect_rejects_unexpected_fields(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post("/api/connect", {"api_key": FAKE, "remember": True})
        self.assertEqual(caught.exception.code, 400)
        self.assertIsNone(provider.key_status()["source"])


if __name__ == "__main__":
    unittest.main()
