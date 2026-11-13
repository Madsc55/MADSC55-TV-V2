import hashlib
import io
import json
import shutil
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
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

    def test_reject_malformed_m3u(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"bad.m3u8"
            p.write_text("#EXTM3U\n#EXTINF:-1,Missing\n")
            with self.assertRaises(ValueError):
                entries(p)


    def _one_stream_fixture(self, root, *, metadata_id="one", proof_id="one"):
        source, protected, evidence, output = (root / name for name in (
            "source.m3u8", "protected.m3u8", "evidence.json", "private-output.m3u8"))
        url = "https://cdn.example.net/one.m3u8"
        source.write_text(
            '#EXTM3U\\n#EXTINF:-1 tvg-id="' + metadata_id + '",One\\n' + url + '\\n',
            encoding="utf-8")
        protected.write_text("#EXTM3U\\n#EXTINF:-1,Protected\\nhttps://example.net/protected.m3u8\\n")
        proof = root / "proof.mp4"
        proof.write_bytes(b"local-offline-fixture-only")
        evidence.write_text(json.dumps([{
            "url": url, "video_verified": True, "audio_verified": True,
            "ibo_playback_verified": True, "evidence_ref": "test-fixture-only",
            "channel_id": proof_id, "evidence_file": "proof.mp4",
            "evidence_sha256": hashlib.sha256(proof.read_bytes()).hexdigest(),
        }]))
        return Namespace(source=source, protected=protected, evidence=evidence,
                         output=output, target=1)

    def test_real_proof_requires_decoded_samples_not_merely_stream_headers(self):
        probe = subprocess.CompletedProcess(["ffprobe"], 0, stdout=json.dumps(
            {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}))
        no_audio = subprocess.CompletedProcess(["ffmpeg"], 0,
                                                stdout="#format: frame checksums\\n0, 0, 0\\n")
        with patch("stage5_evidence_export.subprocess.run", side_effect=[probe, no_audio]) as mocked:
            self.assertFalse(media_has_audio_video(Path("fake-offline.mp4")))
            self.assertEqual(mocked.call_count, 2)
            args = mocked.call_args_list[1].args[0]
            self.assertIn("framemd5", args)
            self.assertIn("file,pipe", args)
        with patch("stage5_evidence_export.subprocess.run", side_effect=[
            probe, subprocess.CompletedProcess(["ffmpeg"], 0,
            stdout="#format: frame checksums\\n0, 0, 0\\n1, 0, 0\\n")]):
            self.assertTrue(media_has_audio_video(Path("fake-offline.mp4")))

    def test_local_ffmpeg_decodes_both_real_fixture_tracks(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg/ffprobe are not installed")
        with tempfile.TemporaryDirectory() as d:
            clip = Path(d) / "proof.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-nostdin", "-v", "error", "-f", "lavfi",
                 "-i", "testsrc2=size=64x64:rate=5", "-f", "lavfi",
                 "-i", "sine=frequency=440:sample_rate=8000",
                 "-t", "1", "-c:v", "mpeg4", "-c:a", "aac", str(clip)],
                capture_output=True, check=True, timeout=30)
            self.assertTrue(media_has_audio_video(clip))
            video_only = Path(d) / "video-only.mp4"
            subprocess.run(["ffmpeg", "-y", "-nostdin", "-v", "error",
                            "-i", str(clip), "-an", "-c:v", "copy", str(video_only)],
                           capture_output=True, check=True, timeout=30)
            self.assertFalse(media_has_audio_video(video_only))

    def test_private_export_is_exclusive_and_uses_exact_channel_id(self):
        with tempfile.TemporaryDirectory() as d:
            args = self._one_stream_fixture(Path(d))
            with patch("stage5_evidence_export.media_has_audio_video", return_value=True):
                with redirect_stdout(io.StringIO()):
                    run(args)
            self.assertEqual(len(entries(args.output)), 1)
            self.assertEqual(stat.S_IMODE(args.output.stat().st_mode), 0o600)
            original = args.output.read_bytes()
            with self.assertRaisesRegex(ValueError, "new private"):
                run(args)
            self.assertEqual(args.output.read_bytes(), original)
            self.assertIn("Protected", args.protected.read_text())

    def test_playback_proof_for_a_different_channel_does_not_authorize_export(self):
        with tempfile.TemporaryDirectory() as d:
            args = self._one_stream_fixture(Path(d), metadata_id="two", proof_id="one")
            with patch("stage5_evidence_export.media_has_audio_video", return_value=True):
                with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REAL_EVIDENCE"):
                    run(args)
            self.assertFalse(args.output.exists())

    def test_private_only_output_name_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            args = self._one_stream_fixture(Path(d))
            args.output = Path(d) / "YENILER.m3u8"
            with self.assertRaisesRegex(ValueError, "new private"):
                run(args)
            self.assertFalse(args.output.exists())

if __name__ == "__main__":
    unittest.main()
