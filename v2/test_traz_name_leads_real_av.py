#!/usr/bin/env python3
"""Grouped offline tests: exact name+SHA / real AV / never broadcaster proof."""
import hashlib
import unittest
from traz_name_leads_real_av import targets,match_sources,aggregate

def sha(x):return hashlib.sha256(x.encode()).hexdigest()
URL="https://cdn.example.org/a.m3u8"
def fixture():
    r={"schema":1,"kind":"V2_TR_AZ_STREAM_XMLTV_EXACT_NAME_REVIEW",
       "policy":"READ_ONLY_METADATA_LEADS_NOT_VIDEO_AUDIO_OR_EPG_ACCURACY",
       "protected_playlist_modified":False,"ibo_device_verified":False,"new_av_proof":0,
       "stream_name_review":{"name_only_candidate_identities":1,
           "name_only_candidate_hashes":1,
           "candidate_identities":[{"channel_id":"SozcuTV.tr",
               "source_url_sha256":[sha(URL)],"metadata_only":True,
               "needs_exact_identity_and_real_av":True}]}}
    return r

class NameLeadsRealAvTests(unittest.TestCase):
    def test_unverified_identity_strictly_separate_from_real_av(self):
        pending=targets(fixture())
        names={"sözcü tv":"SozcuTV.tr"}
        actual=[("tr-source",[{"url":URL,"name":"Sözcü TV","tvg_id":""}],"FETCHED")]
        found,status=match_sources(pending,actual,names)
        self.assertEqual(len(found),1)
        checks={sha(URL):{"url_sha256":sha(URL),"status":"VIDEO_AUDIO_DECODED",
                          "decoded":True,"video":True,"audio":True}}
        result=aggregate(pending,found,status,checks)
        self.assertEqual(result["video_audio_decoded_hashes"],1)
        self.assertEqual(result["channel_identities_confirmed_by_video"],0)
        self.assertFalse(result["ibo_device_verified"])
        self.assertNotIn(URL,str(result))
    def test_name_mismatch_or_tvg_conflict_not_playable_channel(self):
        expected=targets(fixture())
        data=[("tr-source",[{"url":URL,"name":"Other TV","tvg_id":""}],"FETCHED")]
        f,_=match_sources(expected,data,{"sözcü tv":"SozcuTV.tr"})
        self.assertEqual(f,{})
        data=[("tr-source",[{"url":URL,"name":"Sözcü TV","tvg_id":"Other.tr"}],"FETCHED")]
        f,_=match_sources(expected,data,{"sözcü tv":"SozcuTV.tr"})
        self.assertEqual(f,{})
    def test_false_dual_av_and_unknown_proof_rejected(self):
        pending=targets(fixture())
        found={sha(URL):{"url":URL,"channel_id":"SozcuTV.tr","source_ids":{"tr-source"}}}
        fake={sha(URL):{"url_sha256":sha(URL),"status":"VIDEO_AUDIO_DECODED",
                        "video":False,"audio":True,"decoded":True}}
        with self.assertRaises(ValueError):aggregate(pending,found,{},fake)
        with self.assertRaises(ValueError):aggregate(pending,{}, {},fake)
    def test_unavailable_source_keeps_candidate(self):
        pending=targets(fixture())
        report=aggregate(pending,{},{"tr-source":"FETCH_FAILED_TimeoutError"},{})
        self.assertEqual(report["unmatched_source_hashes"],1)
        self.assertEqual(report["name_candidate_channel_ids"],1)
        self.assertEqual(report["channel_identities_confirmed_by_video"],0)
    def test_plaintext_and_fake_metadata_rejected(self):
        r=fixture()
        r["new_av_proof"]=1
        with self.assertRaises(ValueError):targets(r)
        r=fixture()
        r["stream_name_review"]["candidate_identities"][0]["source_url_sha256"]=[URL]
        with self.assertRaises(ValueError):targets(r)

if __name__=="__main__":unittest.main()
