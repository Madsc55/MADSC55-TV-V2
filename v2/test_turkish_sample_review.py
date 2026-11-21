import datetime
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from v2.spoken_language_sample_review import transcribe_sample
from v2.turkish_media_sample_capture import capture
from v2.turkish_sample_review import archive_preview, review_sample
from v2.turkish_webvtt_evidence import review_decoded_cues


class SampleReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.sample = cls.root / "subtitled.mkv"
        subtitle = cls.root / "test.srt"
        subtitle.write_text("1\n00:00:00,000 --> 00:00:02,000\nBugün Türkçe altyazı okuyoruz.\n")
        subprocess.run([
            "ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
            "color=c=white:s=800x360:r=3:d=2", "-f", "lavfi", "-i", "sine=duration=2",
            "-i", str(subtitle), "-map", "0:v", "-map", "1:a", "-map", "2:s",
            "-vf", "drawtext=font='DejaVu Sans':text='Bugün Türkçe altyazı okuyoruz.':"
                   "fontsize=40:fontcolor=black:x=18:y=255",
            "-c:v", "mpeg4", "-c:a", "aac", "-c:s", "srt", "-metadata:s:s:0", "language=tur",
            "-threads", "1", str(cls.sample)], check=True, capture_output=True, timeout=20)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_decode_ocr_and_timed_track(self):
        report = review_sample(self.sample)
        self.assertTrue(report["video_decoded"] and report["audio_decoded"])
        self.assertTrue(report["picture"]["turkish_visible_text_hint"])
        self.assertGreater(report["picture"]["ocr_frames_completed"], 0)
        self.assertTrue(report["subtitle_tracks"][0]["tag_and_text_turkish_hint"])
        self.assertEqual(report["speech"]["status"], "ASR_NOT_REQUESTED")
        provenance = report["evidence_provenance"]
        self.assertEqual(provenance["sample_sha256"], report["sample_sha256"])
        self.assertEqual(provenance["source_identity"], "local_file_unattributed")
        self.assertFalse(provenance["source_identity_verified"])
        self.assertFalse(provenance["capture_receipt_authenticated"])
        self.assertFalse(provenance["capture_timestamp_trusted"])
        self.assertEqual(provenance["review_timestamp_source"], "local_system_clock")
        self.assertEqual(provenance["av_method"], "ffmpeg_local_audio_video_decode")
        self.assertEqual(provenance["ocr_method"], "tesseract_tur_psm6")
        self.assertEqual(provenance["subtitle_method"], "ffmpeg_webvtt_timed_cue_review")
        reviewed = datetime.datetime.fromisoformat(provenance["reviewed_at_utc"].replace("Z", "+00:00"))
        self.assertIsNotNone(reviewed.tzinfo)
        self.assertIsNone(provenance["asr_confidence"])
        self.assertFalse(report["non_turkish_speech_with_turkish_cues_hint"])
        self.assertFalse(report["triage"]["working_channel_verified"])
        self.assertNotIn("okuyoruz", json.dumps(report, ensure_ascii=False))

    def test_foreign_speech_with_timed_turkish_cues(self):
        speech = {"speech_detected": True, "detected_language": "en"}
        with patch("v2.turkish_sample_review.review_audio", return_value=(True, speech)):
            report = review_sample(self.sample, origin_country="TR")
        self.assertTrue(report["non_turkish_speech_with_turkish_cues_hint"])
        self.assertFalse(report["triage"]["source_country_verified"])
        self.assertFalse(report["review_approved"])

    def test_timing_metadata_and_text_are_separate(self):
        for body in ["NOTE\n00:00.000 --> 00:01.000\nTürkçe",
                     "00:02.000 --> 00:01.000\nTürkçe", "00:15.000 --> 00:16.000\nTürkçe",
                     "00:00.000 --> 00:01.000\n<c.Türkçe></c>"]:
            with self.subTest(body=body):
                self.assertEqual(review_decoded_cues("WEBVTT\n\n" + body, "tur", 12000)["cue_count"], 0)
        cue = "WEBVTT\n\n00:00.000 --> 00:01.000\nGood morning"
        self.assertFalse(review_decoded_cues(cue, "tur", 12000)["tag_and_text_turkish_hint"])

    def test_failed_decode_and_missing_model_are_inconclusive(self):
        invalid = self.root / "invalid.mkv"
        invalid.write_bytes(b"not a Matroska file")
        report = review_sample(invalid)
        self.assertFalse(report["video_decoded"] or report["audio_decoded"])
        self.assertFalse(report["triage"]["working_channel_verified"])
        self.assertEqual(review_sample(self.sample, self.root / "missing")["speech"]["status"],
                         "ASR_LOCAL_MODEL_UNAVAILABLE")

    def test_silence_and_invalid_language_probability(self):
        info = SimpleNamespace(language="tr", language_probability=0.97)
        model = SimpleNamespace(transcribe=lambda *a, **k: ([], info))
        self.assertFalse(transcribe_sample("unused", model)["speech_detected"])
        info.language_probability = float("nan")
        with self.assertRaises(ValueError):
            transcribe_sample("unused", model)

    def test_capture_receipt_and_archive_identity(self):
        url = "https://8.8.8.8/example"
        captured = self.root / "capture.mkv"
        def run(command, **kwargs):
            self.assertIn("0:s?", command)
            Path(command[-1]).write_bytes(self.sample.read_bytes())
            return SimpleNamespace(returncode=0)
        body = self.sample.read_bytes()
        class Response:
            status = 200
            def __init__(self):
                import io
                self.source = io.BytesIO(body)
            def getheader(self, name):
                return {"content-type": "video/x-matroska",
                        "content-length": str(len(body))}.get(name.lower())
            def read(self, count):
                return self.source.read(count)
        class Connection:
            sock = None
            def __init__(self, host, port, pinned_ip, timeout):
                self.pinned_ip = pinned_ip
            def request(self, method, target, headers):
                self.headers = headers
            def getresponse(self):
                return Response()
            def close(self):
                pass
        receipt = capture(url, captured, include_subtitles=True, which=lambda name: name,
                          runner=run, connection_factory=Connection)
        with self.assertRaises(ValueError):
            review_sample(captured, capture_receipt={**receipt, "sample_sha256": "0" * 64})
        report = review_sample(captured, capture_receipt=receipt)
        self.assertEqual(report["evidence_provenance"]["url_sha256"], receipt["url_sha256"])
        self.assertEqual(report["evidence_provenance"]["captured_at_utc"], receipt["captured_at_utc"])
        self.assertEqual(report["evidence_provenance"]["capture_method_claimed"], "bounded_ffmpeg_http_capture")
        self.assertFalse(report["evidence_provenance"]["capture_receipt_authenticated"])
        self.assertFalse(report["evidence_provenance"]["capture_timestamp_trusted"])
        bad_time = {**receipt, "captured_at_utc": "2026-11-21T09:00:00"}
        with self.assertRaisesRegex(ValueError, "timezone"):
            review_sample(captured, capture_receipt=bad_time)
        # Use only temporary text inputs for the read-only archive lookup.
        source = self.root / "source.txt"
        source.write_text("#EXTM3U\n#EXTINF:-1,Example\n" + url + "\n")
        state_path = self.root / "state.json"
        state_path.write_text(json.dumps({"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                          "status": {"1": "TEST"}}))
        kw = {"archive": source, "state_path": state_path}
        self.assertIsNone(archive_preview(report, **kw)["target"])
        decision = {"sample_sha256": report["sample_sha256"], "url_sha256": report["url_sha256"],
                    "target": "TURK", "basis": "saw_turkish_subtitles", "reviewed_by": "fixture"}
        self.assertEqual(archive_preview(report, decision=decision, **kw)["source_ordinal"], 1)
        for field, value in [("sample_sha256", "0" * 64), ("target", "YABANCI"), ("reviewed_by", "")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                archive_preview(report, decision={**decision, field: value}, **kw)
        with self.assertRaises(ValueError):
            archive_preview({**report, "url_sha256": "0" * 64}, **kw)
        state_path.write_text(state_path.read_text().replace('"TEST"', '"TURK"'))
        with self.assertRaises(ValueError):
            archive_preview(report, decision=decision, **kw)
        source.write_text(source.read_text() + url + "\n")
        with self.assertRaises(ValueError):
            archive_preview(report, **kw)
