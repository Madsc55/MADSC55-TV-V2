#!/usr/bin/env python3
"""One-batch Stage 3 hash membership, loss and provenance regression gates."""
import hashlib
import unittest

from stage3_exact_coverage import verify_exact_coverage


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ExactHistoricalCoverageTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"url_sha256": sha(x), "source": "#60"}
                     for x in ("historic-a", "historic-b", "historic-c")]

    def test_overlapping_sources_cover_exact_baseline_without_double_counting(self):
        groups = {"git_history": [sha("historic-a"), sha("historic-b")],
                  "dated_health": [sha("historic-b"), sha("historic-c")]}
        self.assertEqual(
            verify_exact_coverage(self.rows, groups, expected_count=3),
            {row["url_sha256"] for row in self.rows})

    def test_same_count_but_nonhistorical_identity_is_rejected(self):
        groups = {"git_history": [sha("historic-a"), sha("historic-b"),
                                  sha("unrelated-new-stream")]}
        with self.assertRaisesRegex(ValueError, "nonhistorical"):
            verify_exact_coverage(self.rows, groups, expected_count=3)

    def test_partial_union_fails_even_if_individual_files_are_valid(self):
        groups = {"git_history": [sha("historic-a")],
                  "dated_health": [sha("historic-b"), sha("historic-b")]}
        with self.assertRaisesRegex(ValueError, "missing: 1"):
            verify_exact_coverage(self.rows, groups, expected_count=3)

    def test_duplicate_or_invalid_original_baseline_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            verify_exact_coverage(self.rows[:2] + self.rows[:1], 
                                  {"git_history": []}, expected_count=3)
        with self.assertRaisesRegex(ValueError, "format"):
            verify_exact_coverage([{"url_sha256": "0"}],
                                  {"git_history": []}, expected_count=1)

    def test_malformed_hash_is_not_accepted_as_match(self):
        with self.assertRaisesRegex(ValueError, "Invalid SHA256"):
            verify_exact_coverage(self.rows,
                                  {"source": [sha("historic-a").upper()]},
                                  expected_count=3)


if __name__ == "__main__":
    unittest.main()
