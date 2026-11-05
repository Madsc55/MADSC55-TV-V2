#!/usr/bin/env python3
"""Grouped offline current/extra XMLTV crosswalk and no-false-EPG claims."""
import unittest
from traz_extra_xmltv_review import remaining_guide_ids,parse_guide,review

def fixture():
    api={"schema":1,"kind":"TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
         "policy":"READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES",
         "protected_playlist_modified":False,
         "identities_missing_epg":["Alpha.tr","Beta.az","Gamma.tr","Delta.tr"]}
    gap={"schema":1,"kind":"V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE",
         "protected_playlist_modified":False,"missing_api_epg_references":4,
         "epg_xmltv":{"exact_xmltv_candidate_ids":["Alpha.tr"],
                      "exact_xmltv_channel_id_candidates":1}}
    prior={"schema":1,"kind":"V2_TR_AZ_STREAM_XMLTV_EXACT_NAME_REVIEW",
           "protected_playlist_modified":False,
           "epg_name_review":{"candidate_identities":[{"channel_id":"Beta.az"}],
                              "display_name_review_identities":1,
                              "still_without_display_name_lead":2}}
    channels=[{"id":"Gamma.tr","name":"Gamma TV"},
              {"id":"Delta.tr","name":"Delta TV"},
              {"id":"Other.tr","name":"Common TV"},{"id":"Foreign.uk","name":"Common TV"}]
    xml=(b'<tv><channel id="provider-gamma">'
         b'<display-name>Gamma TV</display-name></channel>'
         b'<programme channel="provider-gamma" start="20261105080000 +0000"'
         b' stop="20261105090000 +0000"><title>News</title></programme></tv>')
    return api,gap,prior,channels,xml

class AdditionalXmltvSafetyTests(unittest.TestCase):
    def test_only_previous_unmatched_ids_considered(self):
        api,gap,prior,channels,xml=fixture()
        remaining,n,old=remaining_guide_ids(api,gap,prior)
        self.assertEqual(remaining,{"Gamma.tr","Delta.tr"})
        self.assertEqual((n,old),(4,2))
        r=review(api,gap,prior,channels,
                 ["https://dearbulut.github.io/iptv/epg/tr.xml.gz"],
                 lambda _:xml)
        self.assertEqual(r["additional_guide_candidate_identities"],1)
        self.assertEqual(r["still_missing_epg_identities"],1)
        self.assertEqual(r["additional_with_programme_records"],1)
        self.assertEqual(r["additional_with_well_formed_programme_times"],1)
        self.assertFalse(r["programme_schedule_accuracy_verified"])
        self.assertFalse(r["ibo_device_verified"])
        self.assertNotIn("https://",str(r))
    def test_invalid_xmltv_does_not_invent_guide_success(self):
        api,gap,prior,channels,_=fixture()
        r=review(api,gap,prior,channels,
                 ["https://dearbulut.github.io/iptv/epg/tr.xml.gz"],
                 lambda _:b"<html></html>")
        self.assertFalse(r["all_new_sources_parsed"])
        self.assertEqual(r["additional_guide_candidate_identities"],0)
        self.assertEqual(r["still_missing_epg_identities"],2)
    def test_fake_prior_coverage_fails_closed(self):
        a,g,p,_,_=fixture()
        p["epg_name_review"]["still_without_display_name_lead"]=0
        with self.assertRaises(ValueError):remaining_guide_ids(a,g,p)
    def test_unique_name_ambiguity_kept_unmatched(self):
        xml=(b'<tv><channel id="x"><display-name>Common TV</display-name></channel>'
             b'<programme channel="x" start="20261105080000 +0000" stop="20261105090000 +0000"/></tv>')
        hit,_,_=parse_guide(xml,{"Gamma.tr"},{"gamma tv":"Gamma.tr"})
        self.assertEqual(hit,{})
    def test_invalid_times_do_not_prove_schedule(self):
        xml=(b'<tv><channel id="Gamma.tr"/>'
             b'<programme channel="Gamma.tr" start="20261105090000 +0000"'
             b' stop="20261105080000 +0000"/></tv>')
        matched,records,timed=parse_guide(xml,{"Gamma.tr"},{})
        self.assertIn("Gamma.tr",matched)
        self.assertIn("Gamma.tr",records)
        self.assertEqual(timed,set())
    def test_unapproved_guide_endpoint_refused(self):
        a,g,p,ch,xml=fixture()
        with self.assertRaises(ValueError):
            review(a,g,p,ch,["https://private.example.org/epg.xml"],lambda _:xml)

if __name__=="__main__":unittest.main()
