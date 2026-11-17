"""Real FFmpeg video+audio decode of a synthetic, locally prefetched HLS fixture.

This does not validate any external broadcaster or allow live network scans.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from urllib.parse import urlsplit
from v2.safe_hls_prefetch import prefetch_hls, LOCAL_PROTOCOLS

class LocalPrefetchAVTests(unittest.TestCase):
    def test_sanitized_hls_decodes_local_video_and_audio(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "FFmpeg is required for this gate")
        self.assertEqual(LOCAL_PROTOCOLS, "file,crypto")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            review = root / "review"
            review.mkdir()
            generated = source / "source.m3u8"
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                       "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=5",
                       "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
                       "-t", "3", "-c:v", "mpeg2video", "-c:a", "aac", "-f", "hls",
                       "-hls_time", "1", "-hls_segment_filename",
                       str(source / "part-%02d.ts"), str(generated)]
            subprocess.run(command, check=True, timeout=20, capture_output=True)
            def getter(url, limit):
                path = source / Path(urlsplit(url).path).name
                payload = path.read_bytes()
                self.assertLessEqual(len(payload), limit)
                return payload
            manifest = prefetch_hls("https://example.org/source.m3u8", review,
                                    seconds=3, getter=getter)
            self.assertTrue(manifest.exists())
            self.assertNotIn("https://", manifest.read_text(encoding="utf-8"))
            frame = root / "frame.png"
            audio = root / "audio.wav"
            for options in (["-frames:v", "1", "-y", str(frame)],
                            ["-vn", "-ac", "1", "-ar", "16000", "-y", str(audio)]):
                args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-protocol_whitelist", LOCAL_PROTOCOLS, "-i", str(manifest)]
                subprocess.run(args + options, check=True, timeout=20,
                               capture_output=True)
            self.assertGreater(frame.stat().st_size, 256)
            self.assertGreater(audio.stat().st_size, 16000)

if __name__ == "__main__":
    unittest.main()
