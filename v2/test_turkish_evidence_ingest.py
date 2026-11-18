import json
import tempfile
import unittest
from pathlib import Path
from v2.turkish_evidence_ingest import evaluate_record, evaluate_file

class EvidenceIngestTests(unittest.TestCase):
    def test_asr_provenance_is_required(self):
        with self.assertRaises(ValueError):
            evaluate_record({"name": "Haber", "spoken_language": "tr"})
    def test_asr_does_not_approve(self):
        r = evaluate_record({"name": "Haber", "spoken_language": "tr", "evidence_sources": ["asr"]})
        self.assertEqual(r["category"], "TURKISH_SPOKEN_REVIEW")
        self.assertFalse(r["review_approved"])
    def test_subtitle_requires_provenance(self):
        with self.assertRaises(ValueError):
            evaluate_record({"name": "TV", "subtitle_language": "tr"})
    def test_subtitle_only_is_not_spoken(self):
        r = evaluate_record({"name": "TV", "subtitle_language": "tr", "evidence_sources": ["webvtt"]})
        self.assertFalse(r["turkish_spoken_hint"])
    def test_av_requires_decoder(self):
        with self.assertRaises(ValueError):
            evaluate_record({"name": "TV", "video_decoded": True})
    def test_ffprobe_alone_cannot_claim_decoded_video(self):
        with self.assertRaises(ValueError):
            evaluate_record({"name": "TV", "video_decoded": True, "evidence_sources": ["ffprobe"]})
    def test_ffprobe_alone_cannot_claim_decoded_audio(self):
        with self.assertRaises(ValueError):
            evaluate_record({"name": "TV", "audio_decoded": True, "evidence_sources": ["ffprobe"]})
    def test_ffprobe_can_report_metadata_only(self):
        r = evaluate_record({"name": "TV", "stream_checked": True, "evidence_sources": ["ffprobe"]})
        self.assertFalse(r["av_decoded_in_supplied_check"])
    def test_unknown_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            evaluate_record({"name": "TV", "review_approved": True})
    def test_file_is_read_only_review(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d)/"input.json", Path(d)/"output.json"
            src.write_text(json.dumps([{"name": "TV", "evidence_sources": []}]))
            self.assertEqual(evaluate_file(src, dst), 1)
            result = json.loads(dst.read_text())
            self.assertEqual(result["approved"], 0)
            self.assertFalse(result["playlist_modified"])
    def test_invalid_batch_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d)/"input.json", Path(d)/"output.json"
            src.write_text(json.dumps([{"name": "TV"}, {"name": "TV", "spoken_language": "tr"}]))
            with self.assertRaises(ValueError):
                evaluate_file(src, dst)
            self.assertFalse(dst.exists())

if __name__ == "__main__":
    unittest.main()
