#!/usr/bin/env python3
"""One offline batch to guard exact 84-identity 158-hash AV matching."""
import hashlib
import unittest
from traz_missing_target_av import select_targets,source_selection,match_fetched,public_report

def h(s):return hashlib.sha256(s.encode()).hexdigest()
URL1="https://example.org/a.m3u8"
URL2="https://example.org/b.m3u8"

def fixture():
    return {"schema":1,"kind":"V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE",
      "policy":"READ_ONLY_PUBLIC_HASH_ONLY_NO_AUTO_IBO_PROMOTION",
      "protected_playlist_modified":False,"new_video_audio_verified":0,
      "ibo_device_verified":False,
      "exact_missing_stream_candidate_hashes":2,
      "candidate_identities":[{"channel_id":"TV.tr","playback_verified":False,
        "candidate_count":2,"candidate_m3u_url_hashes":[
           {"url_sha256":h(URL1),"source_ids":["fixed-tr"],"av_verified":False},
           {"url_sha256":h(URL2),"source_ids":["historical-az"],"av_verified":False}]}]}

class TargetedNewSourceRealAVContracts(unittest.TestCase):
    def test_select_exact_immutable_hashes_and_known_sources(self):
        target=select_targets(fixture())
        self.assertEqual(len(target),2)
        selection,unknown=source_selection(target,{"fixed-tr":{"id":"fixed-tr"}})
        self.assertEqual([x["id"] for x in selection],["fixed-tr"])
        self.assertEqual(unknown,["historical-az"])
    def test_match_only_exact_channel_id_url_and_provenance(self):
        target=select_targets(fixture())
        good=("fixed-tr",[{"tvg_id":"TV.tr","url":URL1}], "FETCHED")
        fake=("historical-az",[{"tvg_id":"Wrong.tr","url":URL2}], "FETCHED")
        found,statuses=match_fetched(target,[good,fake])
        self.assertEqual(list(found),[h(URL1)])
        self.assertEqual(statuses,{"fixed-tr":"FETCHED","historical-az":"FETCHED"})
        checks={h(URL1):{"url_sha256":h(URL1),"status":"VIDEO_AUDIO_DECODED",
              "video":True,"audio":True,"decoded":True}}
        out=public_report(target,found,statuses,["unresolvable"],checks)
        self.assertEqual(out["real_video_audio_decoded_hashes"],1)
        self.assertEqual(out["real_video_audio_channel_ids"],1)
        self.assertEqual(out["unmatched_or_unavailable_hashes"],1)
        self.assertNotIn("https://",str(out))
        self.assertFalse(out["ibo_device_verified"])
    def test_malformed_and_false_av_cannot_count(self):
        wrong=fixture()
        wrong["candidate_identities"][0]["candidate_m3u_url_hashes"][0]["av_verified"]=True
        with self.assertRaises(ValueError):select_targets(wrong)
        targets=select_targets(fixture())
        found,statuses=match_fetched(targets,[("fixed-tr",[{"tvg_id":"TV.tr","url":URL1}],"FETCHED")])
        bad={h(URL1):{"url_sha256":h(URL1),"status":"VIDEO_AUDIO_DECODED",
                       "video":False,"audio":True,"decoded":True}}
        with self.assertRaises(ValueError):public_report(targets,found,statuses,[],bad)
    def test_source_failure_is_not_permanent_channel_death(self):
        targets=select_targets(fixture())
        found,statuses=match_fetched(targets,[("fixed-tr",[],"FETCH_FAILED_TimeoutError")])
        out=public_report(targets,found,statuses,[],{})
        self.assertEqual(out["real_video_audio_decoded_hashes"],0)
        self.assertEqual(out["source_errors"],{"fixed-tr":"FETCH_FAILED_TimeoutError"})
        self.assertTrue(out["non_av_candidates_not_promoted"])

if __name__=="__main__":
    unittest.main()
