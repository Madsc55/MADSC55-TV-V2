#!/usr/bin/env python3
"""Grouped no-network FFmpeg, HLS, identity and short-term claim regressions."""
import hashlib
import unittest
from unittest.mock import Mock
from traz_hls_codec_stability import prior_verified,current_exact_urls,decode_details,sample,hls_tags,aggregate

URL="https://cdn.example.org/live.m3u8"
HASH=hashlib.sha256(URL.encode()).hexdigest()

def pinned():
    return {"schema":1,"kind":"TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE",
      "policy":"ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS",
      "protected_playlist_modified":False,"ibo_device_verified":False,
      "unprobed":0,"probed":1,"unique_url_candidates":1,
      "video_audio_decoded":1,"streams":[{"url_sha256":HASH,
         "channel_ids":["TV.tr"],"status":"VIDEO_AUDIO_DECODED",
         "video":True,"audio":True,"decoded":True}]}

class HlsCodecEvidenceTests(unittest.TestCase):
    def test_prior_real_av_gate_and_exact_id_only(self):
        ids=prior_verified(pinned())
        valid,ambiguous,missing=current_exact_urls([{"channel":"TV.tr","url":URL}],ids)
        self.assertEqual((valid,ambiguous,missing),({HASH:URL},[],[]))
        valid,ambiguous,missing=current_exact_urls([{"channel":"Other.tr","url":URL}],ids)
        self.assertEqual(valid,{})
        self.assertEqual(ambiguous,[HASH])
    def test_fake_prior_video_audio_rejected(self):
        for mode in ("audio","unprobed","plaintext"):
            x=pinned()
            if mode=="audio":x["streams"][0]["audio"]=False
            if mode=="unprobed":x["unprobed"]=1
            if mode=="plaintext":x["streams"][0]["url"]=URL
            with self.subTest(mode=mode),self.assertRaises(ValueError):prior_verified(x)
    def test_actual_ffmpeg_metadata_parse_and_failed_decode_not_counted(self):
        text="Stream #0:0: Video: h264 (High), yuv420p, 1920x1080, 30 fps\nStream #0:1: Audio: aac (LC), 48000 Hz\n"
        self.assertEqual(decode_details(text)["height"],1080)
        good=sample(URL,runner=lambda *a,**kw:Mock(returncode=0,stderr=text),resolver=lambda u:True)
        bad=sample(URL,runner=lambda *a,**kw:Mock(returncode=1,stderr=text),resolver=lambda u:True)
        self.assertTrue(good["decoded"])
        self.assertFalse(bad["decoded"])
        out=aggregate({HASH:("TV.tr",)},{HASH:URL},[],[],{HASH:good},{HASH:bad},{})
        self.assertEqual(out["both_short_av_samples_decoded"],0)
        self.assertIsNone(out["streams"][0]["reliability_score"])
        self.assertFalse(out["ibo_device_verified"])
        self.assertNotIn(URL,str(out))
    def test_hls_master_variant_not_av(self):
        m=hls_tags("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720\nx.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=4000000,RESOLUTION=1920x1080\ny.m3u8\n")
        self.assertEqual(m["variant_count"],2)
        self.assertEqual(m["max_declared_height"],1080)
        self.assertEqual(m["status"],"HLS_MASTER_METADATA_NOT_AV")
        self.assertEqual(hls_tags("#EXTM3U\n#EXTINF:4,\ns.ts")["status"],"HLS_MEDIA_PLAYLIST")
        self.assertEqual(hls_tags("BAD")["status"],"INVALID_HLS")

if __name__=="__main__":
    unittest.main()
