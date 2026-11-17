import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from v2.backup_text_batch import run

class BatchTests(unittest.TestCase):
    def test_bounded_deduplicated_readonly(self):
        with TemporaryDirectory() as d:
            p=Path(d); src=p/"snapshot.json"; out=p/"out.json"
            src.write_text(json.dumps({"candidates":[{"url":"https://example.org/live"},{"url":"https://example.org/live"},{"url":"https://example.org/other"}]}))
            with patch("v2.backup_text_batch.sample",return_value={"status":"NO_TEXT_EVIDENCE","language_evidence_verified":False}):
                self.assertEqual(run(src,out,1,2,True)["sampled"],1)
            self.assertEqual(len(json.loads(out.read_text())["results"]),1)
            self.assertNotIn("https://",out.read_text())
            with self.assertRaises(ValueError):
                run(src,out,1,2)
    def test_sampler_failure_isolated_and_next_channel_processed(self):
        with TemporaryDirectory() as d:
            p=Path(d); src=p/"snapshot.json"; out=p/"out.json"
            src.write_text(json.dumps({"candidates":[{"url":"https://example.org/a"},{"url":"https://example.org/b"}]}))
            with patch("v2.backup_text_batch.sample",side_effect=[RuntimeError("bad"),{"status":"HINTS_ONLY","raw_text":"SECRET","language_evidence_verified":True}]):
                self.assertEqual(run(src,out,2,2,True)["sampled"],2)
            result=json.loads(out.read_text())["results"]
            self.assertEqual(result[0]["status"],"SAMPLE_ERROR")
            self.assertEqual(result[1]["status"],"HINTS_ONLY")
            self.assertFalse(result[1]["language_evidence_verified"])
            self.assertNotIn("SECRET",out.read_text())

    def test_network_requires_opt_in(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            with self.assertRaisesRegex(ValueError,"opt-in"):
                run(p/"a",p/"b")

    def test_invalid_limit(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            with self.assertRaises(ValueError):
                run(p/"a",p/"b",17,8,True)
    def test_invalid_snapshot(self):
        with TemporaryDirectory() as d:
            p=Path(d); (p/"a").write_text("{}")
            with self.assertRaises(ValueError):
                run(p/"a",p/"b",1,8,True)
if __name__=="__main__":
    unittest.main()
