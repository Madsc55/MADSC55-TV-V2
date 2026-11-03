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
    def test_correct_git_blob_hash_algorithm(self):
        self.assertEqual(len(gitblob(b"test")), 40)

if __name__ == "__main__":
    unittest.main()
