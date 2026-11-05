#!/usr/bin/env python3
"""Grouped offline negative-claim and real metadata crosswalk tests."""
import hashlib
import unittest
from traz_missing_name_xmltv_review import build, registry_names, xmltv_display_candidates, verify_inputs, key

def h(v):return hashlib.sha256(v.encode()).hexdigest()
def fixture():
    ids=["Foo.tr","Bar.az","Ambiguous.tr","Now.tr"]
    api={"schema":1,"kind":"TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
         "policy":"READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES",
         "protected_playlist_modified":False,"all_streams_av_verified":False,
         "identities_without_stream_url_lead":ids,"identities_missing_epg":ids}
    scan={"schema":1,"candidate_status":"UNVERIFIED","playback_verified":False,
          "total_unique_candidates":4,"candidates":[
             {"name":"Foo TV","tvg_id":"","url_sha256":h("foo")},
             {"name":"Bar TV","tvg_id":"Bar.az","url_sha256":h("bar")},
             {"name":"Now TV","tvg_id":"Different.tr","url_sha256":h("conflict")},
             {"name":"News","tvg_id":"","url_sha256":h("ambig")}]}
    gap={"schema":1,"kind":"V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE",
         "protected_playlist_modified":False,"missing_api_stream_identities":4,
         "missing_api_epg_references":4,"candidate_identities":[],
         "exact_missing_stream_identities_with_other_m3u_leads":0,
         "epg_xmltv":{"exact_xmltv_candidate_ids":[]}}
    channels=[{"id":"Foo.tr","name":"Foo TV","alt_names":["Foo Television"]},
              {"id":"Bar.az","name":"Bar TV"},
              {"id":"Ambiguous.tr","name":"News"},
              {"id":"Other.gb","name":"News"},
              {"id":"Now.tr","name":"Now TV"}]
    xml=b'<tv><channel id="foo-id"><display-name>Foo Television</display-name></channel><channel id="bar-id"><display-name>Bar TV</display-name></channel><programme channel="foo-id" start="20261105080000 +0000" stop="20261105090000 +0000"/></tv>'
    return api,scan,gap,channels,xml

class MissingNameXmltvTests(unittest.TestCase):
    def test_realistic_metadata_only_and_programme_presence_not_ibo(self):
        api,scan,gap,channels,xml=fixture()
        r=build(api,scan,gap,channels,["https://guide.example.org/epg.xml"],lambda url:xml)
        self.assertEqual(r["stream_name_review"]["name_only_candidate_identities"],2)
        self.assertEqual(r["stream_name_review"]["conflicting_tvg_id_rows_rejected"],1)
        self.assertEqual(r["stream_name_review"]["still_without_name_lead"],2)
        self.assertEqual(r["epg_name_review"]["display_name_review_identities"],2)
        self.assertEqual(r["epg_name_review"]["with_programme_records"],1)
        self.assertFalse(r["ibo_device_verified"])
        self.assertFalse(r["epg_schedule_accuracy_verified"])
        self.assertEqual(r["new_av_proof"],0)
        self.assertNotIn("https://",str(r))
    def test_ambiguous_names_not_mapped(self):
        _,_,_,channels,_=fixture()
        names,n=registry_names(channels)
        self.assertNotIn("news",names)
        self.assertGreaterEqual(n,1)
    def test_malformed_xmltv_rejected(self):
        for raw in (b"<html></html>",b"<tv>",b"garbage"):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                xmltv_display_candidates(raw,{"foo tv":"Foo.tr"},{"Foo.tr"})
    def test_partial_xmltv_does_not_erase_gap(self):
        api,scan,gap,channels,_=fixture()
        def down(url):raise OSError("offline")
        report=build(api,scan,gap,channels,["https://guide.example.org/epg.xml"],down)
        self.assertFalse(report["epg_name_review"]["all_sources_parsed"])
        self.assertEqual(report["epg_name_review"]["still_without_display_name_lead"],4)
    def test_fake_coverage_and_plaintext_rejected(self):
        api,scan,gap,channels,_=fixture()
        api["identities_without_stream_url_lead"]=["Foo.tr"]
        with self.assertRaises(ValueError):verify_inputs(api,scan,gap)
        api,scan,gap,channels,_=fixture()
        scan["candidates"][0]["url"]="https://example.org/unsafe.m3u8"
        with self.assertRaises(ValueError):build(api,scan,gap,channels,[],lambda _:b"<tv/>")
    def test_strict_name_normalization_no_fuzzy_alias_guess(self):
        self.assertEqual(key("  FOO  TV "),"foo tv")
        self.assertNotEqual(key("Foo TV"),key("Foo News"))

if __name__=="__main__":unittest.main()
