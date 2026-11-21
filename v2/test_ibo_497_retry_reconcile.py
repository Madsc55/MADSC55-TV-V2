#!/usr/bin/env python3
import json
import unittest
from collections import Counter

from ibo_497_retry_reconcile import build_full_report, digest
from ibo_single_playlist_transfer import parse

class RetryReconcileTests(unittest.TestCase):
    def fixture(self, statuses=None):
        blocks = [
            '#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel %d\nhttps://example.test/%d\n' % (i, i)
            for i in range(1, 1793)
        ]
        raw = ('#EXTM3U\n' + ''.join(blocks)).encode()
        selected = parse(raw)[1]
        queue = []
        for block in selected[1107:]:
            url = block.splitlines()[-1].strip()
            queue.append({"channel_sha256": digest(block.encode()),
                          "url_sha256": digest(url.encode()), "run_id": 44640007709,
                          "evidence_sha256": "b" * 64, "attempts": 1,
                          "status": "uncertain", "reason": "recheck_required"})
        initial = {
            "schema": 1, "source_run_id": 44640007709,
            "source_report_canonical_sha256": "b48bd57ba03a7e4ee4ed3f65355572e267db87b4d48c6d4fb390b8484dc55c",
            "current_playlist_sha256": digest(raw),
            "counts": {"verified": 1107, "uncertain": 685},
            "preview_only": True, "canonical_playlist_written": False,
            "retry_queue": queue,
        }
        initial_bytes = json.dumps(initial, sort_keys=True).encode()
        retry_entries = []
        statuses = statuses or ["verified"] * 685
        for block, status in zip(selected[1107:], statuses):
            url = block.splitlines()[-1].strip()
            retry_entries.append({
                "channel_sha256": digest(block.encode()), "url_sha256": digest(url.encode()),
                "run_id": 999, "evidence_sha256": "c" * 64,
                "attempts": 2 if status == "failed" else 1,
                "repeatable_av_failure": status == "failed", "status": status,
            })
        retry = {
            "schema": 1, "retry_only": True, "read_only": True,
            "playlist_sha256": digest(raw), "source_run_id": 999,
            "retry_source_manifest_sha256": digest(initial_bytes),
            "retry_source_manifest_artifact_id": 14681083208,
            "retry_scanned_count": 685, "full_inventory_count": 1792,
            "entries": retry_entries,
            "counts": dict(Counter(statuses)),
        }
        return raw, initial, initial_bytes, retry

    def test_verified_retry_results_recover_all_1792(self):
        raw, initial, initial_bytes, retry = self.fixture()
        full, report_sha = build_full_report(raw, initial, initial_bytes, retry)
        self.assertEqual(len(full["entries"]), 1792)
        self.assertEqual(sum(x["status"] == "verified" for x in full["entries"]), 1792)
        self.assertEqual(len(report_sha), 64)

    def test_only_repeated_deterministic_failures_can_be_failed(self):
        statuses = ["verified"] * 684 + ["failed"]
        raw, initial, initial_bytes, retry = self.fixture(statuses)
        full, _ = build_full_report(raw, initial, initial_bytes, retry)
        self.assertEqual(sum(x["status"] == "failed" for x in full["entries"]), 1)
        retry["entries"][-1]["repeatable_av_failure"] = False
        with self.assertRaises(ValueError):
            build_full_report(raw, initial, initial_bytes, retry)

    def test_incomplete_or_duplicate_retry_report_fails_closed(self):
        raw, initial, initial_bytes, retry = self.fixture()
        retry["entries"].pop()
        retry["counts"] = {"verified": 684}
        with self.assertRaises(ValueError):
            build_full_report(raw, initial, initial_bytes, retry)
        raw, initial, initial_bytes, retry = self.fixture()
        retry["entries"][1] = retry["entries"][0]
        with self.assertRaises(ValueError):
            build_full_report(raw, initial, initial_bytes, retry)

    def test_report_counts_must_match_entry_statuses(self):
        raw, initial, initial_bytes, retry = self.fixture()
        retry["counts"] = {"verified": 1}
        with self.assertRaises(ValueError):
            build_full_report(raw, initial, initial_bytes, retry)

    def test_initial_manifest_mismatch_fails_closed(self):
        raw, initial, initial_bytes, retry = self.fixture()
        with self.assertRaises(ValueError):
            build_full_report(raw, initial, initial_bytes + b" ", retry, require_known_snapshot=True)

if __name__ == "__main__":
    unittest.main()
