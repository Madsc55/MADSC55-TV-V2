import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from v2.backup_archive_offline import run

class OfflineTests(unittest.TestCase):
    def test_roundtrip_without_raw_url(self):
        with TemporaryDirectory() as d:
            d=Path(d)
            k=hashlib.sha256(b"channel").hexdigest()
            (d/"inventory.json").write_text(json.dumps({"channels":[{"url_sha256":k,"name":"Test"}]}))
            (d/"playback.json").write_text(json.dumps({"by_url_sha256":{k:{"playback":"VIDEO_DECODED","audio":"AUDIO_DECODED","decoded_av_verified":True}}}))
            (d/"language.json").write_text(json.dumps({"by_url_sha256":{k:{"language":"TR","language_evidence_verified":True,"review_approved":True}}}))
            result=run(d/"inventory.json",d/"playback.json",d/"language.json",d/"result.json",1)
            self.assertEqual(result["counts"]["TURK_WORKING"],1)
            self.assertNotIn("Test",(d/"result.json").read_text())

    def test_refuses_overwrite(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"input.json"
            p.write_text("{}")
            with self.assertRaises(ValueError):
                run(p,p,p,p,1)

    def test_refuses_existing_output_without_changing_it(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            original=p/"report.json"
            original.write_text("PROTECTED",encoding="utf-8")
            for name in ("inventory.json","playback.json","language.json"):
                (p/name).write_text("{}",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"overwrite"):
                run(p/"inventory.json",p/"playback.json",p/"language.json",original,1)
            self.assertEqual(original.read_text(encoding="utf-8"),"PROTECTED")

    def test_direct_cli_import_works(self):
        script=Path(__file__).with_name("backup_archive_offline.py")
        result=subprocess.run([sys.executable,str(script),"--help"],
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("--expected-count",result.stdout)

if __name__ == "__main__":
    unittest.main()
