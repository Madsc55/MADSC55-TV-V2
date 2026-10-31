#!/usr/bin/env python3
"""No unreviewed GitHub/Gist M3U source can enter a network scan."""
import hashlib
import unittest
from discover import approved_github_source

class GitHubApprovalTests(unittest.TestCase):
    def test_unapproved_source_is_excluded(self):
        url = "https://raw.githubusercontent.com/example/iptv/main/tr.m3u"
        self.assertFalse(approved_github_source(url, set()))
        self.assertTrue(approved_github_source(url, {hashlib.sha256(url.encode()).hexdigest()}))
    def test_unsafe_source_rejected_even_when_hash_approved(self):
        for url in ("http://example.org/tr.m3u", "https://localhost/tr.m3u",
                    "https://user:secret@example.org/tr.m3u"):
            self.assertFalse(approved_github_source(url, {hashlib.sha256(url.encode()).hexdigest()}))
if __name__ == "__main__":
    unittest.main(verbosity=2)
