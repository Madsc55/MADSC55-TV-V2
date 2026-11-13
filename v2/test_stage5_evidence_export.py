import json
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from stage5_evidence_export import entries, run, media_has_audio_video

class Stage5Acceptance(unittest.TestCase):
    def test_no_synthetic_or_unverified_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            source, protected, evidence, output = (p/x for x in ("source.m3u8","protected.m3u8","evidence.json","out.m3u8"))
            source.write_text("#EXTM3U\n#EXTINF:-1,One\nhttps://example.org/one.m3u8\n")
            protected.write_text("#EXTM3U\n#EXTINF:-1,Original\nhttps://example.org/original.m3u8\n")
            evidence.write_text(json.dumps([{"url":"https://example.org/one.m3u8","video_verified":True,"audio_verified":True,"ibo_playback_verified":False,"evidence_ref":"fixture-not-real","channel_id":"one"}]))
            args = Namespace(source=source, protected=protected, evidence=evidence, output=output, target=1000)
            with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REAL_EVIDENCE"):
                run(args)
            self.assertFalse(output.exists())
            self.assertIn("Original", protected.read_text())
    def test_fake_boolean_evidence_does_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            source, protected, evidence, output = (p/x for x in ("source.m3u8","protected.m3u8","evidence.json","out.m3u8"))
            source.write_text("#EXTM3U\n#EXTINF:-1,One\nhttps://example.org/one.m3u8\n")
            protected.write_text("#EXTM3U\n#EXTINF:-1,Original\nhttps://example.org/original.m3u8\n")
            evidence.write_text(json.dumps([{"url":"https://example.org/one.m3u8","video_verified":True,"audio_verified":True,"ibo_playback_verified":True,"evidence_ref":"invented","channel_id":"one","evidence_file":"nonexistent.mp4","evidence_sha256":"0"*64}]))
            args = Namespace(source=source, protected=protected, evidence=evidence, output=output, target=1000)
            with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REAL_EVIDENCE: 0/1000"):
                run(args)
            self.assertFalse(output.exists())

    def test_non_media_proof_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "not-video.mp4"
            path.write_bytes(b"not an audio or video stream")
            self.assertFalse(media_has_audio_video(path))

    def test_ffprobe_stream_headers_alone_are_not_decoded_av_proof(self):
        import subprocess
        from unittest.mock import patch
        calls = []
        def fake_run(command, **kwargs):
            self.assertTrue(kwargs.get("check"))
            calls.append(command[0])
            if command[0] == "ffprobe":
                return subprocess.CompletedProcess(command, 0, '{"streams":[{"codec_type":"video"},{"codec_type":"audio"}]}', "")
            if "0:v:0" in command:
                return subprocess.CompletedProcess(command, 0, "frame=1\nprogress=end\n", "")
            return subprocess.CompletedProcess(command, 0, "out_time_us=0\nprogress=end\n", "")
        with patch("stage5_evidence_export.subprocess.run", side_effect=fake_run):
            self.assertFalse(media_has_audio_video(Path("metadata-only-fixture.mp4")))
        self.assertEqual(calls, ["ffprobe", "ffmpeg", "ffmpeg"])

    def test_decoded_video_and_audio_progress_required(self):
        import subprocess
        from unittest.mock import patch
        def fake_run(command, **kwargs):
            if command[0] == "ffprobe":
                text = '{"streams":[{"codec_type":"video"},{"codec_type":"audio"}]}'
            elif "0:v:0" in command:
                text = "frame=1\nprogress=end\n"
            else:
                text = "out_time_us=128000\nprogress=end\n"
            return subprocess.CompletedProcess(command, 0, text, "")
        with patch("stage5_evidence_export.subprocess.run", side_effect=fake_run):
            self.assertTrue(media_has_audio_video(Path("decoded-fixture.mp4")))

    def test_reject_malformed_m3u(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"bad.m3u8"
            p.write_text("#EXTM3U\n#EXTINF:-1,Missing\n")
            with self.assertRaises(ValueError):
                entries(p)

if __name__ == "__main__":
    unittest.main()
