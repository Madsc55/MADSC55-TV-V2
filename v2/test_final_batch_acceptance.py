#!/usr/bin/env python3
import unittest
from final_batch_acceptance import route, sha, gitblob, report

class FinalBatchAcceptanceTests(unittest.TestCase):
    def test_turkish_hint(self):
        self.assertEqual(route({"name": "TRT 1", "tvg_id": "TRT1.tr"}, {"world"}),
                         "TR_METADATA_HINT")
    def test_azeri_hint(self):
        self.assertEqual(route({"name": "AzTV", "tvg_id": "AzTV.az"}, {"world"}),
                         "AZ_METADATA_HINT")
    def test_foreign_hint_not_speech_proof(self):
        self.assertEqual(route({"name": "TV", "tvg_id": "TV.de"}, {"world"}),
                         "FOREIGN_METADATA_HINT")
    def test_unknown_world_source_is_unverified(self):
        self.assertEqual(route({"name": "Channel", "tvg_id": ""}, {"world"}),
                         "LANGUAGE_UNVERIFIED")
    def test_source_hint_is_not_speech_proof(self):
        self.assertEqual(route({"name": "Channel"}, {"TR"}), "TR_SOURCE_HINT")
        self.assertEqual(route({"name": "Channel"}, {"AZ"}), "AZ_SOURCE_HINT")
    def test_unprobed_and_failed_kept_not_exposed(self):
        url = "https://example.com/stream?token=privatevalue"
        digest = sha(url)
        inventory = {digest: {"url": url, "source_ids": {"failedtest"},
                              "scopes": {"world"}, "meta": {"name": "Normal"}}}
        result = report([("failedtest", [], "FETCH_FAILED_OSError")],
                        inventory, {}, configured=1,historic=0,expired=True,elapsed=2)
        self.assertEqual(result["readiness"], "REVIEW_REQUIRED")
        self.assertEqual(result["unprobed"], 1)
        self.assertEqual(result["candidates"][0]["status"], "NOT_PROBED_BUDGET")
        self.assertNotIn(url, str(result))
        self.assertNotIn("privatevalue", str(result))
    def test_resume_accepts_valid_av_and_rechecks_transient_failures(self):
        from final_batch_acceptance import resume_checks
        good, transient = sha("https://example.com/a"), sha("https://example.com/b")
        inventory = {good: {}, transient: {}}
        prior = {"schema": 1, "kind": "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
                 "unique_url_candidates": 2, "candidates": [
                    {"url_sha256": good, "status": "VIDEO_AUDIO_DECODED",
                     "video": True, "audio": True, "decoded": True},
                    {"url_sha256": transient, "status": "PROBE_FAILED_TIMEOUT",
                     "video": False, "audio": False, "decoded": False}]}
        self.assertEqual(set(resume_checks(prior, inventory)), {good})

    def test_resume_rejects_duplicate_hash_and_false_decode(self):
        from final_batch_acceptance import resume_checks
        digest = sha("https://example.com/a")
        row = {"url_sha256": digest, "status": "VIDEO_AUDIO_DECODED",
               "video": True, "audio": False, "decoded": True}
        prior = {"schema": 1, "kind": "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
                 "unique_url_candidates": 1, "candidates": [row]}
        with self.assertRaises(ValueError):
            resume_checks(prior, {digest: {}})
        prior["unique_url_candidates"] = 2
        prior["candidates"] = [row, dict(row)]
        with self.assertRaises(ValueError):
            resume_checks(prior, {digest: {}})

    def test_unprobed_candidate_never_counts_as_decoded(self):
        url = "https://example.com/another-private-stream"
        digest = sha(url)
        inventory = {digest: {"url": url, "source_ids": {"source"},
                              "scopes": {"world"}, "meta": {"name": "Channel"}}}
        result = report([("source", [], "FETCH_FAILED")], inventory, {},
                        configured=1, historic=0, expired=True, elapsed=1)
        self.assertEqual(result["audio_video_decoded"], 0)
        self.assertEqual(result["unprobed"], 1)

    def test_correct_git_blob_hash_algorithm(self):
        self.assertEqual(len(gitblob(b"test")), 40)


    def test_worldwide_source_snapshot_includes_document_handoff(self):
        from pathlib import Path
        from unittest.mock import patch
        from final_batch_acceptance import sources
        from document_platform_discovery import digest
        url = "https://archive.org/download/public-list/channels.m3u8"
        row = {"id": "docref-" + digest(url)[:20], "url": url,
               "kind": "m3u", "scope": "candidate",
               "origin": "public-document-reference"}
        with (patch("document_platform_discovery.accepted_sources",
                    return_value=[row]),
              patch("final_batch_acceptance.DYNAMIC",
                    Path("/no-dynamic-source-inventory")),
              patch("final_batch_acceptance.FORGE",
                    Path("/no-forge-source-inventory")),
              patch("final_batch_acceptance.fetch", side_effect=OSError("offline"))):
            found, configured, historic = sources()
        matches = [x for x in found if x.get("url") == url]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], row["id"])
        self.assertEqual(historic, 17)
        self.assertEqual(configured, 47)

if __name__ == "__main__":
    unittest.main()
