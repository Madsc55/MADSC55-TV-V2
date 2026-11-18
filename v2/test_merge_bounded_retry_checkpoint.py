"""No-network regression for existing bounded retry evidence importer."""
import copy
import unittest
from datetime import datetime, timezone
from merge_bounded_retry_checkpoint import reconcile
from scan_checkpoint import checkpoint_row

class BoundedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.items = []
        for i in range(15):
            url = "https://example.org/stream/" + str(i)
            row = checkpoint_row(url, None, {}, checked_at=1, recovery_attempts=0)
            self.rows[url] = row
            kind = ("AV_SAMPLE_VERIFIED" if i == 0 else
                    "RETRY_HTTP_503" if i <= 6 else "REVIEW_HTTP_404")
            attempt = {"finished_at_utc": "2026-11-18T18:35:26+00:00"}
            if i == 0:
                attempt.update(outcome="DECODED_AV_SAMPLE", video_frame_decoded=True,
                               audio_frame_decoded=True, segment_sha256="a",
                               video_frame_md5="b", audio_frame_md5="c")
            else:
                attempt.update(outcome="HTTP_ERROR",
                               manifest_http_status=503 if i <= 6 else 404)
            self.items.append(dict(url_sha256=row["url_sha256"],
                                   latest_disposition=kind,
                                   recovery_attempts_after_batch=1,
                                   attempts=[attempt]))
        self.report = dict(tasks=[17, 18, 20], source_run_id=43608247496,
                           unique_urls_attempted=15, attempts_this_batch=17,
                           latest_outcomes={"AV_SAMPLE_VERIFIED": 1,
                                            "RETRY_HTTP_503": 6,
                                            "REVIEW_HTTP_404": 8},
                           observations=self.items)

    def test_exact_merge_and_idempotence(self):
        merged, n = reconcile(self.rows, self.report)
        self.assertEqual(n, 15)
        self.assertEqual(len(merged), 15)
        self.assertTrue(all(row["result"] is None for row in merged.values()))
        replay, n2 = reconcile(merged, self.report)
        self.assertEqual(n2, 0)
        self.assertEqual(replay, merged)

    def test_missing_hash_fails_closed(self):
        report = copy.deepcopy(self.report)
        report["observations"][0]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            reconcile(self.rows, report)

    def test_fake_av_fails_closed(self):
        report = copy.deepcopy(self.report)
        report["observations"][0]["attempts"][0]["audio_frame_decoded"] = False
        with self.assertRaises(ValueError):
            reconcile(self.rows, report)

    def test_stale_report_cannot_rollback(self):
        newer = copy.deepcopy(self.rows)
        url = next(iter(newer))
        newer[url]["checked_at"] = datetime(2026, 11, 19, tzinfo=timezone.utc).timestamp()
        _, n = reconcile(newer, self.report)
        self.assertEqual(n, 14)

if __name__ == "__main__":
    unittest.main()
