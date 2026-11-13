#!/usr/bin/env python3
"""Grouped offline private IBO export acceptance and false proof rejection."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from av_verified_sealed_ibo_export import select,validate_destination

def fixture(decoded=True,ids=None):
    if ids is None:ids=["TestTV.tr"]
    url="https://cdn.example.org/stream.m3u8"
    digest=hashlib.sha256(url.encode()).hexdigest()
    stream={"url_sha256":digest,"status":"VIDEO_AUDIO_DECODED" if decoded else "VIDEO_AUDIO_STREAMS_ONLY",
            "channel_ids":ids,"video":True,"audio":True,"decoded":decoded}
    report={"schema":1,"kind":"TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE",
            "policy":"ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS",
            "unique_url_candidates":1,"streams":[stream],
            "protected_playlist_modified":False,"ibo_device_verified":False}
    rows=[{"url_sha256":digest,"url":url,"channel_ids":ids,
           "probe_status":stream["status"],"video":True,"audio":True,"decoded":decoded}]
    return report,rows

class SeparatePrivateExport(unittest.TestCase):
    def test_existing_cli_hands_encrypted_batch_requests_to_offline_acceptance(self):
        from unittest.mock import patch
        import av_verified_sealed_ibo_export as exporter
        argv=["exporter", "--private-key", "/tmp/key.pem", "--report", "/tmp/report.json",
              "--sealed", "/tmp/proof.sealed", "--batch-out", "/tmp/private-batches"]
        with patch("sys.argv", argv), patch("bulk_candidate_acceptance.main") as batch, \
                patch.object(exporter,"validate_destination") as plaintext_destination:
            exporter.main()
        batch.assert_called_once_with(["--report", "/tmp/report.json", "--sealed", "/tmp/proof.sealed",
                                       "--private-key", "/tmp/key.pem", "--out", "/tmp/private-batches"])
        plaintext_destination.assert_not_called()

    def test_real_video_audio_and_exact_identity_exported(self):
        content,summary=select(*fixture())
        self.assertEqual(summary["verified_entries"],1)
        self.assertIn('tvg-id="TestTV.tr"',content)
        self.assertIn('https://cdn.example.org/stream.m3u8',content)
        self.assertFalse(summary["ibo_device_verified"])

    def test_ffprobe_only_never_exported(self):
        content,summary=select(*fixture(decoded=False))
        self.assertEqual(summary["verified_entries"],0)
        self.assertEqual(content,"#EXTM3U\n")

    def test_ambiguous_one_url_multiple_identities_not_exported(self):
        content,summary=select(*fixture(ids=["One.tr","Two.az"]))
        self.assertEqual(summary["verified_entries"],0)
        self.assertEqual(summary["ambiguous_multi_channel_url_skipped"],1)

    def test_wrong_hash_and_false_av_rejected(self):
        report,rows=fixture()
        rows[0]["url"]="https://cdn.example.org/different.m3u8"
        with self.assertRaises(ValueError):select(report,rows)
        report,rows=fixture()
        rows[0]["video"]=False
        # No false AV proof from sealed mismatch; decoded gating will not export.
        content,summary=select(report,rows)
        self.assertEqual(summary["verified_entries"],0)
        report,rows=fixture()
        report["streams"][0]["audio"]=False
        with self.assertRaises(ValueError):select(report,rows)

    def test_duplicate_authenticated_hash_cannot_be_exported_twice(self):
        report,rows=fixture()
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError,"Duplicate authenticated URL hash"):
            select(report,rows)

    def test_incomplete_authenticated_batch_fails_closed(self):
        report,rows=fixture()
        rows.clear()
        with self.assertRaisesRegex(ValueError,"disagree"):
            select(report,rows)

    def test_zero_verified_candidates_never_pads_target_package(self):
        report,rows=fixture(decoded=False)
        content,summary=select(report,rows)
        self.assertEqual(summary["verified_entries"],0)
        self.assertEqual(summary["status"],"NO_VERIFIED_STREAM_TO_EXPORT")
        self.assertEqual(content,"#EXTM3U\n")
        self.assertFalse(summary["protected_main_playlist_modified"])

    def test_cannot_target_main_or_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
            with self.assertRaises(ValueError):validate_destination(path)
            from av_verified_sealed_ibo_export import REPORTS
            target=REPORTS/"private-test-existing.m3u8"
            try:
                target.touch(exist_ok=False)
                with self.assertRaises(ValueError):validate_destination(target)
            finally:
                target.unlink(missing_ok=True)

if __name__=="__main__":
    unittest.main()
