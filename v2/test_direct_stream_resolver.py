import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from direct_stream_resolver import resolve_candidate, resolve_report, write_encrypted_report
from secure_archive import MAGIC, decrypt

class DirectStreamResolverTests(unittest.TestCase):
    def run_meta(self, meta):
        def runner(command, **kwargs):
            self.assertEqual(command[0], "yt-dlp")
            return SimpleNamespace(returncode=0, stdout=json.dumps(meta), stderr="")
        return runner

    def test_youtube_live_page_resolves_direct_hls_candidate(self):
        item = {"source": "youtube", "source_id": "youtube:abcdefghijk",
                "url": "https://www.youtube.com/watch?v=abcdefghijk",
                "name": "Live News", "status": "LIVE_METADATA_VERIFIED", "verified_av": False}
        resolved, error = resolve_candidate(item, runner=self.run_meta({
            "is_live": True, "url": "https://cdn.example/live.m3u8",
            "protocol": "m3u8_native"}))
        self.assertIsNone(error)
        self.assertEqual(resolved["source_id"], item["source_id"])
        self.assertEqual(resolved["status"], "RESOLVED_DIRECT_HLS_NOT_AV_VERIFIED")
        self.assertFalse(resolved["verified_av"])

    def test_youtube_page_without_live_metadata_is_rejected_before_resolve(self):
        item = {"source": "youtube", "source_id": "youtube:abcdefghijk",
                "url": "https://www.youtube.com/watch?v=abcdefghijk",
                "status": "DISCOVERED_NOT_LIVE_VERIFIED", "verified_av": False}
        resolved, error = resolve_candidate(item, runner=lambda *_args, **_kwargs: self.fail("must not run"))
        self.assertIsNone(resolved)
        self.assertEqual(error, "YOUTUBE_NOT_LIVE_VERIFIED")

    def test_official_page_requires_live_metadata_and_direct_hls(self):
        item = {"source": "official", "source_id": "official:tv.example/live",
                "url": "https://tv.example/live", "name": "Official TV",
                "status": "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED", "verified_av": False}
        resolved, error = resolve_candidate(item, runner=self.run_meta({
            "is_live": True, "url": "https://cdn.example/stream.m3u8",
            "protocol": "m3u8_native"}))
        self.assertIsNone(error)
        self.assertEqual(resolved["source"], "official")
        self.assertTrue(resolved["live_metadata_verified"])

    def test_non_hls_and_non_live_metadata_are_rejected(self):
        item = {"source": "official", "source_id": "official:tv.example/live",
                "url": "https://tv.example/live",
                "status": "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED", "verified_av": False}
        resolved, error = resolve_candidate(item, runner=self.run_meta({
            "is_live": True, "url": "https://cdn.example/video.mp4", "protocol": "https"}))
        self.assertIsNone(resolved)
        self.assertEqual(error, "NOT_DIRECT_HTTPS_HLS")
        resolved, error = resolve_candidate(item, runner=self.run_meta({
            "is_live": False, "url": "https://cdn.example/stream.m3u8", "protocol": "m3u8_native"}))
        self.assertIsNone(resolved)
        self.assertEqual(error, "LIVE_STATUS_NOT_VERIFIED")

    def test_encrypted_report_round_trip_hides_direct_url(self):
        direct_url = "https://cdn.example/live.m3u8?token=secret"
        report = {"resolved": 1, "candidates": [{"url": direct_url}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resolved.enc"
            result = write_encrypted_report(report, path, "long-test-passphrase-123")
            blob = path.read_bytes()
            self.assertTrue(blob.startswith(MAGIC))
            self.assertNotIn(direct_url.encode(), blob)
            restored = json.loads(decrypt(blob, "long-test-passphrase-123"))
            self.assertEqual(restored["candidates"][0]["url"], direct_url)
            self.assertTrue(result["encrypted"])

    def test_resolver_budget_balances_youtube_and_official_candidates(self):
        candidates = []
        for index in range(3):
            candidates.append({"source": "youtube", "source_id": f"youtube:abcdefghij{index}",
                               "url": "https://www.youtube.com/watch?v=abcdefghijk",
                               "status": "LIVE_METADATA_VERIFIED", "verified_av": False})
            candidates.append({"source": "official", "source_id": f"official:tv{index}.example",
                               "url": f"https://tv{index}.example/live",
                               "status": "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED", "verified_av": False})
        report = resolve_report({"candidates": candidates}, runner=lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout=json.dumps({"is_live": True, "url": "https://cdn.example/live.m3u8",
                                            "protocol": "m3u8_native"}), stderr=""), limit=4)
        self.assertEqual(report["attempted"], 4)
        self.assertEqual(report["eligible"], 6)
        self.assertEqual(report["skipped_by_limit"], 2)
        self.assertEqual(report["resolved"], 4)

if __name__ == "__main__":
    unittest.main()
