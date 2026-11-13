"""Stage 3 scanner contract tests: no network or playlist mutations."""
import unittest
from unittest.mock import patch
import real_ibo_scan as scanner


class ScannerStage3IntegrationTests(unittest.TestCase):
    def test_http_404_is_recorded_for_review(self):
        import urllib.error
        from stage3_recovery_queue import build_recovery_queue
        entry = {"url": "https://example.org/missing.m3u8"}
        diagnostics = {}
        failure = urllib.error.HTTPError(entry["url"], 404, "Not Found", {}, None)
        with patch.object(scanner.urllib.request, "urlopen", side_effect=failure):
            self.assertIsNone(scanner.check_hls(entry, 2, diagnostics))
        self.assertEqual(diagnostics["last_http_status"], 404)
        queue = build_recovery_queue([{**entry, **diagnostics, "recovery_attempts": 1}])
        self.assertEqual(queue[0]["action"], "REVIEW")

    def test_http_503_is_recorded_for_retry(self):
        import urllib.error
        from stage3_recovery_queue import build_recovery_queue
        entry = {"url": "https://example.org/busy.m3u8"}
        diagnostics = {}
        failure = urllib.error.HTTPError(entry["url"], 503, "Unavailable", {}, None)
        with patch.object(scanner.urllib.request, "urlopen", side_effect=failure):
            self.assertIsNone(scanner.check_hls(entry, 2, diagnostics))
        self.assertEqual(diagnostics["last_http_status"], 503)
        queue = build_recovery_queue([{**entry, **diagnostics, "recovery_attempts": 1}])
        self.assertEqual(queue[0]["action"], "RETRY")

    def test_truncated_source_is_retried_before_parsing(self):
        import http.client
        class Response:
            headers = {'Content-Length': '100'}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return b'#EXTM3U\n'
        with patch.object(scanner.urllib.request, 'urlopen', return_value=Response()) as opener, patch.object(scanner.time, 'sleep'):
            with self.assertRaises(http.client.IncompleteRead):
                scanner.fetch('https://example.org/source.m3u', timeout=1)
        self.assertEqual(opener.call_count, 3)

    def test_verified_probe_quality_is_carried_forward(self):
        entry = {"url": "https://example.org/stream.m3u8", "name": "Example", "group": "News"}
        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/vnd.apple.mpegurl"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, size):
                return b"#EXTM3U\n#EXT-X-VERSION:3\n"
        observed = {"status": "AV_STREAMS_PRESENT", "video": True, "audio": True,
                    "streams": [{"codec_type": "video", "width": 1280, "height": 720},
                                {"codec_type": "audio", "codec_name": "aac"}]}
        with patch.object(scanner.urllib.request, "urlopen", return_value=FakeResponse()), patch.object(scanner, "probe", return_value=observed), patch.object(scanner, "verify_decoded_av", return_value={"decoded_av_verified": True, "decode_status": "DECODED_AV"}):
            result = scanner.check_hls(entry, 2)
        self.assertEqual(result["verified_quality"]["quality"], "720p")

    def test_av_without_resolution_is_not_accepted(self):
        entry = {"url": "https://example.org/stream.m3u8"}
        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/vnd.apple.mpegurl"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, size):
                return b"#EXTM3U\n#EXT-X-VERSION:3\n"
        observed = {"status": "AV_STREAMS_PRESENT", "video": True, "audio": True,
                    "streams": [{"codec_type": "video", "codec_name": "h264"},
                                {"codec_type": "audio", "codec_name": "aac"}]}
        with patch.object(scanner.urllib.request, "urlopen", return_value=FakeResponse()), patch.object(scanner, "probe", return_value=observed), patch.object(scanner, "verify_decoded_av", return_value={"decoded_av_verified": True, "decode_status": "DECODED_AV"}):
            self.assertIsNone(scanner.check_hls(entry, 2))

    def test_http_success_without_av_is_not_exported(self):
        entry = {"url": "https://example.org/stream.m3u8"}
        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/vnd.apple.mpegurl"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, size):
                return b"#EXTM3U\n#EXT-X-VERSION:3\n"
        with patch.object(scanner.urllib.request, "urlopen", return_value=FakeResponse()), patch.object(scanner, "probe", return_value={"status": "VIDEO_ONLY", "video": True, "audio": False}):
            self.assertIsNone(scanner.check_hls(entry, 2))

    def test_stream_metadata_without_decoded_av_is_not_exported(self):
        entry = {"url": "https://example.org/stream.m3u8"}
        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/vnd.apple.mpegurl"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, size):
                return b"#EXTM3U\\n#EXT-X-VERSION:3\\n"
        observed = {"status": "AV_STREAMS_PRESENT", "video": True, "audio": True,
                    "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
                                {"codec_type": "audio", "codec_name": "aac"}]}
        with patch.object(scanner.urllib.request, "urlopen", return_value=FakeResponse()), \
             patch.object(scanner, "probe", return_value=observed), \
             patch.object(scanner, "verify_decoded_av", return_value={"decoded_av_verified": False, "decode_status": "NO_DECODED_FRAME"}):
            diagnostics = {}
            self.assertIsNone(scanner.check_hls(entry, 2, diagnostics))
            self.assertEqual(diagnostics["decode_status"], "NO_DECODED_FRAME")


if __name__ == "__main__":
    unittest.main()
