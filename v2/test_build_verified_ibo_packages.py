import json
import pathlib
import tempfile
import unittest
from build_verified_ibo_packages import eligible, make

class PackageAcceptance(unittest.TestCase):
    def test_unproven_rejected(self):
        self.assertFalse(eligible({"status":"AV_VERIFIED","video_proven":True,"audio_proven":False,"url":"https://example.org/a.m3u8"}))

    def test_insufficient_evidence_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            source=root/"evidence.jsonl"
            source.write_text(json.dumps({"status":"AV_VERIFIED","video_proven":True,"audio_proven":True,"url":"https://example.org/a.m3u8","tvg_id":"channel-a","name":"Test"})+"\n")
            report=make(source,root/"out")
            self.assertEqual(report["verified_unique_channels"],1)
            self.assertEqual(report["packages"]["1000"],"BLOCKED_INSUFFICIENT_AV_EVIDENCE")
            self.assertEqual(report["packages"]["2000"],"BLOCKED_INSUFFICIENT_AV_EVIDENCE")
            self.assertFalse((root/"out").exists())

    def test_duplicate_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            rows=[{"status":"AV_VERIFIED","video_proven":True,"audio_proven":True,"url":f"https://example.org/{i}.m3u8","tvg_id":"same","name":"Test"} for i in range(2)]
            source=root/"evidence.jsonl"
            source.write_text("\n".join(json.dumps(r) for r in rows)+"\n")
            self.assertEqual(make(source,root/"out")["verified_unique_channels"],1)

if __name__=="__main__":
    unittest.main()
