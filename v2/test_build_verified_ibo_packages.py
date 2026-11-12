import json
import pathlib
import tempfile
import unittest
from build_verified_ibo_packages import eligible, make

def fixture(url):
    return {"status":"AV_VERIFIED","video_proven":True,"audio_proven":True,"url":url,
            "av_evidence":{"url":url,"video":True,"audio":True,"sha256":"a"*64,"captured_at":"2026-11-12T12:00:00Z"}}

class PackageAcceptance(unittest.TestCase):
    def test_untraceable_flags_rejected(self):
        self.assertFalse(eligible({"status":"AV_VERIFIED","video_proven":True,"audio_proven":True,"url":"https://example.org/a.m3u8"}))

    def test_unproven_rejected(self):
        self.assertFalse(eligible({"status":"AV_VERIFIED","video_proven":True,"audio_proven":False,"url":"https://example.org/a.m3u8"}))

    def test_insufficient_evidence_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            source=root/"evidence.jsonl"
            source.write_text(json.dumps({**fixture("https://example.org/a.m3u8"),"tvg_id":"channel-a","name":"Test"})+"\n")
            report=make(source,root/"out")
            self.assertEqual(report["verified_unique_channels"],1)
            self.assertEqual(report["packages"]["1000"],"BLOCKED_INSUFFICIENT_AV_EVIDENCE")
            self.assertEqual(report["packages"]["2000"],"BLOCKED_INSUFFICIENT_AV_EVIDENCE")
            self.assertFalse((root/"out").exists())

    def test_duplicate_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            rows=[{**fixture(f"https://example.org/{i}.m3u8"),"tvg_id":"same","name":"Test"} for i in range(2)]
            source=root/"evidence.jsonl"
            source.write_text("\n".join(json.dumps(r) for r in rows)+"\n")
            self.assertEqual(make(source,root/"out")["verified_unique_channels"],1)

    def test_1000_and_2000_m3u_integrity_with_synthetic_fixtures_only(self):
        # Synthetic records exercise formatting; they are NEVER production evidence.
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            source=root/"fixture.jsonl"
            rows=[{**fixture(f"https://example.org/{i}.m3u8"),"tvg_id":f"test-{i}",
                   "name":f"Fixture {i}","group":"Tests"} for i in range(2000)]
            source.write_text("\n".join(json.dumps(r) for r in rows)+"\n")
            result=make(source,root/"out")
            self.assertEqual(result["verified_unique_channels"],2000)
            for count in (1000,2000):
                path=root/"out"/f"IBO_AV_VERIFIED_{count}.m3u8"
                lines=path.read_text().splitlines()
                self.assertEqual(lines[0],"#EXTM3U")
                self.assertEqual(len(lines),1+2*count)
                self.assertEqual(len(set(lines[2::2])),count)
                self.assertTrue(all(line.startswith("#EXTINF:") for line in lines[1::2]))
                self.assertTrue(all(line.startswith("https://") for line in lines[2::2]))

if __name__=="__main__":
    unittest.main()
