#!/usr/bin/env python3
"""Single offline test group for official feed rendition exact-ID recovery."""
import copy
import unittest
from traz_official_feed_variant_gap import reconcile

def fixture():
    api={"schema":1,"kind":"TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
         "policy":"READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES",
         "all_streams_av_verified":False,"protected_playlist_modified":False,
         "identities_without_stream_url_lead":["One.tr","Two.az","Three.tr"]}
    gap={"schema":1,"kind":"V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE",
         "protected_playlist_modified":False,"missing_api_stream_identities":3,
         "exact_missing_stream_identities_with_other_m3u_leads":1,
         "candidate_identities":[{"channel_id":"Three.tr","candidate_count":1}]}
    streams={"iptv-org-tr-streams":[
        {"tvg_id":"One.tr@SD","url":"https://cdn.example.org/one.m3u8"},
        {"tvg_id":"Three.tr@SD","url":"https://cdn.example.org/old.m3u8"}],
        "iptv-org-az-streams":[
        {"tvg_id":"Two.az@HD","url":"https://cdn.example.org/two.m3u8"}]}
    return api,gap,streams

class OfficialFeedVariantTests(unittest.TestCase):
    def test_target_only_missing_ids_not_previously_covered(self):
        r=reconcile(*fixture())
        self.assertEqual(r["original_missing_api_stream_identities"],3)
        self.assertEqual(r["original_exact_source_matched_identities"],1)
        self.assertEqual(r["exact_missing_stream_identities_with_other_m3u_leads"],2)
        self.assertEqual(r["exact_missing_stream_candidate_hashes"],2)
        self.assertEqual(r["still_without_exact_feed_variant_source"],0)
        self.assertFalse(r["source_scan_complete"])
        self.assertEqual(r["new_video_audio_verified"],0)
        self.assertFalse(r["ibo_device_verified"])
        self.assertNotIn("https://",str(r))
    def test_forged_feed_or_wrong_suffix_is_not_promoted(self):
        a,g,rows=fixture()
        rows["iptv-org-tr-streams"][0]["tvg_id"]="Other.tr@SD"
        rows["iptv-org-az-streams"][0]["tvg_id"]="Two.az@UNKNOWN"
        r=reconcile(a,g,rows)
        self.assertEqual(r["exact_missing_stream_identities_with_other_m3u_leads"],0)
    def test_same_url_for_two_broadcasters_needs_manual_collision(self):
        a,g,rows=fixture()
        rows["iptv-org-az-streams"][0]["url"]=rows["iptv-org-tr-streams"][0]["url"]
        r=reconcile(a,g,rows)
        self.assertEqual(r["conflicting_stream_hashes_not_promoted"],1)
        self.assertEqual(r["exact_missing_stream_identities_with_other_m3u_leads"],0)
    def test_partial_source_failure_kept_without_fake_av(self):
        a,g,rows=fixture()
        del rows["iptv-org-az-streams"]
        r=reconcile(a,g,rows,{"iptv-org-az-streams":"HTTPError"})
        self.assertFalse(r["source_scan_complete"])
        self.assertEqual(r["still_without_exact_feed_variant_source"],1)
    def test_incomplete_or_fake_original_metadata_rejected(self):
        a,g,rows=fixture()
        a["all_streams_av_verified"]=True
        with self.assertRaises(ValueError):reconcile(a,g,rows)
        a,g,rows=fixture()
        g["missing_api_stream_identities"]=42
        with self.assertRaises(ValueError):reconcile(a,g,rows)

if __name__=="__main__":unittest.main()
