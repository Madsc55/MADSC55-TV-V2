#!/usr/bin/env python3
"""Offline SHA-only historical-to-world FFmpeg evidence bridge safety tests."""
import copy
import hashlib
import json
import unittest
from historical_world_av_bridge import bridge


def sha(s):return hashlib.sha256(s.encode()).hexdigest()


class HistoricalWorldAVBridgeTests(unittest.TestCase):
    def fixture(self):
        a,b,c,d=[sha(x) for x in "abcd"]
        world={"schema":1,"kind":"V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
            "protected_main_playlist_modified":False,
            "plaintext_url_in_public_report":False,"ibo_player_verified":False,
            "probe_budget_expired":False,"unique_url_candidates":3,"probed":3,
            "unprobed":0,"sealed_url_count":3,"audio_video_decoded":2,
            "candidates":[{"url_sha256":a,"status":"VIDEO_AUDIO_DECODED",
                "video":True,"audio":True,"decoded":True},
                {"url_sha256":b,"status":"VIDEO_AUDIO_STREAMS_ONLY",
                 "video":True,"audio":True,"decoded":False},
                {"url_sha256":d,"status":"VIDEO_AUDIO_DECODED",
                 "video":True,"audio":True,"decoded":True}]}
        current={"source_content_audit":{"historical_baseline_count":3,
            "historical_identifiers_present_in_current_sources":2,
            "historical_identifiers_absent_from_current_sources":1,
            "historical_identifiers_absent_sha256_sample":[c]}}
        return {a,b,c},world,current

    def test_hash_reconciliation_without_current_av_claims(self):
        historic,world,current=self.fixture()
        r=bridge(historic,world,current)
        self.assertEqual(r["historical_hashes_present_in_world"],2)
        self.assertEqual(r["historical_hashes_with_prior_world_ffmpeg_video_audio"],1)
        self.assertEqual(r["historical_hashes_absent_from_world"],1)
        self.assertEqual(r["historical_hashes_with_both_streams_without_ffmpeg_decode"],1)
        self.assertEqual(r["currently_absent_not_in_world_scan"],1)
        self.assertTrue(r["previous_evidence_only_not_current_playback"])
        self.assertFalse(r["ibo_device_verified"])
        self.assertNotIn("https://",json.dumps(r))

    def test_claiming_ffmpeg_decode_without_both_streams_fails(self):
        original,world,current=self.fixture()
        world["candidates"][0]["audio"]=False
        with self.assertRaises(ValueError):bridge(original,world,current)

    def test_duplicate_or_omitted_world_probes_rejected(self):
        original,world,current=self.fixture()
        world["candidates"][1]["url_sha256"]=world["candidates"][0]["url_sha256"]
        with self.assertRaises(ValueError):bridge(original,world,current)
        original,world,current=self.fixture()
        world["unprobed"]=1
        with self.assertRaises(ValueError):bridge(original,world,current)

    def test_mutated_source_baseline_or_world_count_rejected(self):
        original,world,current=self.fixture()
        current["source_content_audit"]["historical_identifiers_present_in_current_sources"]=1
        with self.assertRaises(ValueError):bridge(original,world,current)
        original,world,current=self.fixture()
        world["audio_video_decoded"]=1
        with self.assertRaises(ValueError):bridge(original,world,current)

    def test_unapproved_url_based_ids_not_used(self):
        original,world,current=self.fixture()
        world["candidates"][0]["url_sha256"]="https://secret.example.org/watch"
        with self.assertRaises(ValueError):bridge(original,world,current)

if __name__=="__main__":
    unittest.main()
