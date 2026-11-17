import json
import tempfile
import unittest
from pathlib import Path
from v2.turkish_channel_batch_review import prepare_review

class BatchReviewTests(unittest.TestCase):
    def test_read_only_classification_and_no_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "evidence.jsonl"
            target = Path(directory) / "review.jsonl"
            records = [
                {"name": "Haber Global", "spoken_language": "tr"},
                {"name": "TRT World", "origin_country": "TR", "spoken_language": "en"},
                {"name": "Global Cinema", "subtitle_language": "tr"},
            ]
            source.write_text("".join(json.dumps(r) + "\n" for r in records))
            before = source.read_bytes()
            result = prepare_review(source, target)
            self.assertEqual(result["reviewed"], 3)
            self.assertEqual(result["approved"], 0)
            self.assertEqual(before, source.read_bytes())
            rows = [json.loads(s) for s in target.read_text().splitlines()]
            self.assertEqual(rows[0]["category"], "TURKISH_SPOKEN_REVIEW")
            self.assertEqual(rows[1]["category"], "TURKEY_OR_NORTHERN_CYPRUS_ORIGIN_REVIEW")
            self.assertEqual(rows[2]["category"], "TURKISH_SUBTITLED_REVIEW")
            self.assertFalse(any(r["playlist_modified"] for r in rows))
            with self.assertRaises(FileExistsError):
                prepare_review(source, target)
    def test_reject_raw_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "evidence.jsonl"
            target = Path(directory) / "review.jsonl"
            source.write_text(json.dumps({"name": "TV", "url": "https://example.com/x"}) + "\n")
            with self.assertRaises(ValueError):
                prepare_review(source, target)
            self.assertFalse(target.exists())
    def test_reject_same_input_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.jsonl"
            path.write_text("")
            with self.assertRaises(ValueError):
                prepare_review(path, path)

if __name__ == "__main__":
    unittest.main()
