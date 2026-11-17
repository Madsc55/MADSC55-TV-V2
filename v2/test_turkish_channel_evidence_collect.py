"""Offline tests for authorized YEDEKLER evidence collector."""
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    from . import turkish_channel_evidence_collect as collector
    collect = collector.collect
except ImportError:
    import turkish_channel_evidence_collect as collector
    collect = collector.collect

class EvidenceCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.playlist = self.root / "source.m3u8"
        self.playlist.write_text(
            "#EXTM3U\n"
            + "".join(f'#EXTINF:-1 group-title="OTHER",Channel {i}\nhttps://example.com/{i}.m3u8\n' for i in range(1,1004))
            + '#EXTINF:-1 group-title="YEDEKLER",Turkish TV\nhttps://example.com/1004.m3u8\n'
            + '#EXTINF:-1 group-title="OTHER",Foreign TV\nhttps://example.com/1005.m3u8\n',
            encoding="utf-8")
        self.output = self.root / "evidence.jsonl"

    def test_reject_without_authorization(self):
        with self.assertRaises(ValueError):
            collect(self.playlist, self.output, [1004])

    def test_reject_without_egress(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                collect(self.playlist, self.output, [1004], source_authorized=True)

    def test_protect_first_1003_and_non_yedekler(self):
        with patch.dict("os.environ", {"MADSC55_SECURE_EGRESS_CONFIRMED": "1"}):
            for ordinal in (1003,1005):
                with self.assertRaises(ValueError):
                    collect(self.playlist, self.output, [ordinal], source_authorized=True)

    def test_evidence_without_playlist_mutation(self):
        before = self.playlist.read_bytes()
        report = {"url_sha256":hashlib.sha256(b"https://example.com/1004.m3u8").hexdigest(), "status":"AV_INCOMPLETE",
                  "video_decoded":False, "audio_decoded":False,
                  "spoken_turkish_hint":False, "subtitle_turkish_hint":False}
        with patch.dict("os.environ", {"MADSC55_SECURE_EGRESS_CONFIRMED": "1"}), patch.object(collector, "review_one", return_value=report):
            result = collect(self.playlist, self.output, [1004], source_authorized=True)
        self.assertEqual(result["sampled"],1)
        self.assertEqual(json.loads(self.output.read_text())["playlist_ordinal"],1004)
        self.assertEqual(before,self.playlist.read_bytes())

if __name__ == "__main__":
    unittest.main()
