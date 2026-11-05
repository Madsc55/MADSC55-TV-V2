#!/usr/bin/env python3
"""One batch of exact API/M3U linkage, false-identity and protection tests."""
import hashlib
import unittest
from traz_api_m3u_bridge import join

def sha(v): return hashlib.sha256(v.encode()).hexdigest()

class ExactAPIToM3UBridge(unittest.TestCase):
    def fixture(self):
        a,b,c=(sha(x) for x in ("one","two","three"))
        api={"schema":1,"kind":"TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
             "policy":"READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES",
             "all_streams_av_verified":False,"protected_playlist_modified":False,
             "unique_channel_url_pairs":3,
             "stream_references":[
                 {"channel_id":"SZCTV.tr","url_sha256":a,"av_verified":False,
                  "epg_guide_reference":True,"country_metadata":"TR",
                  "feed_language_metadata":["tur"]},
                 {"channel_id":"Other.tr","url_sha256":b,"av_verified":False},
                 {"channel_id":"Different.tr","url_sha256":b,"av_verified":False}]}
        scan={"schema":1,"playback_verified":False,
              "candidates":[
                  {"url_sha256":a,"tvg_id":"SZCTV.tr","source_ids":["iptv-org-tr"]},
                  {"url_sha256":b,"tvg_id":"NotThatChannel.tr","source_ids":["other"]},
                  {"url_sha256":c,"tvg_id":"Missing.tr"}]}
        return api,scan

    def test_exact_hash_and_channel_identity_only(self):
        report=join(*self.fixture())
        self.assertEqual(report["exact_channel_and_url_hash_matches"],1)
        self.assertEqual(report["url_hash_overlaps_without_exact_channel_id"],1)
        self.assertEqual(report["api_channel_url_pairs"],3)
        self.assertEqual(report["m3u_url_hashes_present_in_api"],2)
        self.assertEqual(report["epg_matched_exact_streams"],1)
        self.assertEqual(report["m3u_entries_not_in_api"],1)
        self.assertFalse(report["all_streams_av_verified"])
        self.assertFalse(report["ibo_device_verified"])
        self.assertTrue(report["exact_matches"][0]["identity_match_only"])

    def test_identity_swaps_cannot_fake_match(self):
        api,scan=self.fixture()
        scan["candidates"][0]["tvg_id"]="Other.tr"
        report=join(api,scan)
        self.assertEqual(report["exact_channel_and_url_hash_matches"],0)
        self.assertEqual(report["url_hash_overlaps_without_exact_channel_id"],2)

    def test_duplicate_hash_and_fake_proof_fail_closed(self):
        api,scan=self.fixture()
        scan["candidates"].append(dict(scan["candidates"][0]))
        with self.assertRaises(ValueError):join(api,scan)
        api,scan=self.fixture()
        api["all_streams_av_verified"]=True
        with self.assertRaises(ValueError):join(api,scan)
        api,scan=self.fixture()
        api["stream_references"][0]["url"]="https://not-public.example.org/a.m3u8"
        with self.assertRaises(ValueError):join(api,scan)

    def test_verified_iptv_org_feed_suffix_exact_hash_only(self):
        api,scan=self.fixture()
        scan["candidates"][0]["tvg_id"]="SZCTV.tr@SD"
        r=join(api,scan)
        self.assertEqual(r["exact_channel_and_url_hash_matches"],1)
        scan["candidates"][0]["source_ids"]=["not-iptv-org"]
        r=join(api,scan)
        self.assertEqual(r["exact_channel_and_url_hash_matches"],0)

if __name__=="__main__":
    unittest.main()
