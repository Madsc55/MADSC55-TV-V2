#!/usr/bin/env python3
"""Offline SHA-only verification of 8 exact blocked-page candidates."""
import copy
import json
import unittest
from blocked_official_prior_av_bridge import LEDGER, reconcile


class BlockedOfficialPriorEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prior=json.loads(LEDGER.read_text(encoding="utf-8"))
        cls.current={
            "kind":"BLOCKED_OFFICIAL_PAGES_EXACT_SOURCE_ONLY",
            "video_audio_verified":False,
            "no_plaintext_stream_urls":True,
            "protected_ibo_playlist_modified":False,
            "candidate_url_count":8,
            "candidate_url_sha256":[x["url_sha256"] for x in cls.prior["records"]]}

    def test_reconcile_real_8_hashes_four_previous_av_not_current(self):
        r=reconcile(self.current,self.prior)
        self.assertEqual(r["previous_decoder_verified_candidates"],4)
        self.assertEqual(r["current_exact_candidates"],8)
        self.assertEqual(len(r["previous_decoder_verified_channel_pages"]),3)
        self.assertEqual(r["previous_status_counts"]["VIDEO_AUDIO_DECODED"],4)
        self.assertFalse(r["current_video_audio_verified"])
        self.assertFalse(r["remaining_http_403_redirect_errors_resolved"])
        self.assertNotIn("https://",json.dumps(r))

    def test_new_candidate_is_not_falsely_marked_previous_av(self):
        current=copy.deepcopy(self.current)
        current["candidate_url_sha256"]=current["candidate_url_sha256"][:7]+["0"*64]
        result=reconcile(current,self.prior)
        self.assertEqual(result["previous_status_counts"]["NOT_PRESENT_IN_PRIOR_AV_ARTIFACT"],1)

    def test_mutated_probe_claim_fails(self):
        past=copy.deepcopy(self.prior)
        past["records"][0]["prior_probe_status"]="VIDEO_AUDIO_DECODED_FAKE"
        with self.assertRaises(ValueError):
            reconcile(self.current,past)
        current=copy.deepcopy(self.current)
        current["video_audio_verified"]=True
        with self.assertRaises(ValueError):
            reconcile(current,self.prior)

    def test_malformed_current_candidate_count_fails(self):
        changed=copy.deepcopy(self.current)
        changed["candidate_url_count"]=10
        with self.assertRaises(ValueError):
            reconcile(changed,self.prior)


if __name__=="__main__":
    unittest.main()
