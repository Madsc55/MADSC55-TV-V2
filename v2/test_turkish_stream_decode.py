import subprocess
import unittest
from unittest.mock import patch

from v2.turkish_stream_decode import decode


class DecodeEvidenceTests(unittest.TestCase):
    ITEM = {"channel_id": "fixture-channel", "url": "https://example.invalid/live"}

    @patch("v2.turkish_stream_decode.subprocess.run")
    def test_requires_both_video_and_audio_frames(self, run):
        run.return_value = subprocess.CompletedProcess(
            ["ffmpeg"], 0,
            stderr="[Parsed_showinfo_0 @ x] n: 0 pts: 0\n"
                   "[Parsed_ashowinfo_1 @ x] n:0 pts:0\n")
        result = decode(self.ITEM)
        self.assertEqual(result["status"], "SHORT_DECODE_VERIFIED")
        self.assertEqual(result["media_types"], ["audio", "video"])
        command = run.call_args.args[0]
        self.assertIn("showinfo", command)
        self.assertIn("ashowinfo", command)

    @patch("v2.turkish_stream_decode.subprocess.run")
    def test_zero_exit_without_video_frame_is_not_verified(self, run):
        run.return_value = subprocess.CompletedProcess(
            ["ffmpeg"], 0, stderr="[Parsed_ashowinfo_1 @ x] n:0 pts:0\n")
        self.assertEqual(decode(self.ITEM)["status"], "DECODE_UNVERIFIED")

    @patch("v2.turkish_stream_decode.subprocess.run")
    def test_zero_exit_without_audio_frame_is_not_verified(self, run):
        run.return_value = subprocess.CompletedProcess(
            ["ffmpeg"], 0, stderr="[Parsed_showinfo_0 @ x] n: 0 pts: 0\n")
        self.assertEqual(decode(self.ITEM)["status"], "DECODE_UNVERIFIED")

    @patch("v2.turkish_stream_decode.subprocess.run")
    def test_nonzero_exit_is_not_verified_even_with_frame_logs(self, run):
        run.return_value = subprocess.CompletedProcess(
            ["ffmpeg"], 1,
            stderr="[Parsed_showinfo_0 @ x] n: 0 pts: 0\n"
                   "[Parsed_ashowinfo_1 @ x] n:0 pts:0\n")
        self.assertEqual(decode(self.ITEM)["status"], "DECODE_UNVERIFIED")

    @patch("v2.turkish_stream_decode.subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 18))
    def test_timeout_is_unverified(self, run):
        self.assertEqual(decode(self.ITEM)["status"], "DECODE_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
