#!/usr/bin/env python3
import json
import subprocess
import unittest
from unittest.mock import patch
from media_probe import probe

class ProbeTests(unittest.TestCase):
    def test_reject_non_http(self):
        self.assertEqual(probe("file:///etc/passwd")["status"], "INVALID_URL")

    @patch("media_probe.subprocess.run")
    def test_media_confirmed(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps({"streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"}]})
        result = probe("https://example.org/live.m3u8")
        self.assertEqual(result["status"], "MEDIA_CONFIRMED")
        self.assertEqual(len(result["streams"]), 2)

    @patch("media_probe.subprocess.run")
    def test_no_media(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps({"streams": []})
        self.assertEqual(probe("https://example.org/live.m3u8")["status"], "NO_MEDIA_STREAM")

    @patch("media_probe.subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 1))
    def test_timeout(self, run):
        self.assertEqual(probe("https://example.org/live.m3u8")["status"], "PROBE_TIMEOUT")

if __name__ == "__main__":
    unittest.main()
