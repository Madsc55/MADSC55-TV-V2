#!/usr/bin/env python3
"""Offline acceptance for historical exact-hash, real FFmpeg-only proof."""
import hashlib
import json
import unittest
from historical_exact_real_av import grouped_decode


def urlhash(v):
    return hashlib.sha256(v.encode()).hexdigest()


class HistoricalExactRealAVTests(unittest.TestCase):
    def fixtures(self):
        a="https://stream.example.org/a.m3u8"
        b="https://stream.example.org/b.m3u8"
        c="https://stream.example.org/c.m3u8"
        return {urlhash(a),urlhash(b),urlhash(c)}, {urlhash(a):a,urlhash(b):b}

    def test_grouped_decode_counts_only_genuine_ffmpeg_success(self):
        missing,recovered=self.fixtures()
        def prober(pair):
            digest,url=pair
            good=url.endswith("/a.m3u8")
            return {"url_sha256":digest,"status":"VIDEO_AUDIO_DECODED" if good else "VIDEO_AUDIO_STREAMS_ONLY",
                    "video":True,"audio":True,"decoded":good}
        doc=grouped_decode(missing,recovered,prober=prober)
        self.assertEqual(doc["exact_git_history_url_hashes_found"],2)
        self.assertEqual(doc["original_historical_url_hashes_requested"],3)
        self.assertEqual(len(doc["not_in_git_history_sha256"]),1)
        self.assertEqual(doc["ffprobe_video_audio_both_streams_count"],2)
        self.assertEqual(doc["current_real_ffmpeg_video_audio_decoded_count"],1)
        self.assertEqual(doc["url_hashes_unverified_after_real_probe"],1)
        self.assertNotIn("https://",json.dumps(doc))
        self.assertFalse(doc["ibo_device_verified"])

    def test_missing_or_mismatched_url_hash_is_not_reconstructed(self):
        missing,recovered=self.fixtures()
        recovered[next(iter(recovered))]="https://stream.example.org/invented.m3u8"
        with self.assertRaises(ValueError):
            grouped_decode(missing,recovered)
        with self.assertRaises(ValueError):
            grouped_decode(missing,{"f"*64:"https://example.org/suspect.m3u8"})

    def test_ffprobe_only_result_does_not_claim_decoder_acceptance(self):
        missing,recovered=self.fixtures()
        with self.assertRaises(ValueError):
            grouped_decode(missing,recovered,prober=lambda pair:
                {"url_sha256":pair[0],"status":"VIDEO_AUDIO_DECODED","video":True,
                 "audio":True,"decoded":False})

    def test_contradictory_decoder_evidence_is_rejected(self):
        missing,recovered=self.fixtures()
        for status,video,audio,decoded in (
            ("VIDEO_AUDIO_DECODED",False,True,False),
            ("VIDEO_AUDIO_DECODED",True,False,False),
            ("VIDEO_AUDIO_STREAMS_ONLY",True,True,True),
        ):
            with self.subTest(status=status,video=video,audio=audio,decoded=decoded):
                with self.assertRaises(ValueError):
                    grouped_decode(missing,recovered,prober=lambda pair:
                        {"url_sha256":pair[0],"status":status,
                         "video":video,"audio":audio,"decoded":decoded})

    def test_prober_cannot_emit_url_or_wrong_identity(self):
        missing,recovered=self.fixtures()
        with self.assertRaises(ValueError):
            grouped_decode(missing,recovered,prober=lambda pair:
                {"url_sha256":pair[0],"status":"https://example.org/secret",
                 "video":False,"audio":False,"decoded":False})
        with self.assertRaises(ValueError):
            grouped_decode(missing,recovered,prober=lambda pair:
                {"url_sha256":"0"*64,"status":"PROBE_UNCONFIRMED",
                 "video":False,"audio":False,"decoded":False})

    def test_unsafe_source_and_bad_worker_size_fail_closed(self):
        missing,recovered=self.fixtures()
        with self.assertRaises(ValueError):
            grouped_decode(missing,recovered,workers=0)
        with self.assertRaises(ValueError):
            grouped_decode({urlhash("http://127.0.0.1/a.m3u8")},
                {urlhash("http://127.0.0.1/a.m3u8"):"http://127.0.0.1/a.m3u8"})

if __name__=="__main__":
    unittest.main()
