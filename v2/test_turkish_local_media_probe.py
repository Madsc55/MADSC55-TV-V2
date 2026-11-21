import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from v2.turkish_local_media_probe import probe_local_sample

class LocalProbeTests(unittest.TestCase):
    def test_turkish_subtitle_track_is_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            sample = Path(d) / "sample.mkv"
            sample.write_bytes(b"sample")
            def runner(command, **kwargs):
                self.assertEqual(kwargs["timeout"], 10)
                self.assertNotIn("http", " ".join(command))
                return SimpleNamespace(returncode=0, stdout=json.dumps({"streams": [
                    {"index": 2, "codec_type": "subtitle", "tags": {"language": "tur"}}]}).encode())
            report = probe_local_sample(sample, runner=runner, which=lambda _: "/usr/bin/ffprobe")
            self.assertEqual(report["turkish_subtitle_track_candidates"], 1)
            self.assertFalse(report["review_approved"])
            self.assertFalse(report["playlist_modified"])

    def test_missing_ffprobe_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            sample = Path(d) / "sample.mkv"
            sample.write_bytes(b"sample")
            self.assertEqual(probe_local_sample(sample, which=lambda _: None)["status"], "FFPROBE_UNAVAILABLE")

    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            original = Path(d) / "real.mkv"
            original.write_bytes(b"sample")
            symlink = Path(d) / "link.mkv"
            symlink.symlink_to(original)
            with self.assertRaises(ValueError):
                probe_local_sample(symlink)

    def test_malformed_probe_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            sample = Path(d) / "sample.mkv"
            sample.write_bytes(b"sample")
            report = probe_local_sample(sample, which=lambda _: "/usr/bin/ffprobe",
                                        runner=lambda *a, **kw: SimpleNamespace(returncode=0, stdout=b"not-json"))
            self.assertEqual(report["status"], "PROBE_FAILED")
            self.assertFalse(report["review_approved"])


class RealStreamDecodeTests(unittest.TestCase):
    def setUp(self):
        import shutil
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg is not installed")

    def _make_media(self, directory, with_audio):
        import subprocess
        output = Path(directory) / ("with-av.mp4" if with_audio else "video-only.mp4")
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=64x64:r=10:d=1",
        ]
        if with_audio:
            command += ["-f", "lavfi", "-i", "sine=frequency=1000:duration=1"]
        command += ["-t", "1", "-c:v", "mpeg4"]
        if with_audio:
            command += ["-c:a", "aac"]
        else:
            command += ["-an"]
        command += [str(output)]
        subprocess.run(command, check=True, capture_output=True, timeout=20)
        return output

    def test_requires_real_video_and_audio_decode(self):
        from v2.turkish_stream_decode import decode
        with tempfile.TemporaryDirectory() as directory:
            sample = self._make_media(directory, with_audio=True)
            result = decode({"channel_id": "fixture-av", "url": str(sample)})
        self.assertEqual(result["status"], "SHORT_DECODE_VERIFIED")
        self.assertEqual(result["media_types"], ["audio", "video"])

    def test_missing_audio_is_not_verified(self):
        from v2.turkish_stream_decode import decode
        with tempfile.TemporaryDirectory() as directory:
            sample = self._make_media(directory, with_audio=False)
            result = decode({"channel_id": "fixture-video-only", "url": str(sample)})
        self.assertEqual(result["status"], "DECODE_UNVERIFIED")
        self.assertEqual(result["media_types"], [])
