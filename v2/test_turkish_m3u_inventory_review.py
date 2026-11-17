import json
import tempfile
import unittest
from pathlib import Path
from v2.turkish_m3u_inventory_review import inventory_review

class M3UInventoryReviewTests(unittest.TestCase):
    def test_source_preserved_and_urls_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d) / "in.m3u8", Path(d) / "review.jsonl"
            src.write_text('#EXTM3U\n#EXTINF:-1 group-title="YEDEKLER",Haber Global\nhttps://example.com/private.m3u8\n#EXTINF:-1,TRT World\nhttps://example.com/other.m3u8\n')
            before = src.read_bytes()
            r = inventory_review(src, out)
            self.assertEqual(r["channels"], 2)
            self.assertEqual(src.read_bytes(), before)
            data = out.read_text()
            self.assertNotIn("example.com", data)
            rows = [json.loads(x) for x in data.splitlines()]
            self.assertEqual(rows[0]["playlist_ordinal"], 1)
            self.assertEqual(rows[0]["source_group"], "YEDEKLER")
            self.assertEqual(rows[1]["playlist_ordinal"], 2)
            self.assertFalse(rows[0]["review_approved"])
            with self.assertRaises(FileExistsError):
                inventory_review(src, out)
    def test_unpaired_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d) / "in.m3u8", Path(d) / "out.jsonl"
            src.write_text("#EXTM3U\n#EXTINF:-1,Missing stream\n")
            with self.assertRaises(ValueError):
                inventory_review(src, out)
            self.assertFalse(out.exists())

if __name__ == "__main__":
    unittest.main()
