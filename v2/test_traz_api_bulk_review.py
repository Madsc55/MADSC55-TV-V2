#!/usr/bin/env python3
"""Grouped no-network exact metadata / FFmpeg review backlog regressions."""
import copy
import hashlib
import unittest
from traz_api_bulk_review import audit

def digest(x):return hashlib.sha256(x.encode()).hexdigest()

def fixtures():
    h1,h2,h3=(digest(x) for x in ("a","b","c"))
    source={"schema":1,"kind":"TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
      "policy":"READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES",
      "protected_playlist_modified":False,"ibo_device_verified":False,
      "unique_channel_url_pairs":3,"target_unique_channel_ids":3,
      "target_identities_without_epg_reference":2,
      "identities_missing_epg":["Alpha.tr","Missing.tr"],
      "identities_without_stream_url_lead":["Missing.tr"],
      "stream_references":[
        {"url_sha256":h1,"channel_id":"Alpha.tr","country_metadata":"TR","av_verified":False},
        {"url_sha256":h2,"channel_id":"Alpha.tr","country_metadata":"TR","av_verified":False},
        {"url_sha256":h3,"channel_id":"Beta.az","country_metadata":"AZ",
         "epg_guide_reference":True,"av_verified":False}]}
    av={"schema":1,"kind":"TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE",
      "policy":"ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS",
      "protected_playlist_modified":False,"ibo_device_verified":False,
      "unique_url_candidates":3,"probed":3,"unprobed":0,"video_audio_decoded":2,
      "status_counts":{"VIDEO_AUDIO_DECODED":2,"PROBE_FAILED_HTTP_FORBIDDEN":1},
      "streams":[
        {"url_sha256":h1,"channel_ids":["Alpha.tr"],"video":True,"audio":True,
         "decoded":True,"status":"VIDEO_AUDIO_DECODED"},
        {"url_sha256":h2,"channel_ids":["Alpha.tr"],"video":True,"audio":True,
         "decoded":True,"status":"VIDEO_AUDIO_DECODED"},
        {"url_sha256":h3,"channel_ids":["Beta.az"],"video":False,"audio":False,
         "decoded":False,"status":"PROBE_FAILED_HTTP_FORBIDDEN"}]}
    return source,av

class TRZBatchReviewTests(unittest.TestCase):
    def test_full_hash_parity_and_backlogs(self):
        api,av=fixtures()
        d=audit(api,av)
        self.assertEqual(d["identities_with_decoded_av"],1)
        self.assertEqual(d["decoded_av_alternative_urls"],1)
        self.assertEqual(d["identities_with_no_stream_url_lead"],1)
        self.assertEqual(d["missing_epg_reference_count"],2)
        self.assertEqual(d["video_audio_decoded_url_hashes"],2)
        self.assertFalse(d["ibo_device_verified"])
        self.assertIsNone(d["individual_channels"][0]["reliability_score"])

    def test_hash_swap_and_fake_decoder_rejected(self):
        api,av=fixtures()
        for bad in ["changed-id","hash-missing","fake-decode"]:
            x=copy.deepcopy(av)
            if bad=="changed-id":x["streams"][0]["channel_ids"]=["Beta.az"]
            if bad=="hash-missing":x["streams"][0]["url_sha256"]="e"*64
            if bad=="fake-decode":x["streams"][2]["decoded"]=True
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                audit(api,x)

    def test_incomplete_scan_rejected_not_published(self):
        api,av=fixtures()
        av["unprobed"]=1
        with self.assertRaises(ValueError):audit(api,av)

    def test_missing_epg_backlog_must_be_consistent(self):
        api,av=fixtures()
        api["identities_missing_epg"].append("Duplicate.tr")
        with self.assertRaises(ValueError):audit(api,av)

    def test_source_count_must_match_historical_and_current_url_identity(self):
        api,av=fixtures()
        api["unique_channel_url_pairs"]=999
        with self.assertRaises(ValueError):audit(api,av)

    def test_public_plaintext_url_rejected(self):
        api,av=fixtures()
        api["stream_references"][0]["url"]="https://example.org/private.m3u8"
        with self.assertRaises(ValueError):audit(api,av)
        api,av=fixtures()
        av["streams"][0]["url"]="https://example.org/private.m3u8"
        with self.assertRaises(ValueError):audit(api,av)

if __name__=="__main__":
    unittest.main()
