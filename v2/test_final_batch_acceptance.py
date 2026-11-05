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
        reused = resume_checks(prior, inventory)
        self.assertEqual(set(reused), {good})
        self.assertEqual(reused[good]["evidence_origin"], "PRIOR_RUN_HASH_ONLY_NOT_FRESH")

    def test_resume_reprobes_all_unconfirmed_av_statuses(self):
        from final_batch_acceptance import resume_checks
        statuses = [
            ("VIDEO_AUDIO_STREAMS_ONLY", True, True, False),
            ("VIDEO_ONLY", True, False, False),
            ("AUDIO_ONLY", False, True, False),
            ("NO_AV", False, False, False),
        ]
        candidates = []
        inventory = {}
        for index, (status, video, audio, decoded) in enumerate(statuses):
            digest = sha("https://example.com/reprobe/" + str(index))
            inventory[digest] = {}
            candidates.append({"url_sha256": digest, "status": status,
                               "video": video, "audio": audio, "decoded": decoded})
        prior = {"schema": 1, "kind": "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
                 "unique_url_candidates": len(candidates), "candidates": candidates}
        self.assertEqual(resume_checks(prior, inventory), {})

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

    def test_resume_rejects_all_inconsistent_av_status_classes(self):
        from final_batch_acceptance import resume_checks
        digest = sha("https://example.com/av")
        states = [
            ("VIDEO_AUDIO_DECODED", True, False, True),
            ("VIDEO_AUDIO_STREAMS_ONLY", True, False, False),
            ("VIDEO_ONLY", True, True, False),
            ("AUDIO_ONLY", True, True, False),
            ("NO_AV", False, True, False),
        ]
        for status, video, audio, decoded in states:
            with self.subTest(status=status):
                prior = {"schema": 1, "kind": "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
                         "unique_url_candidates": 1, "candidates": [
                            {"url_sha256": digest, "status": status, "video": video,
                             "audio": audio, "decoded": decoded}]}
                with self.assertRaises(ValueError):
                    resume_checks(prior, {digest: {}})

    def test_report_separates_prior_evidence_from_current_probe(self):
        from final_batch_acceptance import report
        old, fresh = sha("https://example.com/old"), sha("https://example.com/new")
        inventory = {d: {"url": "https://example.com/private", "meta": {"name": "TV"},
                         "source_ids": {"source"}, "scopes": {"world"}} for d in (old, fresh)}
        checks = {d: {"status": "VIDEO_AUDIO_DECODED", "video": True,
                      "audio": True, "decoded": True, "audio_lang_tags": [],
                      "evidence_origin": origin} for d, origin in
                  ((old, "PRIOR_RUN_HASH_ONLY_NOT_FRESH"),
                   (fresh, "CURRENT_RUN_FFPROBE_FFMPEG"))}
        result = report([("source", [], "FETCHED")], inventory, checks,
                        configured=1, historic=0, expired=False, elapsed=1)
        self.assertEqual(result["evidence_origin_counts"],
                         {"PRIOR_RUN_HASH_ONLY_NOT_FRESH": 1,
                          "CURRENT_RUN_FFPROBE_FFMPEG": 1})
        self.assertEqual({x["evidence_origin"] for x in result["candidates"]},
                         {"PRIOR_RUN_HASH_ONLY_NOT_FRESH", "CURRENT_RUN_FFPROBE_FFMPEG"})

    def test_unprobed_candidate_never_counts_as_decoded(self):
        url = "https://example.com/another-private-stream"
        digest = sha(url)
        inventory = {digest: {"url": url, "source_ids": {"source"},
                              "scopes": {"world"}, "meta": {"name": "Channel"}}}
        result = report([("source", [], "FETCH_FAILED")], inventory, {},
                        configured=1, historic=0, expired=True, elapsed=1)
        self.assertEqual(result["audio_video_decoded"], 0)
        self.assertEqual(result["unprobed"], 1)

    def test_batch_workflow_does_not_require_old_run_artifact(self):
        """An expired historical run must not prevent a fresh real AV scan."""
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/v2-source-integration-batch.yml").read_text()
        self.assertIn("if gh run download 42077381839", workflow)
        self.assertIn("Prior evidence unavailable; scan without reuse", workflow)
        self.assertIn('if test -s v2/reports/ci/prior/final-worldwide-acceptance.json; then', workflow)
        self.assertIn('args+=(--reuse-report v2/reports/ci/prior/final-worldwide-acceptance.json)', workflow)
        self.assertIn('timeout 16000s python v2/final_batch_acceptance.py "${args[@]}"', workflow)

    def test_tr_az_priority_keeps_every_unverified_global_candidate(self):
        from final_batch_acceptance import prioritized_pending
        from final_batch_acceptance import sha
        urls = ["https://example.com/world", "https://example.com/tr",
                "https://example.com/az", "https://example.com/checked"]
        digests = [sha(url) for url in urls]
        inventory = {
            digests[0]: {"url": urls[0], "meta": {"name": "Global TV"}, "scopes": {"world"}},
            digests[1]: {"url": urls[1], "meta": {"name": "TRT 1"}, "scopes": {"world"}},
            digests[2]: {"url": urls[2], "meta": {"name": "Azərbaycan TV"}, "scopes": {"world"}},
            digests[3]: {"url": urls[3], "meta": {"name": "Already decoded"}, "scopes": {"world"}},
        }
        entries_ = sorted(inventory.items())
        checks = {digests[3]: {"status": "VIDEO_AUDIO_DECODED"}}
        pending = prioritized_pending(entries_, inventory, checks)
        self.assertEqual({digest for digest, _ in pending}, set(digests[:3]))
        self.assertEqual({digest for digest, _ in pending[:2]}, set(digests[1:3]))
        self.assertEqual(pending[-1][0], digests[0])

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
