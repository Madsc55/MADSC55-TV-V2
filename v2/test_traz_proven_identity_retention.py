#!/usr/bin/env python3
"""Artifact-free exact AV hash identity preservation regression."""
import unittest
from traz_av_evidence_union import retain_proven_identity


class ProvenIdentityRetentionTests(unittest.TestCase):
    def test_prior_multiple_exact_ids_are_preserved(self):
        found = {"a" * 64: frozenset(("TRT1.tr", "TRT1Backup.tr"))}
        retain_proven_identity(found, "a" * 64, "TRT1.tr")
        self.assertEqual(found["a" * 64],
                         frozenset(("TRT1.tr", "TRT1Backup.tr")))

    def test_unrelated_channel_cannot_claim_proven_hash(self):
        found = {"a" * 64: frozenset(("TRT1.tr", "TRT1Backup.tr"))}
        with self.assertRaisesRegex(ValueError, "different broadcaster"):
            retain_proven_identity(found, "a" * 64, "Other.tr")
        self.assertEqual(len(found["a" * 64]), 2)

    def test_new_hash_adds_only_exact_proven_identity(self):
        found = {}
        retain_proven_identity(found, "b" * 64, "DHA.tr")
        self.assertEqual(found["b" * 64], frozenset(("DHA.tr",)))


if __name__ == "__main__":
    unittest.main()
