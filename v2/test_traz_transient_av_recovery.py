#!/usr/bin/env python3
"""Grouped no-network regression of selective transient AV recovery."""
import copy
import hashlib
import unittest
from traz_transient_av_recovery import select_retry,aggregate

def sha(x):return hashlib.sha256(x.encode()).hexdigest()
def fixture():
    ids=["One.tr","Two.az","Three.tr"]
    statuses=["VIDEO_AUDIO_DECODED","PROBE_FAILED_NETWORK_TIMEOUT","PROBE_FAILED_HTTP_NOT_FOUND"]
    rows=[{"url_sha256":sha(cid),"exact_channel_id":cid,
           "source_ids":["source-tr"],"status":status,
           "decoded":i==0,"video":i==0,"audio":i==0,"ibo_device_verified":False}
          for i,(cid,status) in enumerate(zip(ids,statuses))]
    p={"schema":1,"kind":"V2_TR_AZ_MISSING_M3U_REAL_AV_READONLY",
       "policy":"PUBLIC_SHA_ONLY_RSA_AES_SEALED_STREAM_URLS",
       "protected_playlist_modified":False,"ibo_device_verified":False,
       "old_historical_orphan_50_auto_recovered":False,
       "candidate_hashes":3,"matched_current_source_hashes":3,
       "unmatched_or_unavailable_hashes":0,"real_video_audio_decoded_hashes":1,
       "real_video_audio_channel_ids":1,
       "av_status_counts":{x:1 for x in statuses},"results":rows}
    g={"schema":1,"kind":"V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE",
       "protected_playlist_modified":False,
       "candidate_identities":[{"channel_id":cid,"candidate_count":1,
        "candidate_m3u_url_hashes":[{"url_sha256":sha(cid),"av_verified":False}]}
        for cid in ids]}
    return p,g

class TransientBatchSafety(unittest.TestCase):
    def test_only_timeout_selected_not_already_good_or_not_found(self):
        p,g=fixture()
        target,old,counts=select_retry(p,g)
        self.assertEqual(set(target),{sha("Two.az")})
        self.assertEqual(old,{"One.tr"})
        self.assertEqual(sum(counts.values()),3)
        url="https://cdn.example.org/stream.m3u8"
        found={sha("Two.az"):{"url":url,"channel_id":"Two.az","source_ids":{"source-tr"}}}
        proof={sha("Two.az"):{"url_sha256":sha("Two.az"),"status":"VIDEO_AUDIO_DECODED",
                               "video":True,"audio":True,"decoded":True}}
        report=aggregate(target,old,found,{"source-tr":"FETCHED"},[],proof,counts)
        self.assertEqual(report["new_distinct_av_identities"],1)
        self.assertEqual(report["previous_failures_not_retried"],2)
        self.assertFalse(report["ibo_device_verified"])
        self.assertNotIn(url,str(report))
    def test_identity_mismatch_and_fake_prior_rejected(self):
        p,g=fixture()
        p["results"][1]["exact_channel_id"]="Other.tr"
        with self.assertRaises(ValueError):select_retry(p,g)
        p,g=fixture()
        p["results"][0]["audio"]=False
        with self.assertRaises(ValueError):select_retry(p,g)
    def test_previous_success_status_without_decoded_av_is_rejected(self):
        p,g=fixture()
        p["results"][0]["decoded"]=False
        p["results"][0]["video"]=False
        p["results"][0]["audio"]=False
        with self.assertRaisesRegex(ValueError,"Contradictory previous"):
            select_retry(p,g)

    def test_numeric_previous_decoded_flags_are_not_av_evidence(self):
        for numeric in (0, 1):
            p,g=fixture()
            p["results"][0]["decoded"]=numeric
            with self.subTest(decoded=numeric):
                with self.assertRaisesRegex(ValueError,"Malformed previous"):
                    select_retry(p,g)

    def test_new_ffmpeg_forgery_rejected(self):
        p,g=fixture()
        target,old,counts=select_retry(p,g)
        digest=sha("Two.az")
        fake={digest:{"url_sha256":digest,"status":"VIDEO_AUDIO_DECODED",
                      "video":False,"audio":True,"decoded":True}}
        with self.assertRaises(ValueError):
            aggregate(target,old,{digest:{"url":"https://e.org/x"}},
                      {},[],fake,counts)
    def test_contradictory_retry_proof_never_claims_av(self):
        p,g=fixture()
        target,old,counts=select_retry(p,g)
        digest=sha("Two.az")
        for decoded,status in ((False,"VIDEO_AUDIO_DECODED"),
                               (1,"VIDEO_AUDIO_DECODED"),
                               (0,"PROBE_FAILED_NETWORK_TIMEOUT")):
            with self.subTest(decoded=decoded,status=status):
                fake={digest:{"url_sha256":digest,"status":status,
                              "video":True,"audio":True,"decoded":decoded}}
                with self.assertRaisesRegex(ValueError,"Fake FFmpeg recovery"):
                    aggregate(target,old,{digest:{"url":"https://e.org/x"}},
                              {},[],fake,counts)

    def test_source_outage_does_not_delete_identities(self):
        p,g=fixture()
        target,old,counts=select_retry(p,g)
        report=aggregate(target,old,{},{"source-tr":"FETCH_FAILED_TimeoutError"},[],{},counts)
        self.assertEqual(report["unavailable_original_url_hashes"],1)
        self.assertEqual(report["new_distinct_av_identities"],0)
        self.assertEqual(report["original_av_channel_identities"],1)
    def test_deduplicated_source_evidence_hash(self):
        p,g=fixture()
        g["candidate_identities"][2]["candidate_m3u_url_hashes"][0]["url_sha256"]=sha("Two.az")
        with self.assertRaises(ValueError):select_retry(p,g)

if __name__=="__main__":unittest.main()
