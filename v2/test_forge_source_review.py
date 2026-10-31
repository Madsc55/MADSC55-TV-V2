#!/usr/bin/env python3
import hashlib
import unittest
from forge_source_review import normalize, approved_sources, valid_forge_source

class ForgeReviewTests(unittest.TestCase):
    def test_gitlab_raw_api_allowed(self):
        url = "https://gitlab.com/api/v4/projects/42/repository/files/tr.m3u/raw?ref=main"
        self.assertTrue(valid_forge_source(url))
    def test_codeberg_public_m3u_allowed(self):
        self.assertTrue(valid_forge_source("https://codeberg.org/example/tv/raw/branch/main/tr.m3u"))
    def test_private_or_credentialed_rejected(self):
        for url in ("http://gitlab.com/test.m3u", "https://127.0.0.1/a.m3u",
                    "https://user:secret@gitlab.com/a.m3u", "https://gitlab.com:8080/a.m3u"):
            self.assertFalse(valid_forge_source(url))
    def test_no_automatic_promotion(self):
        url = "https://codeberg.org/example/tv/raw/branch/main/tr.m3u"
        report = {"schema": 1, "sources": [{"source_url": url, "forge": "codeberg"}]}
        self.assertEqual(approved_sources(report, set()), [])
        selected = approved_sources(report, {hashlib.sha256(url.encode()).hexdigest()})
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["scope"], "candidate")
    def test_deduplicate_and_drop_invalid(self):
        url = "https://codeberg.org/example/tv/raw/branch/main/tr.m3u"
        report = {"schema": 1, "sources": [{"source_url": url}, {"source_url": url},
                                             {"source_url": "https://localhost/a.m3u"}]}
        self.assertEqual(len(normalize(report)), 1)
if __name__ == "__main__":
    unittest.main(verbosity=2)
