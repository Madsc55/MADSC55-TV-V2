import json
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from stage5_evidence_export import entries, run

class Stage5Acceptance(unittest.TestCase):
    def test_no_synthetic_or_unverified_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            source, protected, evidence, output = (p/x for x in ("source.m3u8","protected.m3u8","evidence.json","out.m3u8"))
            source.write_text("#EXTM3U\n#EXTINF:-1,One\nhttps://example.org/one.m3u8\n")
            protected.write_text("#EXTM3U\n#EXTINF:-1,Original\nhttps://example.org/original.m3u8\n")
            evidence.write_text(json.dumps([{"url":"https://example.org/one.m3u8","video_verified":True,"audio_verified":True,"ibo_playback_verified":False,"evidence_ref":"fixture-not-real","channel_id":"one"}]))
            args = Namespace(source=source, protected=protected, evidence=evidence, output=output, target=1000)
            with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REAL_EVIDENCE"):
                run(args)
            self.assertFalse(output.exists())
            self.assertIn("Original", protected.read_text())
    def test_fake_boolean_evidence_does_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            source, protected, evidence, output = (p/x for x in ("source.m3u8","protected.m3u8","evidence.json","out.m3u8"))
            source.write_text("#EXTM3U\\n#EXTINF:-1,One\\nhttps://example.org/one.m3u8\\n")
            protected.write_text("#EXTM3U\\n#EXTINF:-1,Original\\nhttps://example.org/original.m3u8\\n")
            evidence.write_text(json.dumps([{"url":"https://example.org/one.m3u8","video_verified":True,"audio_verified":True,"ibo_playback_verified":True,"evidence_ref":"invented","channel_id":"one","evidence_file":"nonexistent.mp4","evidence_sha256":"0"*64}]))
            args = Namespace(source=source, protected=protected, evidence=evidence, output=output, target=1000)
            with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REAL_EVIDENCE: 0/1000"):
                run(args)
            self.assertFalse(output.exists())

    def test_reject_malformed_m3u(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"bad.m3u8"
            p.write_text("#EXTM3U\n#EXTINF:-1,Missing\n")
            with self.assertRaises(ValueError):
                entries(p)

if __name__ == "__main__":
    unittest.main()
