import unittest
from unittest.mock import patch
from subprocess import CompletedProcess, TimeoutExpired
from media_decode import decode_media


class DecodeTests(unittest.TestCase):
    def test_rejects_private_and_file_urls(self):
        for url in ("file:///etc/passwd", "http://127.0.0.1/a.m3u8", "http://localhost/a.m3u8"):
            with patch("media_decode.subprocess.run") as run:
                self.assertFalse(decode_media({"url": url}))
                run.assert_not_called()

    @patch("media_decode.subprocess.run")
    def test_manifest_only_is_not_decode(self, run):
        run.return_value = CompletedProcess([], 0, "#format: frame checksums\n", "")
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))

    @patch("media_decode.subprocess.run")
    def test_frame_checksum_proves_decode(self, run):
        run.return_value = CompletedProcess([], 0, "#format: frame checksums\n#media_type 0: video\n0, 0, 0, 1, 123, 0123456789abcdef\n", "")
        self.assertTrue(decode_media({"url": "https://example.org/live.m3u8"}))
        self.assertIn("-frames:v", run.call_args.args[0])

    @patch("media_decode.subprocess.run")
    def test_audio_only_checksum_is_not_video(self, run):
        run.return_value = CompletedProcess([], 0, "#media_type 0: audio\n0, 0, 0, 1, 123, 0123456789abcdef\n", "")
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))

    @patch("media_decode.subprocess.run")
    def test_timeout_fails_closed(self, run):
        run.side_effect = TimeoutExpired("ffmpeg", 2)
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))

    @patch("media_decode.subprocess.run")
    def test_nonzero_exit_fails_closed(self, run):
        run.return_value = CompletedProcess([], 1, "", "error")
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
