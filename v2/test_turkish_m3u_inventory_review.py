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
    def test_foreign_name_with_turkish_speech_and_subtitles(self):
        with tempfile.TemporaryDirectory() as d:
            src, out, evidence = (Path(d) / n for n in ("in.m3u8", "out.jsonl", "evidence.jsonl"))
            src.write_text("#EXTM3U\n#EXTINF:-1,Global Network\nhttps://example.com/live\n")
            evidence.write_text(json.dumps({"playlist_ordinal": 1, "spoken_language": "tr",
                                            "subtitle_language": "tr", "stream_checked": True,
                                            "video_decoded": True, "audio_decoded": True}) + "\n")
            inventory_review(src, out, evidence)
            row = json.loads(out.read_text().strip())
            self.assertEqual(row["category"], "TURKISH_SPOKEN_REVIEW")
            self.assertTrue(row["turkish_subtitle_hint"])
            self.assertTrue(row["av_decoded_in_supplied_check"])
            self.assertFalse(row["working_channel_verified"])
    def test_reject_duplicate_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            src, out, evidence = (Path(d) / n for n in ("in.m3u8", "out.jsonl", "evidence.jsonl"))
            src.write_text("#EXTM3U\n#EXTINF:-1,TV\nhttps://example.com/live\n")
            row = json.dumps({"playlist_ordinal": 1, "spoken_language": "tr"}) + "\n"
            evidence.write_text(row + row)
            with self.assertRaises(ValueError):
                inventory_review(src, out, evidence)
            self.assertFalse(out.exists())
    def test_sampler_asr_hint_foreign_name_and_url_binding(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            src, out, evidence = (Path(d) / n for n in ("in.m3u8", "out.jsonl", "evidence.jsonl"))
            url = "https://example.com/live"
            src.write_text("#EXTM3U\n#EXTINF:-1,Global Network\n" + url + "\n")
            sample = {"url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                      "status": "AV_SAMPLED_REVIEW_REQUIRED", "video_decoded": True,
                      "audio_decoded": True, "spoken_turkish_hint": True,
                      "subtitle_turkish_hint": False}
            evidence.write_text(json.dumps({"playlist_ordinal": 1, "sample_report": sample}) + "\n")
            inventory_review(src, out, evidence)
            row = json.loads(out.read_text())
            self.assertEqual(row["category"], "ASR_TURKISH_HINT_REVIEW")
            self.assertTrue(row["sampler_spoken_turkish_hint"])
            self.assertFalse(row["language_evidence_verified"])
            self.assertFalse(row["working_channel_verified"])
            self.assertNotIn(url, out.read_text())
            out.unlink()
            sample["url_sha256"] = "0" * 64
            evidence.write_text(json.dumps({"playlist_ordinal": 1, "sample_report": sample}) + "\n")
            with self.assertRaises(ValueError):
                inventory_review(src, out, evidence)
            self.assertFalse(out.exists())
    def test_unpaired_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d) / "in.m3u8", Path(d) / "out.jsonl"
            src.write_text("#EXTM3U\n#EXTINF:-1,Missing stream\n")
            with self.assertRaises(ValueError):
                inventory_review(src, out)
            self.assertFalse(out.exists())

if __name__ == "__main__":
    unittest.main()
