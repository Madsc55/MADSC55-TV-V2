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
        for item in self.items[:2]:
            item["attempts"].insert(0, {"outcome": "NETWORK_TIMEOUT",
                                        "finished_at_utc": "2026-11-18T18:33:44+00:00"})
        self.report = dict(tasks=[17, 18, 20], source_run_id=43608247496,
                           source_artifact_id=14135417421,
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


    def test_retries_preserve_prior_av_evidence_and_its_age(self):
        prior = copy.deepcopy(self.rows)
        proof = {"decoded_av_verified": True, "decode_status": "DECODED_AV",
                 "verified_quality": {"av_verified": True, "quality": "HD"}}
        urls = list(prior)[:2]  # A later one-segment sample and a later HTTP 503.
        for url in urls:
            prior[url] = checkpoint_row(url, proof, {}, checked_at=1)
        merged, count = reconcile(prior, self.report)
        self.assertEqual(count, 15)
        for url in urls:
            self.assertEqual(merged[url]["result"], prior[url]["result"])
            self.assertEqual(merged[url]["checked_at"], prior[url]["checked_at"])
            detail = merged[url]["diagnostics"]["bounded_retry_import"]
            self.assertGreater(detail["observed_at"], merged[url]["checked_at"])
            self.assertEqual(len(detail["attempts"]), 2)
        self.assertEqual(reconcile(merged, self.report), (merged, 0))

    def test_mismatched_evidence_totals_and_source_are_rejected(self):
        examples = (("source_artifact_id", 1), ("source_run_id", 1))
        for field, value in examples:
            with self.subTest(field=field), self.assertRaises(ValueError):
                reconcile(self.rows, {**self.report, field: value})
        missing = copy.deepcopy(self.report)
        missing["observations"][0]["attempts"].pop(0)
        with self.assertRaises(ValueError):
            reconcile(self.rows, missing)
        changed = copy.deepcopy(self.report)
        changed["observations"][1]["latest_disposition"] = "REVIEW_HTTP_404"
        changed["observations"][1]["attempts"][-1]["manifest_http_status"] = 404
        with self.assertRaises(ValueError):
            reconcile(self.rows, changed)

    def test_missing_hash_fails_closed(self):
        report = copy.deepcopy(self.report)
        report["observations"][0]["url_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            reconcile(self.rows, report)

    def test_partial_resume_preserves_membership_and_newer_results(self):
        from datetime import timedelta
        eligible, newer = list(self.rows)[:2]
        unrelated = "https://example.org/unrelated"
        latest = datetime.fromisoformat(self.items[1]["attempts"][-1]["finished_at_utc"])
        rows = {
            eligible: self.rows[eligible],
            newer: checkpoint_row(newer, None, {"from_new_scan": True},
                                  checked_at=(latest + timedelta(seconds=1)).timestamp()),
            unrelated: checkpoint_row(unrelated, None, {}, checked_at=1),
        }
        with self.assertRaises(ValueError):
            reconcile(rows, self.report)
        merged, applied = reconcile(rows, self.report, existing_rows_only=True)
        self.assertEqual(applied, 1)
        self.assertEqual(merged.keys(), rows.keys())
        self.assertEqual(merged[newer], rows[newer])
        self.assertEqual(merged[unrelated], rows[unrelated])
        self.assertEqual(merged[eligible]["diagnostics"]["bounded_retry_import"]["attempts"],
                         self.items[0]["attempts"])
        self.assertEqual(reconcile(merged, self.report, existing_rows_only=True), (merged, 0))

    def test_fake_av_fails_closed(self):
        report = copy.deepcopy(self.report)
        report["observations"][0]["attempts"][-1]["audio_frame_decoded"] = False
        with self.assertRaises(ValueError):
            reconcile(self.rows, report)

    def test_stale_report_cannot_rollback(self):
        newer = copy.deepcopy(self.rows)
        url = next(iter(newer))
        newer[url]["checked_at"] = datetime(2026, 11, 19, tzinfo=timezone.utc).timestamp()
        _, n = reconcile(newer, self.report)
        self.assertEqual(n, 14)


    def test_real_committed_report_shape_and_outcomes(self):
        from hashlib import sha256
        from pathlib import Path
        from merge_bounded_retry_checkpoint import REVIEWED_REPORT_SHA256
        path = Path(__file__).resolve().parent / "reports" / "task17-18-20-bounded-retry-20261118.json"
        self.assertEqual(sha256(path.read_bytes()).hexdigest(), REVIEWED_REPORT_SHA256)
        real = __import__("json").loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(real["observations"]), 15)
        self.assertEqual(sum(len(x["attempts"]) for x in real["observations"]), 17)
        for obs in real["observations"]:
            self.assertEqual(len(obs["url_sha256"]), 64)
            self.assertIn(obs["latest_disposition"], real["latest_outcomes"])
            self.assertLessEqual(obs["recovery_attempts_after_batch"], 3)
        self.assertFalse(real["sealed_checkpoint_updated"])

    def test_duplicate_hash_fails_closed(self):
        report = copy.deepcopy(self.report)
        report["observations"][1]["url_sha256"] = report["observations"][0]["url_sha256"]
        with self.assertRaises(ValueError):
            reconcile(self.rows, report)

    def test_false_http_status_fails_closed(self):
        report = copy.deepcopy(self.report)
        report["observations"][1]["attempts"][-1]["manifest_http_status"] = 200
        with self.assertRaises(ValueError):
            reconcile(self.rows, report)

if __name__ == "__main__":
    unittest.main()
