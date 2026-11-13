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
from stage5_evidence_export import entries, run, media_has_audio_video, valid_private_destination

class Stage5Acceptance(unittest.TestCase):
    def test_no_synthetic_or_unverified_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            source, protected, evidence, output = (p/x for x in ("source.m3u8","protected.m3u8","evidence.json","private-out.m3u8"))
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
            source, protected, evidence, output = (p/x for x in ("source.m3u8","protected.m3u8","evidence.json","private-out.m3u8"))
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
            '#EXTM3U\n#EXTINF:-1 tvg-id="' + metadata_id + '",One\n' + url + '\n',
            encoding="utf-8")
        protected.write_text("#EXTM3U\n#EXTINF:-1,Protected\nhttps://example.net/protected.m3u8\n")
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
                                                stdout="#format: frame checksums\n0, 0, 0\n")
        with patch("stage5_evidence_export.subprocess.run", side_effect=[probe, no_audio]) as mocked:
            self.assertFalse(media_has_audio_video(Path("fake-offline.mp4")))
            self.assertEqual(mocked.call_count, 2)
            args = mocked.call_args_list[1].args[0]
            self.assertIn("framemd5", args)
            self.assertIn("file,pipe", args)
        with patch("stage5_evidence_export.subprocess.run", side_effect=[
            probe, subprocess.CompletedProcess(["ffmpeg"], 0,
            stdout="#format: frame checksums\n0, 0, 0\n1, 0, 0\n")]):
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

    def test_rejects_one_proof_reused_for_different_channel_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            args = self._one_stream_fixture(root)
            first_url = "https://cdn.example.net/one.m3u8"
            second_url = "https://cdn.example.net/two.m3u8"
            # Two distinct filenames with identical bytes are not independent AV proof.
            (root / "copy-proof.mp4").write_bytes((root / "proof.mp4").read_bytes())
            args.source.write_text(
                '#EXTM3U\n#EXTINF:-1 tvg-id="one",One\n' + first_url
                + '\n#EXTINF:-1 tvg-id="two",Two\n' + second_url + '\n')
            evidence = json.loads(args.evidence.read_text())
            duplicate = dict(evidence[0], url=second_url, channel_id="two",
                             evidence_ref="second-channel-same-media",
                             evidence_file="copy-proof.mp4")
            evidence.append(duplicate)
            args.evidence.write_text(json.dumps(evidence))
            args.target = 2  # Small offline fixture; production CLI is 1000/2000.
            with patch("stage5_evidence_export.media_has_audio_video", return_value=True):
                with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REAL_EVIDENCE: 1/2"):
                    run(args)
            self.assertFalse(args.output.exists())

    def test_invalid_library_targets_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            args = self._one_stream_fixture(Path(d))
            for target in (0, -1, True, 2001, "1000"):
                args.target = target
                with self.subTest(target=target), self.assertRaisesRegex(ValueError, "Invalid package target"):
                    run(args)
            self.assertFalse(args.output.exists())

    def test_private_exports_reject_repository_reports_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self._one_stream_fixture(Path(directory))
            # Validation only: never create or write a file inside the repository.
            args.output = Path(__file__).resolve().parents[1] / "v2/reports/private-stage5-never-write-fixture.m3u8"
            with self.assertRaisesRegex(ValueError, "isolated location"):
                valid_private_destination(args.output, args.source, args.protected)
            self.assertFalse(args.output.exists())

    def test_private_only_output_name_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            args = self._one_stream_fixture(Path(d))
            args.output = Path(d) / "YENILER.m3u8"
            with self.assertRaisesRegex(ValueError, "new private"):
                run(args)
            self.assertFalse(args.output.exists())

    def test_source_m3u_url_validation_blocks_invalid_authorities_and_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "unsafe.m3u8"
            bad_urls = (
                "https://",
                "http://",
                "https://example.org:99999/live.m3u8",
                "https://example.org:invalid/live.m3u8",
                "https://user:password@example.org/live.m3u8",
                "https://example.org/live path.m3u8",
                "https://example.org/live.m3u8#private-fragment",
                "https://[invalid/live.m3u8",
                "https://example.org/live.m3u8\\tother",
            )
            for url in bad_urls:
                with self.subTest(url=url):
                    source.write_text('#EXTM3U\\n#EXTINF:-1 tvg-id="one",One\\n' + url + '\\n', encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "Malformed M3U entry"):
                        entries(source)

    def test_source_m3u_rejects_stripped_url_whitespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "whitespace.m3u8"
            for url in (" https://example.org/live.m3u8", "https://example.org/live.m3u8 "):
                with self.subTest(url=url):
                    source.write_text('#EXTM3U\\n#EXTINF:-1 tvg-id="one",One\\n' + url + '\\n', encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "Malformed M3U entry"):
                        entries(source)

    def test_source_m3u_keeps_valid_signed_url_for_private_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "valid.m3u8"
            url = "https://example.org:8443/live.m3u8?sig=sample%2Ftoken"
            source.write_text('#EXTM3U\\n#EXTINF:-1 tvg-id="one",One\\n' + url + '\\n', encoding="utf-8")
            self.assertEqual(entries(source)[0][1], url)


if __name__ == "__main__":
    unittest.main()
