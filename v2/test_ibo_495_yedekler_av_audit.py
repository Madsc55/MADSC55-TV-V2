#!/usr/bin/env python3
import hashlib
import os
import unittest
from unittest.mock import patch

from ibo_495_yedekler_av_audit import select_retry_blocks, digest, classify_outcomes, audit_one

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
            "source_head_sha": "1e8bd6d46762366f151e1270cc767f598c8e63e8",
            "source_report_file_sha256": "30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c",
            "source_playlist_sha256": "eee260cce3926caff18238f9583958b40475e362ce7650fb7fac51a66a84ee1c",
            "source_artifact_id": 14587983768,
            "source_artifact_name": "yedekler-av-audit",
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

    def test_only_two_deterministic_absences_are_failed(self):
        self.assertEqual(classify_outcomes("NO_MEDIA", "NO_MEDIA"), "failed")
        self.assertEqual(classify_outcomes("NO_DECODED_FRAME", "NO_DECODED_FRAME"), "failed")
        self.assertEqual(classify_outcomes("TIMEOUT", "NO_MEDIA"), "uncertain")
        self.assertEqual(classify_outcomes("NO_MEDIA", "DECODE_FAILED"), "uncertain")
        self.assertEqual(classify_outcomes("NO_MEDIA", "AV_VERIFIED"), "verified")

    def test_retry_row_has_two_consistent_probe_outcomes(self):
        block = '#EXTINF:-1 group-title="🗂️ YEDEKLER",Sample\\nhttps://example.test/sample\\n'
        scenarios = [
            (["NO_MEDIA", "NO_MEDIA"], "failed", 2),
            (["TIMEOUT", "NO_MEDIA"], "uncertain", 2),
            (["AV_STREAMS_PRESENT"], "verified", 1),
        ]
        for statuses, expected, attempts in scenarios:
            calls = [{"status": status} for status in statuses]
            with (self.subTest(expected=expected),
                  patch("ibo_495_yedekler_av_audit.probe", side_effect=calls),
                  patch("ibo_495_yedekler_av_audit.verify_decoded_av",
                        return_value={"decoded_av_verified": True, "decode_status": "DECODED_AV"}),
                  patch.dict(os.environ, {"GITHUB_RUN_ID": "999"})):
                row = audit_one((1, block))
            self.assertEqual(row["status"], expected)
            self.assertEqual(row["attempts"], attempts)
            first = "AV_VERIFIED" if statuses[0] == "AV_STREAMS_PRESENT" else statuses[0]
            self.assertEqual(row["first_probe_status"], first)
            self.assertEqual(row["second_probe_status"], statuses[1] if attempts == 2 else None)
            self.assertEqual(row["probe_status"],
                             row["second_probe_status"] if attempts == 2 else first)
            self.assertEqual(row["decoded_av_verified"], expected == "verified")
            self.assertEqual(len(row["evidence_sha256"]), 64)

    def test_recovered_second_attempt_is_still_verified(self):
        block = '#EXTINF:-1 group-title="🗂️ YEDEKLER",Sample\\nhttps://example.test/sample\\n'
        with (patch("ibo_495_yedekler_av_audit.probe",
                    side_effect=[{"status": "TIMEOUT"}, {"status": "AV_STREAMS_PRESENT"}]),
              patch("ibo_495_yedekler_av_audit.verify_decoded_av",
                    return_value={"decoded_av_verified": True, "decode_status": "DECODED_AV"}),
              patch.dict(os.environ, {"GITHUB_RUN_ID": "999"})):
            row = audit_one((1, block))
        self.assertEqual(row["status"], "verified")
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(row["first_probe_status"], "TIMEOUT")
        self.assertEqual(row["second_probe_status"], "AV_VERIFIED")
        self.assertEqual(row["decode_status"], "DECODED_AV")

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

    def test_live_retry_entrypoint_fails_closed_before_any_probe(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from ibo_495_yedekler_av_audit import main
        raw, manifest = self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            playlist = Path(folder) / 'MADSC55_TV_IBO_CALISANLAR_TEST.m3u8'
            playlist.write_bytes(raw)
            source = Path(folder) / 'manifest.json'
            source.write_text(__import__('json').dumps(manifest))
            with patch('ibo_495_yedekler_av_audit.INITIAL_CURRENT_PLAYLIST_SHA256', __import__('hashlib').sha256(raw).hexdigest()), patch('ibo_495_yedekler_av_audit.digest', side_effect=lambda data: 'b001bf48f07437e9ae67ed9f73b12ea9cfcab653523973435cf3b1cee3c31fcc' if data == source.read_bytes() else __import__('hashlib').sha256(data).hexdigest()), patch('sys.argv', ['audit', '--retry-manifest', str(source), '--playlist', str(playlist)]), patch('ibo_495_yedekler_av_audit.probe') as probe:
                with self.assertRaisesRegex(RuntimeError, 'SECURITY HOLD'):
                    main()
                probe.assert_not_called()

if __name__ == "__main__":
    unittest.main()
