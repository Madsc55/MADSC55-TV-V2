#!/usr/bin/env python3
"""Regression: an explicit unmatched playlist TVG-ID must never be remapped by name."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_epg import select_epg_source


class ExplicitIdSafetyTest(unittest.TestCase):
    def test_explicit_unknown_id_does_not_fallback_to_name(self):
        source, ambiguous = select_epg_source(
            "playlist.official.id", "Example TV", "Example TV",
            {"exampletv": {"publisher.other.id"}},
            {"publisher.other.id": [object()]})
        self.assertIsNone(source)
        self.assertFalse(ambiguous)

    def test_exact_id_is_allowed(self):
        source, ambiguous = select_epg_source(
            "publisher.id", "Example TV", "Example TV",
            {"exampletv": {"publisher.other.id"}},
            {"publisher.id": [object()], "publisher.other.id": [object()]})
        self.assertEqual(source, "publisher.id")
        self.assertFalse(ambiguous)

    def test_missing_id_name_remains_review_hint(self):
        source, ambiguous = select_epg_source(
            "", "Example TV", "Example TV",
            {"exampletv": {"publisher.id"}}, {"publisher.id": [object()]})
        self.assertEqual(source, "publisher.id")
        self.assertFalse(ambiguous)


if __name__ == "__main__":
    unittest.main()
