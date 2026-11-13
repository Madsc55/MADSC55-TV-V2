import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import patch
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

    def test_ffprobe_metadata_alone_does_not_count_as_decoded_av(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "metadata-only.mp4"
            path.write_bytes(b"offline-mock")
            calls = []
            def simulated_decoder(command, **kwargs):
                calls.append(command[0])
                if command[0] == "ffprobe":
                    return SimpleNamespace(returncode=0, stdout=json.dumps({
                        "streams": [{"codec_type": "video"}, {"codec_type": "audio"}]
                    }))
                # No framemd5 data frame: a stream declaration is not decoded AV.
                return SimpleNamespace(returncode=0, stdout="# empty frame list\n")
            with patch("stage5_evidence_export.subprocess.run", side_effect=simulated_decoder):
                self.assertFalse(media_has_audio_video(path))
            self.assertEqual(calls, ["ffprobe", "ffmpeg"])

    def test_requires_decoded_video_and_audio_frames(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "decoded-mock.mp4"
            path.write_bytes(b"offline-mock")
            calls = []
            def simulated_decoder(command, **kwargs):
                calls.append(command[0])
                if command[0] == "ffprobe":
                    return SimpleNamespace(returncode=0, stdout=json.dumps({
                        "streams": [{"codec_type": "video"}, {"codec_type": "audio"}]
                    }))
                return SimpleNamespace(returncode=0,
                                       stdout="# framemd5\n0, 0, 0, 1, 12, deadbeef\n")
            with patch("stage5_evidence_export.subprocess.run", side_effect=simulated_decoder):
                self.assertTrue(media_has_audio_video(path))
            self.assertEqual(calls, ["ffprobe", "ffmpeg", "ffmpeg"])

    def test_reused_media_file_does_not_prove_1000_distinct_channels(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proof = root / "single-proof.mp4"
            proof.write_bytes(b"synthetic-offline-test-only")
            digest = hashlib.sha256(proof.read_bytes()).hexdigest()
            source = root / "source.m3u8"
            source.write_text("#EXTM3U\n" + "".join(
                f"#EXTINF:-1,Channel {i}\nhttps://example.org/live/{i}.m3u8\n"
                for i in range(1000)))
            evidence = root / "evidence.json"
            evidence.write_text(json.dumps([{
                "url": f"https://example.org/live/{i}.m3u8",
                "video_verified": True, "audio_verified": True,
                "ibo_playback_verified": True, "evidence_ref": f"fixture-{i}",
                "channel_id": f"channel-{i}", "evidence_file": proof.name,
                "evidence_sha256": digest
            } for i in range(1000)]))
            protected = root / "original.m3u8"
            protected.write_text("#EXTM3U\n#EXTINF:-1,Protected\nhttps://example.org/p\n")
            output = root / "out.m3u8"
            args = Namespace(source=source, protected=protected, evidence=evidence,
                             output=output, target=1000)
            with patch("stage5_evidence_export.media_has_audio_video", return_value=True):
                with self.assertRaisesRegex(ValueError, "INSUFFICIENT_REAL_EVIDENCE: 1/1000"):
                    run(args)
            self.assertFalse(output.exists())

    def test_export_never_overwrites_an_existing_package(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rows, playlist = [], ["#EXTM3U"]
            for i in range(1000):
                url = f"https://example.org/live/{i}.m3u8"
                playlist += [f"#EXTINF:-1,Channel {i}", url]
                data = f"offline-fixture-{i}".encode()
                filename = f"proof-{i}.mp4"
                (root / filename).write_bytes(data)
                rows.append({"url": url, "channel_id": f"id-{i}",
                             "video_verified": True, "audio_verified": True,
                             "ibo_playback_verified": True,
                             "evidence_ref": f"offline-fixture-{i}",
                             "evidence_file": filename,
                             "evidence_sha256": hashlib.sha256(data).hexdigest()})
            source = root / "source.m3u8"
            source.write_text("\n".join(playlist) + "\n")
            evidence = root / "evidence.json"
            evidence.write_text(json.dumps(rows))
            protected = root / "protected.m3u8"
            protected.write_text("#EXTM3U\n#EXTINF:-1,Protected\nhttps://example.org/p\n")
            output = root / "out.m3u8"
            output.write_bytes(b"DO_NOT_REPLACE")
            args = Namespace(source=source, protected=protected, evidence=evidence,
                             output=output, target=1000)
            with patch("stage5_evidence_export.media_has_audio_video", return_value=True):
                with self.assertRaises(FileExistsError):
                    run(args)
            self.assertEqual(output.read_bytes(), b"DO_NOT_REPLACE")
            self.assertIn("Protected", protected.read_text())

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

if __name__ == "__main__":
    unittest.main()
