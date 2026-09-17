import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

try:
    from jev_lab import __main__ as cli
except ImportError:
    cli = None

LIVE_ENV = ("TYPESAFE_API_KEY", "JEV_ALLOW_LIVE")


@unittest.skipIf(cli is None, "cli compare pending")
class CompareCommandTests(unittest.TestCase):
    """The compare command is CLI-only work and must fail closed on live arms."""

    def run_cli(self, *argv, **kwargs):
        """Run the CLI in-process. Returns (exit_code, output, written_report)."""
        env = {k: v for k, v in os.environ.items() if k not in LIVE_ENV}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "compare.json"
            stream = io.StringIO()
            code = 0
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch("sys.argv", ["jev_lab", "compare", "--out", str(out), *argv]),
            ):
                try:
                    with redirect_stdout(stream), redirect_stderr(stream):
                        cli.main()
                except SystemExit as exc:
                    code = exc.code or 0
            report = json.loads(out.read_text()) if out.exists() else None
            return code, stream.getvalue(), report

    def test_replay_only_compare_runs_offline(self):
        code, _output, report = self.run_cli("--arms", "replay", "--cases", "S01,S02")
        self.assertEqual(code, 0)
        self.assertIsNotNone(report)
        self.assertFalse(report["ranked"])
        self.assertEqual([arm["name"] for arm in report["arms"]], ["replay"])
        self.assertEqual(report["arms"][0]["succeeded"], 2)
        self.assertEqual(report["arms"][0]["failed"], 0)

    def test_live_arm_is_refused_before_any_call_without_consent(self):
        code, output, report = self.run_cli("--arms", "replay,native")
        self.assertEqual(code, 2)
        self.assertIsNone(report, "nothing may be written when the live gate refuses")
        self.assertIn("--allow-network", output)

    def test_live_arm_needs_both_the_flag_and_the_mode(self):
        code, output, report = self.run_cli("--allow-network", "--arms", "gateway")
        self.assertEqual(code, 2)
        self.assertIsNone(report)
        self.assertIn("--allow-network", output)

    def test_unknown_arm_is_refused_before_any_call(self):
        code, _output, report = self.run_cli("--arms", "replay,openai")
        self.assertEqual(code, 2)
        self.assertIsNone(report)

    def test_compare_never_pools_arms_into_one_evaluation(self):
        """metrics.evaluate() refuses mixed provenance, so arms are evaluated
        independently: no report-level metrics object may span two arms, each arm
        computes its own, and an arm that produced nothing reports unavailable."""
        code, _output, report = self.run_cli(
            "--mode",
            "live",
            "--allow-network",
            "--arms",
            "replay,native",
            "--cases",
            "S01",
        )
        self.assertEqual(code, 1)
        self.assertNotIn("metrics", report, "no metrics object may span arms")
        arms = {arm["name"]: arm for arm in report["arms"]}
        self.assertEqual(sorted(arms), ["native", "replay"])
        for name in ("native", "replay"):
            dist = arms[name]["tracks"]["comparable_distribution"]
            self.assertFalse(dist["pooled_with_other_arms"], f"{name} arm must not be pooled")
        self.assertEqual(arms["replay"]["tracks"]["comparable_distribution"]["metrics"]["n"], 1)
        self.assertIsNone(
            arms["native"]["tracks"]["comparable_distribution"]["metrics"],
            "an arm with no successful call reports unavailable, never zero",
        )

    def test_consented_live_failure_is_retained_verbatim(self):
        """Consent satisfies the CLI gate, not the provider gate: the provider still
        refuses without terminal credentials, and its own message must survive."""
        code, _output, report = self.run_cli(
            "--mode",
            "live",
            "--allow-network",
            "--arms",
            "replay,native",
            "--cases",
            "S01",
        )
        self.assertEqual(code, 1, "a recorded failure must exit non-zero")
        native = next(arm for arm in report["arms"] if arm["name"] == "native")
        self.assertEqual((native["succeeded"], native["failed"]), (0, 1))
        failure = native["failures"][0]
        self.assertIn("TYPESAFE_API_KEY", failure["error"])
        self.assertIn("live mode disabled", failure["error"].lower())
        self.assertTrue(failure["cost_unknown"])
        replay = next(arm for arm in report["arms"] if arm["name"] == "replay")
        self.assertEqual(replay["succeeded"], 1, "one arm failing must not stop another")

    def test_rules_arm_compare_runs_offline(self):
        code, _output, report = self.run_cli("--arms", "replay,rules", "--cases", "S02,S04")
        self.assertEqual(code, 0)
        names = [arm["name"] for arm in report["arms"]]
        self.assertEqual(names, ["replay", "rules"])
        self.assertTrue(report["planted_error"]["S04"])
        rows = {
            arm["name"]: {row["case_id"]: row for row in arm["cases"]} for arm in report["arms"]
        }
        self.assertEqual(rows["rules"]["S02"]["answers"]["issue"], "delivery")
        self.assertEqual(rows["replay"]["S02"]["answers"]["issue"], "routine")


if __name__ == "__main__":
    unittest.main()
