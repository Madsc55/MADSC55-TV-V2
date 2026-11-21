#!/usr/bin/env python3
import hashlib
import unittest

from ibo_495_yedekler_av_audit import select_retry_blocks, digest

class RetrySelectionTests(unittest.TestCase):
    def fixture(self):
        blocks = [
            '#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel %d\nhttps://example.test/%d\n' % (i, i)
            for i in range(1, 1793)
        ]
        raw = ('#EXTM3U\n' + ''.join(blocks)).encode()
        selected = [b for b in blocks]
        queue = []
        for pos, block in enumerate(selected[1107:], 1108):
            url = block.splitlines()[-1].strip()
            queue.append({
                "channel_sha256": digest(block.encode()),
                "url_sha256": digest(url.encode()),
                "run_id": 44640007709,
                "evidence_sha256": "b" * 64,
                "attempts": 1,
                "status": "uncertain",
                "reason": "recheck_required",
            })
        manifest = {
            "schema": 1,
            "source_run_id": 44640007709,
            "source_report_file_sha256": "30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c",
            "source_playlist_sha256": "eee260cce3926caff18238f9583958b40475e362ce7650fb7fac51a66a84ee1c",
            "source_artifact_id": 14587983768,
            "source_yedekler_count": 1792,
            "current_yedekler_count": 1792,
            "current_playlist_sha256": digest(raw),
            "ordered_yedekler_blocks_identical": True,
            "preview_only": True,
            "new_scan_started": False,
            "canonical_playlist_written": False,
            "counts": {"verified": 1107, "uncertain": 685},
            "failed_count": 0,
            "failed_tail_start_1based": None,
            "retry_queue": queue,
        }
        return raw, manifest

    def test_selects_exactly_685_uncertain_not_all_1792(self):
        raw, manifest = self.fixture()
        chosen = select_retry_blocks(raw, manifest)
        self.assertEqual(len(chosen), 685)
        self.assertEqual(chosen[0][0], 1108)
        self.assertEqual(chosen[-1][0], 1792)

    def test_rejects_changed_playlist(self):
        raw, manifest = self.fixture()
        with self.assertRaises(ValueError):
            select_retry_blocks(raw + b" ", manifest)

    def test_rejects_non_uncertain_queue_item(self):
        raw, manifest = self.fixture()
        manifest["retry_queue"][0]["status"] = "failed"
        with self.assertRaises(ValueError):
            select_retry_blocks(raw, manifest)

    def test_rejects_duplicate_identity(self):
        raw, manifest = self.fixture()
        manifest["retry_queue"][1] = manifest["retry_queue"][0]
        with self.assertRaises(ValueError):
            select_retry_blocks(raw, manifest)

    def test_rejects_url_hash_mismatch(self):
        raw, manifest = self.fixture()
        manifest["retry_queue"][0]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            select_retry_blocks(raw, manifest)

if __name__ == "__main__":
    unittest.main()
