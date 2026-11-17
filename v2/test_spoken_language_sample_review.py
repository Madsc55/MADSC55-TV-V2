import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from v2.spoken_language_sample_review import run

class SpeechSampleSafetyTests(unittest.TestCase):
    def test_refuses_existing_output_before_model_loading(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)
            out=p/"existing.json"
            out.write_text("PROTECTED")
            with patch.object(sys,"argv",["speech","--output",str(out)]):
                with self.assertRaises(SystemExit):
                    run()
            self.assertEqual(out.read_text(),"PROTECTED")

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
