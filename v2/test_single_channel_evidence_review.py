import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from v2.single_channel_evidence_review import review_one
from v2.safe_hls_prefetch import UnsafeMediaSource

URL = "https://example.org/approved/live.m3u8"

class SingleChannelReviewTests(unittest.TestCase):
    def test_review_requires_explicit_source_authorization(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "approved single source"):
                review_one(URL, Path(d) / "report.json", source_authorized=False)
            self.assertFalse((Path(d) / "report.json").exists())

    @patch.dict(os.environ, {}, clear=True)
    def test_secure_egress_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("v2.single_channel_evidence_review.prefetch_hls") as fetch:
                with self.assertRaisesRegex(ValueError, "egress"):
                    review_one(URL, Path(d) / "report.json", source_authorized=True)
                fetch.assert_not_called()

    @patch.dict(os.environ, {"MADSC55_SECURE_EGRESS_CONFIRMED": "1"})
    def test_private_url_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("v2.single_channel_evidence_review.prefetch_hls") as fetch:
                with self.assertRaisesRegex(ValueError, "Unsafe source URL"):
                    review_one("http://127.0.0.1/video.m3u8",
                               Path(d) / "new.json", source_authorized=True)
                fetch.assert_not_called()

    @patch.dict(os.environ, {"MADSC55_SECURE_EGRESS_CONFIRMED": "1"})
    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d) / "protected.m3u8"
            out.write_text("PROTECTED_PLAYLIST",encoding="utf-8")
            with patch("v2.single_channel_evidence_review.prefetch_hls") as fetch:
                with self.assertRaises(FileExistsError):
                    review_one(URL, out, source_authorized=True)
                fetch.assert_not_called()
            self.assertEqual(out.read_text(encoding="utf-8"),"PROTECTED_PLAYLIST")

    @patch.dict(os.environ, {"MADSC55_SECURE_EGRESS_CONFIRMED": "1"})
    def test_unsafe_hls_prefetch_does_not_run_decoder(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d) / "report.json"
            with patch("v2.single_channel_evidence_review.shutil.which",
                       return_value="/usr/bin/ffmpeg"):
                with patch("v2.single_channel_evidence_review.prefetch_hls",
                           side_effect=UnsafeMediaSource("redirect")):
                    with patch("v2.single_channel_evidence_review.subprocess.run") as decode:
                        with self.assertRaises(UnsafeMediaSource):
                            review_one(URL, out, source_authorized=True)
                        decode.assert_not_called()
            self.assertFalse(out.exists())

    @patch.dict(os.environ, {"MADSC55_SECURE_EGRESS_CONFIRMED": "1"})
    def test_unified_review_no_auto_approval_or_raw_media_data(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            out=root / "evidence.json"
            captured=[]
            def decode(command, **kwargs):
                captured.append(command)
                if command[0]=="ffmpeg":
                    Path(command[-1]).write_bytes(b"x" * 20001)
                    return SimpleNamespace(returncode=0,stdout=b"")
                return SimpleNamespace(returncode=0,stdout="TÜRKİYE HABERLERİ CANLI")
            with patch("v2.single_channel_evidence_review.shutil.which",
                       return_value="/usr/bin/tool"):
                with patch("v2.single_channel_evidence_review.prefetch_hls",
                           return_value=root / "safe-local.m3u8"):
                    with patch("v2.single_channel_evidence_review.subtitle_observations",
                               return_value=[{"kind":"SUBTITLE","text":"Türkiye haberleri",
                                              "language_tag":"tr"}]):
                        with patch("v2.single_channel_evidence_review._offline_asr_hint",
                                   return_value={"status":"ASR_HINT_ONLY",
                                                 "spoken_turkish_hint":True}):
                            with patch("v2.single_channel_evidence_review.subprocess.run",
                                       side_effect=decode):
                                result=review_one(URL,out,seconds=8,source_authorized=True)
            self.assertEqual(result["status"],"AV_SAMPLED_REVIEW_REQUIRED")
            self.assertTrue(result["video_decoded"])
            self.assertTrue(result["audio_decoded"])
            self.assertTrue(result["spoken_turkish_hint"])
            self.assertTrue(result["ocr_turkish_hint"])
            self.assertTrue(result["subtitle_turkish_hint"])
            self.assertFalse(result["language_evidence_verified"])
            self.assertFalse(result["review_approved"])
            self.assertFalse(result["real_turkish_broadcaster_verified"])
            self.assertFalse(result["playlist_modified"])
            data=out.read_text(encoding="utf-8")
            self.assertNotIn(URL,data)
            self.assertNotIn("Türkiye haberleri",data)
            self.assertNotIn("TÜRKİYE HABERLERİ CANLI",data)
            self.assertEqual(json.loads(data)["url_sha256"],result["url_sha256"])
            ffmpeg=[cmd for cmd in captured if cmd[0]=="ffmpeg"]
            self.assertEqual(len(ffmpeg),2)
            for cmd in ffmpeg:
                self.assertEqual(cmd[cmd.index("-protocol_whitelist")+1],"file,crypto")
                self.assertEqual(cmd[cmd.index("-i")+1],str(root / "safe-local.m3u8"))
                self.assertNotIn(URL,cmd)

if __name__=="__main__":
    unittest.main()
