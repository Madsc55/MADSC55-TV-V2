#!/usr/bin/env python3
"""Offline official broadcaster directory safety regressions."""
import unittest
from official_sites_discovery import collect_official_sites


class OfficialSitesTests(unittest.TestCase):
    def test_catalog_shape_fails_closed(self):
        for bad in (None, {}, "not-a-list"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    collect_official_sites(bad)

    def test_malformed_and_private_records_are_excluded(self):
        rows = [None, "invalid", {}, {"country": "TR", "id": "", "website": "https://example.org"},
                {"country": "TR", "id": "local", "website": "http://127.0.0.1/live"},
                {"country": "TR", "id": "credential", "website": "https://user:pass@example.org/live"},
                {"country": "TR", "id": "token", "website": "https://example.org/live?token=secret"},
                {"country": "TR", "id": "fragment", "website": "https://example.org/live#secret"},
                {"country": "AZ", "id": "other", "website": "https://example.org"},
                {"country": "TR", "id": "closed", "closed": True, "website": "https://example.org"},
                {"country": "TR", "id": "valid.tr", "name": "Valid TV", "website": "https://example.org/live"},
                {"country": "TR", "id": "valid.tr", "name": "Duplicate", "website": "https://example.org/another"}]
        found = collect_official_sites(rows, {"TR"})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["channel_id"], "valid.tr")
        self.assertNotIn("secret", str(found))
        self.assertEqual(found[0]["status"], "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED")
        self.assertEqual({row["channel_id"] for row in collect_official_sites(rows)}, {"valid.tr", "other"})


if __name__ == "__main__":
    unittest.main()
