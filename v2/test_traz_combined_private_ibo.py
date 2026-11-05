#!/usr/bin/env python3
"""Grouped safety contract for combining two RSA sealed AV evidence batches."""
import hashlib
import unittest
from copy import deepcopy
from traz_combined_private_ibo import checked_target,make_combined

def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

API_URL="https://cdn.example.org/a.m3u8"
TARGET_URL="https://cdn.example.org/b.m3u8"
def fixture():
    a,b=sha(API_URL),sha(TARGET_URL)
    api={"schema":1,"kind":"TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE",
         "policy":"ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS",
         "protected_playlist_modified":False,"ibo_device_verified":False,
         "unprobed":0,"probed":1,"unique_url_candidates":1,
         "video_audio_decoded":1,
         "streams":[{"url_sha256":a,"status":"VIDEO_AUDIO_DECODED",
            "video":True,"audio":True,"decoded":True,"channel_ids":["TV.tr"]}]}
    private=[{"url":API_URL,"url_sha256":a,"probe_status":"VIDEO_AUDIO_DECODED",
              "video":True,"audio":True,"decoded":True,"channel_ids":["TV.tr"]}]
    target={"schema":1,"kind":"V2_TR_AZ_MISSING_M3U_REAL_AV_READONLY",
            "policy":"PUBLIC_SHA_ONLY_RSA_AES_SEALED_STREAM_URLS",
            "protected_playlist_modified":False,"ibo_device_verified":False,
            "old_historical_orphan_50_auto_recovered":False,
            "candidate_hashes":1,"matched_current_source_hashes":1,
            "ffmpeg_probed":1,"real_video_audio_decoded_hashes":1,
            "results":[{"url_sha256":b,"exact_channel_id":"New.az",
                        "status":"VIDEO_AUDIO_DECODED","video":True,
                        "audio":True,"decoded":True}]}
    sealed=[{"url":TARGET_URL,"url_sha256":b,
             "channel_id":"New.az","ffmpeg_status":"VIDEO_AUDIO_DECODED",
             "av_decoded":True}]
    return api,private,target,sealed

class CombinePrivateIbo(unittest.TestCase):
    def test_two_real_av_batches_merge_without_production(self):
        content,s=make_combined(*fixture())
        self.assertEqual(s["device_test_entries"],2)
        self.assertEqual(s["primary_exact_channel_ids"],2)
        self.assertEqual(s["target_new_nonduplicate_addresses"],1)
        self.assertFalse(s["protected_playlist_modified"])
        self.assertFalse(s["ibo_device_verified"])
        self.assertEqual(content.count("#EXTINF:"),2)
        self.assertIn("New.az",content)

    def test_duplicate_address_same_identity_is_deduplicated(self):
        a,p,t,s=fixture()
        t["results"][0]["url_sha256"]=sha(API_URL)
        t["results"][0]["exact_channel_id"]="TV.tr"
        s[0]["url_sha256"]=sha(API_URL)
        s[0]["url"]=API_URL
        s[0]["channel_id"]="TV.tr"
        content,summary=make_combined(a,p,t,s)
        self.assertEqual(summary["device_test_entries"],1)
        self.assertEqual(summary["duplicate_addresses_deduplicated"],1)

    def test_same_address_different_identity_rejected(self):
        a,p,t,s=fixture()
        t["results"][0]["url_sha256"]=sha(API_URL)
        s[0]["url_sha256"]=sha(API_URL)
        s[0]["url"]=API_URL
        with self.assertRaisesRegex(ValueError,"different channel"):
            make_combined(a,p,t,s)

    def test_metadata_and_false_ffmpeg_proof_not_exported(self):
        a,p,t,s=fixture()
        for bad in ("fake_status","identity_swap","incomplete_hash"):
            x=deepcopy(t); y=deepcopy(s)
            if bad=="fake_status":
                x["results"][0]["audio"]=False
            if bad=="identity_swap":
                y[0]["channel_id"]="Another.az"
            if bad=="incomplete_hash":
                y.clear()
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                make_combined(a,p,x,y)

    def test_missing_target_url_is_not_a_false_av_candidate(self):
        a,p,t,s=fixture()
        h=sha("not-present")
        t["candidate_hashes"]=2
        t["results"].append({"url_sha256":h,"exact_channel_id":"Lost.tr",
            "status":"NOT_FOUND_IN_CURRENT_SOURCE",
            "video":False,"audio":False,"decoded":False})
        content,summary=make_combined(a,p,t,s)
        self.assertEqual(summary["device_test_entries"],2)
        self.assertNotIn("Lost.tr",content)

    def test_api_partial_or_false_playback_rejected(self):
        a,p,t,s=fixture()
        a["unprobed"]=1
        with self.assertRaises(ValueError):
            make_combined(a,p,t,s)

    def test_malformed_target_report_fails_closed(self):
        a,p,t,s=fixture()
        t["old_historical_orphan_50_auto_recovered"]=True
        with self.assertRaises(ValueError):
            make_combined(a,p,t,s)

if __name__=="__main__":
    unittest.main()
