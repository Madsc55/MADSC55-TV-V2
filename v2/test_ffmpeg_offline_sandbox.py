import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from v2.ffmpeg_offline_sandbox import isolated_local_ffmpeg, SandboxUnavailable

class OfflineSandboxTests(unittest.TestCase):
    def test_missing_sandbox_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.ts"
            source.write_bytes(b"fixture")
            with self.assertRaises(SandboxUnavailable):
                isolated_local_ffmpeg(source, Path(directory) / "out.mkv",
                                      which=lambda x: None,
                                      runner=lambda *a, **k: self.fail("must not run"))
    def test_no_network_and_no_remote_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.ts"
            source.write_bytes(b"fixture")
            target = Path(directory) / "out.mkv"
            def runner(cmd, **kwargs):
                self.assertIn("--unshare-net", cmd)
                self.assertEqual(cmd[cmd.index("-protocol_whitelist") + 1], "file")
                self.assertEqual(cmd[cmd.index("-i") + 1], str(source))
                self.assertNotIn("http", cmd)
                target.write_bytes(b"fixture-output")
                return SimpleNamespace(returncode=0)
            receipt = isolated_local_ffmpeg(source, target, runner=runner,
                      which=lambda x: "/usr/bin/" + x)
            self.assertFalse(receipt["live_retry_authorized"])
            self.assertFalse(receipt["av_verified"])
    def test_failure_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.ts"
            source.write_bytes(b"fixture")
            with self.assertRaises(SandboxUnavailable):
                isolated_local_ffmpeg(source, Path(directory) / "out.mkv",
                     runner=lambda *a, **k: SimpleNamespace(returncode=1),
                     which=lambda x: "/usr/bin/" + x)
if __name__ == "__main__":
    unittest.main()
