"""Stage 3 scanner contract tests: no network or playlist mutations."""
import unittest
from unittest.mock import patch
import real_ibo_scan as scanner


class ScannerStage3IntegrationTests(unittest.TestCase):
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
        observed = {"status": "AV_VERIFIED", "video": True, "audio": True,
                    "streams": [{"codec_type": "video", "width": 1280, "height": 720},
                                {"codec_type": "audio", "codec_name": "aac"}]}
        with patch.object(scanner.urllib.request, "urlopen", return_value=FakeResponse()), patch.object(scanner, "probe", return_value=observed):
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
        observed = {"status": "AV_VERIFIED", "video": True, "audio": True,
                    "streams": [{"codec_type": "video", "codec_name": "h264"},
                                {"codec_type": "audio", "codec_name": "aac"}]}
        with patch.object(scanner.urllib.request, "urlopen", return_value=FakeResponse()), patch.object(scanner, "probe", return_value=observed):
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


if __name__ == "__main__":
    unittest.main()
