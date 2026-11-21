#!/usr/bin/env python3
"""Offline tests for the deterministic 685-row report-only retry plan."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v2.ibo_497_retry_plan import build_plan, digest, write_plan


class RetryPlanTests(unittest.TestCase):
    def fixture(self):
        blocks = [
            '#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel %d\nhttps://example.test/%d\n' % (i, i)
            for i in range(1, 1793)
        ]
        raw = ('#EXTM3U\n' + ''.join(blocks)).encode("utf-8")
        selected = blocks
        queue = []
        for position, block in enumerate(selected[1107:], 1108):
            url = block.splitlines()[-1].strip()
            queue.append({
                "channel_sha256": digest(block.encode("utf-8")),
                "url_sha256": digest(url.encode("utf-8")),
                "run_id": 44640007709,
                "evidence_sha256": "b" * 64,
                "attempts": 1,
                "status": "uncertain",
                "reason": "recheck_required",
                "source_timestamp_utc": "2026-11-20T00:20:09.490490+00:00",
            })
        manifest = {
            "source_run_id": 44640007709,
            "source_head_sha": "1e8bd6d46762366f151e1270cc767f598c8e63e8",
            "source_artifact_id": 14587983768,
            "source_report_file_sha256": "c" * 64,
            "source_report_canonical_sha256": "b" * 64,
            "source_playlist_sha256": "d" * 64,
            "current_playlist_sha256": digest(raw),
            "counts": {"verified": 1107, "uncertain": 685},
            "source_yedekler_count": 1792,
            "current_yedekler_count": 1792,
            "ordered_yedekler_blocks_identical": True,
            "preview_only": True,
            "new_scan_started": False,
            "canonical_playlist_written": False,
            "retry_queue": queue,
        }
        manifest_bytes = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return raw, manifest, manifest_bytes

    def build(self, raw, manifest, manifest_bytes):
        with (
            patch("v2.ibo_497_retry_plan.SOURCE_PLAYLIST_SHA256", digest(raw)),
            patch("v2.ibo_497_retry_plan.SOURCE_REPORT_FILE_SHA256", "c" * 64),
            patch("v2.ibo_497_retry_plan.SOURCE_REPORT_CANONICAL_SHA256", "b" * 64),
            patch("v2.ibo_497_retry_plan.INITIAL_MANIFEST_SHA256", digest(manifest_bytes)),
        ):
            return build_plan(raw, manifest, manifest_bytes, require_known_snapshot=True)

    def test_exact_685_plan_is_deterministic_and_read_only(self):
        raw, manifest, manifest_bytes = self.fixture()
        first = self.build(raw, manifest, manifest_bytes)
        second = self.build(raw, manifest, manifest_bytes)
        self.assertEqual(first, second)
        self.assertEqual(first["uncertain_retry_plan_count"], 685)
        self.assertEqual(len(first["items"]), 685)
        self.assertEqual(first["items"][0]["position"], 1108)
        self.assertEqual(first["items"][-1]["position"], 1792)
        self.assertEqual(first["items"][0]["next_attempt_number"], 2)
        self.assertFalse(first["live_retry_authorized"])
        self.assertFalse(first["new_scan_started"])
        self.assertFalse(first["playlist_write_allowed"])
        self.assertFalse(first["archive_write_allowed"])
        self.assertEqual(first["network_attempts"], 0)
        self.assertEqual(len(first["plan_sha256"]), 64)

    def test_missing_duplicate_or_mismatched_queue_item_rejected(self):
        raw, manifest, manifest_bytes = self.fixture()
        manifest["retry_queue"].pop()
        with self.assertRaises(ValueError):
            self.build(raw, manifest, manifest_bytes)
        raw, manifest, manifest_bytes = self.fixture()
        manifest["retry_queue"][1] = manifest["retry_queue"][0]
        with self.assertRaises(ValueError):
            self.build(raw, manifest, manifest_bytes)
        raw, manifest, manifest_bytes = self.fixture()
        manifest["retry_queue"][0]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.build(raw, manifest, manifest_bytes)

    def test_invalid_status_attempts_and_timestamp_rejected(self):
        for field, value in [
            ("status", "verified"),
            ("attempts", True),
            ("attempts", 2),
            ("source_timestamp_utc", "2026-11-20T00:20:09"),
            ("channel_sha256", "bad"),
        ]:
            raw, manifest, manifest_bytes = self.fixture()
            manifest["retry_queue"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.build(raw, manifest, manifest_bytes)

    def test_manifest_provenance_and_current_playlist_are_pinned(self):
        for field, value in [
            ("source_run_id", 1),
            ("source_artifact_id", 2),
            ("source_report_canonical_sha256", "0" * 64),
            ("source_yedekler_count", 18074),
            ("ordered_yedekler_blocks_identical", False),
            ("canonical_playlist_written", True),
        ]:
            raw, manifest, manifest_bytes = self.fixture()
            manifest[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build(raw, manifest, manifest_bytes)
        raw, manifest, manifest_bytes = self.fixture()
        with self.assertRaises(ValueError):
            self.build(raw + b"\n", manifest, manifest_bytes)

    def test_idempotent_output_never_overwrites_different_plan(self):
        raw, manifest, manifest_bytes = self.fixture()
        plan = self.build(raw, manifest, manifest_bytes)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "retry-plan.json"
            self.assertEqual(write_plan(target, plan), "CREATED")
            original = target.read_bytes()
            self.assertEqual(write_plan(target, plan), "ALREADY_PRESENT")
            self.assertEqual(target.read_bytes(), original)
            target.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                write_plan(target, plan)
            self.assertEqual(target.read_bytes(), b"tampered")

    def test_symlink_output_rejected(self):
        raw, manifest, manifest_bytes = self.fixture()
        plan = self.build(raw, manifest, manifest_bytes)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "retry-plan.json"
            protected = Path(directory) / "protected.json"
            protected.write_text("protected")
            target.symlink_to(protected)
            with self.assertRaises(ValueError):
                write_plan(target, plan)
            self.assertEqual(protected.read_text(), "protected")


if __name__ == "__main__":
    unittest.main()
