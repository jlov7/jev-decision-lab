"""Exports remain interpretable when in-memory receipt IDs expire."""

import runpy
import shutil
import tempfile
import unittest
from pathlib import Path

from jev_lab import engine, probes


class ExportCustodyTests(unittest.TestCase):
    def test_published_probe_keeps_self_contained_audit_receipts(self):
        result = probes.publish(
            probes.probe("S02", 2, mode="replay"), lambda r: dict(r, receipt_id="temporary")
        )
        self.assertEqual(len(result.get("audit_receipts", [])), 2)
        for r in result["audit_receipts"]:
            self.assertIn("request", r)
            self.assertIn("response", r)
            self.assertEqual(
                r["receipt_hash"],
                engine.digest({k: v for k, v in r.items() if k != "receipt_hash"}),
            )

    def test_published_ablation_keeps_each_input_and_output(self):
        result = probes.publish(
            probes.ablate("S02", mode="replay"), lambda r: dict(r, receipt_id="temporary")
        )
        for variant in result["variants"]:
            self.assertIn("audit_receipt", variant)
            self.assertIn("request", variant["audit_receipt"])

    def test_source_regeneration_preserves_the_dated_live_evidence_note(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            source = Path(__file__).resolve().parents[1] / "scripts/source_register.py"
            target = root / "scripts/source_register.py"
            shutil.copyfile(source, target)
            runpy.run_path(str(target), run_name="__main__")
            text = (root / "docs/SOURCES.md").read_text()
            self.assertIn("2026-09-18", text)
            self.assertIn("No authenticated live response at this access date", text)
