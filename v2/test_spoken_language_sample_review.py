import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from v2.spoken_language_sample_review import run, valid_url

class SpeechSampleSafetyTests(unittest.TestCase):
    def test_rejects_local_and_embedded_credential_urls(self):
        for url in ("http://127.0.0.1/live", "http://169.254.169.254/latest",
                    "https://user:pass@example.org/live", "file:///etc/passwd"):
            with self.subTest(url=url):
                self.assertFalse(valid_url(url))

    def test_refuses_existing_output_before_model_loading(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)
            out=p/"existing.json"
            out.write_text("PROTECTED")
            with patch.object(sys,"argv",["speech","--output",str(out)]):
                with self.assertRaises(SystemExit):
                    run()
            self.assertEqual(out.read_text(),"PROTECTED")

    def test_speech_workflow_checks_current_playlist_not_stale_sha(self):
        source=(Path(__file__).resolve().parents[1] /
                ".github/workflows/v2-spoken-language-existing-snapshot.yml").read_text(encoding="utf-8")
        self.assertIn("git rev-parse HEAD:MADSC55_TV_IBO_CALISANLAR_TEST.m3u8", source)
        self.assertIn("persist-credentials: false", source)
        self.assertNotIn("4b1c3cea4b5107a425abab60f62d41f9f81e05a7", source)

    def test_unsafe_dns_rejected_before_asr_model_load(self):
        import hashlib
        import types
        from unittest.mock import Mock
        with TemporaryDirectory() as directory:
            p=Path(directory)
            url="https://example.org/live"
            digest=hashlib.sha256(url.encode("utf-8")).hexdigest()
            snapshot=p/"snapshot.json"
            playback=p/"playback.json"
            output=p/"new.json"
            snapshot.write_text(json.dumps({"candidates":[{"url":url}]}))
            playback.write_text(json.dumps({"coverage_complete":True,
                "channel_results":[{"url_sha256":digest,"playback":"VIDEO_DECODED",
                                    "audio":"AUDIO_DECODED"}]}))
            model=Mock(side_effect=AssertionError("Model must not load"))
            with patch.dict("os.environ", {"MADSC55_SECURE_EGRESS_CONFIRMED":"1"}):
                with patch("v2.spoken_language_sample_review.public_dns_for_url",return_value=False):
                    with patch.dict(sys.modules,{"faster_whisper":types.SimpleNamespace(WhisperModel=model)}):
                        with patch.object(sys,"argv",["speech","--snapshot",str(snapshot),
                            "--playback",str(playback),"--output",str(output)]):
                            with self.assertRaisesRegex(SystemExit,"Unsafe or unresolvable DNS"):
                                run()
            model.assert_not_called()
            self.assertFalse(output.exists())

    def test_rejects_snapshot_playback_identity_mismatch(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)
            snapshot=p/"snapshot.json"
            playback=p/"playback.json"
            snapshot.write_text(json.dumps({"candidates":[{"url":"https://example.org/a"}]}))
            playback.write_text(json.dumps({"coverage_complete":True,
                "channel_results":[{"url_sha256":"a"*64}]}))
            # The model dependency is optional; inject a stub module to reach
            # identity validation, which must fail before any stream fetch.
            import types
            with patch.dict(sys.modules,{"faster_whisper":types.SimpleNamespace(WhisperModel=object)}):
                with patch.object(sys,"argv",["speech","--snapshot",str(snapshot),
                                               "--playback",str(playback),
                                               "--output",str(p/"new.json")]):
                    with self.assertRaisesRegex(SystemExit,"identity mismatch"):
                        run()
            self.assertFalse((p/"new.json").exists())

if __name__=="__main__":
    unittest.main()
