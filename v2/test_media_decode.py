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

    def test_invalid_timeout_type_fails_closed(self):
        with patch("media_decode.subprocess.run") as run:
            for timeout in (None, "20", [], {}, True, False, float("nan"), float("inf"), float("-inf")):
                self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}, timeout=timeout))
            run.assert_not_called()

    @patch("media_decode.subprocess.run")
    def test_manifest_only_is_not_decode(self, run):
        run.return_value = CompletedProcess([], 0, "#format: frame checksums\n", "")
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))

    @patch("media_decode.subprocess.run")
    def test_frame_checksum_proves_decode(self, run):
        run.return_value = CompletedProcess([], 0, "#format: frame checksums\n#media_type 0: video\n#media_type 1: audio\n0, 0, 0, 1, 123, 0123456789abcdef\n1, 0, 0, 1, 123, abcdef0123456789\n", "")
        self.assertTrue(decode_media({"url": "https://example.org/live.m3u8"}))
        self.assertNotIn("-frames:v", run.call_args.args[0])
        self.assertNotIn("-frames:a", run.call_args.args[0])
        self.assertIn("-t", run.call_args.args[0])

    def test_real_ffmpeg_frame_muxer_emits_video_and_audio(self):
        """Exercise real FFmpeg: one audio frame used to terminate before video."""
        import shutil
        import subprocess
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg not installed")
        command = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
                   "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=25",
                   "-f", "lavfi", "-i", "sine=frequency=440",
                   "-map", "0:v:0", "-map", "1:a:0",
                   "-frames:v", "1", "-t", "3", "-f", "framemd5", "-"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("#media_type 0: video", result.stdout)
        self.assertIn("#media_type 1: audio", result.stdout)
        frames = [line.split(",", 1)[0].strip() for line in result.stdout.splitlines()
                  if line and not line.startswith("#")]
        self.assertIn("0", frames)
        self.assertIn("1", frames)

    def test_delayed_audio_is_decoded_before_bounded_end(self):
        """Real FFmpeg regression: audio starts after the first video frame."""
        import shutil
        import subprocess
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg not installed")
        command = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
                   "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=25",
                   "-f", "lavfi", "-i", "sine=frequency=440",
                   "-filter_complex", "[1:a]adelay=500|500[a]",
                   "-map", "0:v:0", "-map", "[a]",
                   "-t", "2", "-f", "framemd5", "-"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        media = {}
        frames = set()
        for line in result.stdout.splitlines():
            if line.startswith("#media_type "):
                index, kind = line[len("#media_type "):].split(":", 1)
                media[int(index)] = kind.strip()
            elif line and not line.startswith("#"):
                fields = [field.strip() for field in line.split(",")]
                if len(fields) >= 6 and fields[0].isdigit() and fields[4].isdigit() and int(fields[4]) > 0:
                    frames.add(media.get(int(fields[0])))
        self.assertEqual(frames, {"video", "audio"})

    @patch("media_decode.subprocess.run")
    def test_video_only_checksum_is_not_av(self, run):
        run.return_value = CompletedProcess([], 0, "#media_type 0: video\n0, 0, 0, 1, 123, 0123456789abcdef\n", "")
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))

    @patch("media_decode.subprocess.run")
    def test_declared_audio_without_decoded_audio_is_not_av(self, run):
        run.return_value = CompletedProcess([], 0, "#media_type 0: video\n#media_type 1: audio\n0, 0, 0, 1, 123, 0123456789abcdef\n", "")
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))

    @patch("media_decode.subprocess.run")
    def test_zero_length_audio_frame_is_not_av(self, run):
        run.return_value = CompletedProcess([], 0, "#media_type 0: video\n#media_type 1: audio\n0, 0, 0, 1, 123, 0123456789abcdef\n1, 0, 0, 1, 0, abcdef0123456789\n", "")
        self.assertFalse(decode_media({"url": "https://example.org/live.m3u8"}))

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
