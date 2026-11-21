import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from stream_probe import probe, verify_decoded_av


class StreamProbeTests(unittest.TestCase):
    def test_malformed_url_types(self):
        for value in (None, 7, [], {}, "", "   "):
            with self.subTest(value=value):
                self.assertEqual(probe(value)["status"], "INVALID_URL")

    def test_invalid_and_ambiguous_urls(self):
        bad = (
            "file:///etc/passwd",
            "https://u:p@example.com/x",
            "https://stream.example:53/live",
            "https://stream.example/live#fragment",
            "https://%31%32%37.0.0.1/live",
            r"https://stream.example\@127.0.0.1/live",
            "https://stream.example/line\nfeed",
        )
        for value in bad:
            with self.subTest(value=value):
                self.assertEqual(probe(value)["status"], "INVALID_URL")

    @patch("stream_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("stream_probe.subprocess.run")
    def test_probe_reports_stream_metadata_without_claiming_decode(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
            {"codec_type": "audio", "codec_name": "aac"},
        ]}), "")
        result = probe("https://example.org/live.m3u8")
        self.assertEqual(result["status"], "AV_STREAMS_PRESENT")
        self.assertFalse(result["decoded_av_verified"])
        self.assertTrue(result["video"] and result["audio"])
        self.assertNotIn("example.org", str(result))

    @patch("stream_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("stream_probe.subprocess.run")
    def test_probe_command_restricts_protocols_redirects_and_tls(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]}), "")
        with patch("stream_probe._egress_guard_installed", return_value=True):
            result = probe("https://example.org/live.m3u8", require_guard=True)
        self.assertEqual(result["status"], "AV_STREAMS_PRESENT")
        command = run.call_args.args[0]
        self.assertIn("-protocol_whitelist", command)
        self.assertIn("http,https,tcp,tls,crypto", command)
        self.assertIn("-max_redirects", command)
        self.assertIn("-tls_verify", command)

    @patch("stream_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("stream_probe.subprocess.run")
    def test_video_only_is_not_verified(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"streams": [
            {"codec_type": "video", "codec_name": "h264"},
        ]}), "")
        self.assertEqual(probe("https://example.org/live.m3u8")["status"], "VIDEO_ONLY")

    @patch("stream_probe.shutil.which", return_value="/usr/bin/ffprobe")
    @patch("stream_probe.subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 5))
    def test_timeout(self, run, which):
        self.assertEqual(probe("https://example.org/live.m3u8")["status"], "TIMEOUT")

    def test_retry_probe_fails_closed_without_installed_guard(self):
        with patch("stream_probe._egress_guard_installed", return_value=False), \
             patch("stream_probe.subprocess.run") as run:
            result = probe("https://stream.example/live.m3u8", require_guard=True)
        self.assertEqual(result["status"], "EGRESS_GUARD_REQUIRED")
        run.assert_not_called()

    def test_retry_decode_fails_closed_without_installed_guard(self):
        with patch("stream_probe._egress_guard_installed", return_value=False), \
             patch("stream_probe.subprocess.run") as run:
            result = verify_decoded_av("https://stream.example/live.m3u8", require_guard=True)
        self.assertEqual(result["decode_status"], "EGRESS_GUARD_REQUIRED")
        run.assert_not_called()

    def test_decode_command_restricts_protocols_redirects_and_tls(self):
        frame = "0, 0, 1, 1, 1000, abcdef\n"
        completed = SimpleNamespace(returncode=0, stdout=frame, stderr="")
        with patch("stream_probe._egress_guard_installed", return_value=True), \
             patch("stream_probe.shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("stream_probe.subprocess.run", side_effect=[completed, completed]) as run:
            result = verify_decoded_av("https://stream.example/live.m3u8", require_guard=True)
        self.assertTrue(result["decoded_av_verified"])
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            command = call.args[0]
            self.assertIn("-protocol_whitelist", command)
            self.assertIn("http,https,tcp,tls,crypto", command)
            self.assertIn("-max_redirects", command)
            self.assertIn("-tls_verify", command)


if __name__ == "__main__":
    unittest.main()
