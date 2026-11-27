import json
import tempfile
import unittest
from pathlib import Path
from foreign_archive_plan import next_group
from nonforeign_fresh_full import inventory
from foreign_archive_batch import batch, digest

class ForeignAuditTests(unittest.TestCase):
    def test_scope_and_resume(self):
        raw=('#EXTM3U\n#EXTINF:-1 group-title="YABANCI ARŞİVİ (2)",TRT\nhttps://example.org/a\n'
             '#EXTINF:-1 group-title="YABANCI ARŞİVİ (2)",TV\nhttps://example.org/b\n').encode()
        self.assertEqual(len(inventory(raw,"foreign")),2)
        def probe(row):
            return {**{k:v for k,v in row.items() if k!="url"},"rounds":[{}, {}, {}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"batch-0.json"
            first=batch(raw,0,p,probe,expected=2)
            self.assertTrue(first["complete"])
            self.assertEqual(batch(raw,0,p,lambda _:self.fail("retested"),resume=p,expected=2),first)
    def test_plan_rejects_stale(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            self.assertEqual(next_group(p,"a"),list(range(20)))
            (p/"batch-0.json").write_text(json.dumps({"playlist_sha256":"b","batch":0,"scope":"foreign"}))
            with self.assertRaises(ValueError):
                next_group(p,"a")
