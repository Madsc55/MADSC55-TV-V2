import tempfile
import unittest
from pathlib import Path
from v2.stage2_unified_runner import run, TASKS, summarize_media

class Stage2Tests(unittest.TestCase):
    def test_end_to_end_offline(self):
        source={k:{"status":"OBSERVED"} for k in TASKS[:8]}
        record={"healthy_rounds":3,"rounds":[{"evidence":[{"full_sample":True,
                "language_review":{"asr":{"status":"TEST"},"ocr":{},"webvtt":{}}}]}]}
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"report"
            report=run(b"fixture",lambda:source.copy(),lambda:[record],out,"offline")
            self.assertEqual(set(report["tasks"]),set(TASKS))
            self.assertEqual(report["tasks"]["B19"]["three_round_av"],1)
            self.assertEqual(report["tasks"]["B30"]["selected"],0)
            self.assertFalse(report["production_accepted"])
            self.assertTrue((out/"stage2.md").exists())
    def test_live_hash_guard(self):
        with self.assertRaises(ValueError):
            run(b"fixture",lambda:{},lambda:[],Path("unused"),"live")
    def test_no_evidence_is_not_pass(self):
        self.assertEqual(summarize_media([])["B19"]["status"],"INCOMPLETE")
