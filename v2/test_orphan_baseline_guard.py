#!/usr/bin/env python3
"""Grouped original orphan identity-loss gate: exact SHA-only evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orphan_baseline_guard import (
    load_immutable_baseline, reconcile_immutable_sources, SOURCES)


BASELINE = Path(__file__).resolve().parent / "history/m3u-orphan-50-hash-baseline.json"


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ImmutableOrphanBaselineTests(unittest.TestCase):
    def test_real_original_evidence_survives_artifact_expiration(self):
        ledger = load_immutable_baseline(BASELINE)
        self.assertEqual(sum(len(x) for x in ledger["sources"].values()), 55)
        self.assertEqual(len(set(sum(ledger["sources"].values(), []))), 50)
        self.assertEqual(ledger["report_run_id"], 41661347263)
        self.assertEqual(ledger["source_workflow_artifact_id"], 13241662530)

    def test_tampered_original_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            obj = json.loads(BASELINE.read_text())
            obj["decompressed_sha256"] = "0" * 64
            path = Path(folder) / "tampered.json"
            path.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "proof mismatch"):
                load_immutable_baseline(path)

    def test_source_missing_metadata_fails_closed_without_erasing_other_sources(self):
        broken = "#EXTINF:-1 tvg-id=\"T.tr\",Turkish TV"
        src = {"sources": {k: [] for k in SOURCES}}
        src["sources"]["discevisita-tr"] = [sha(broken)]
        payloads = {k: "#EXTM3U\n" for k in SOURCES}
        result = reconcile_immutable_sources(src, payloads)
        self.assertEqual(result["status"], "LOSS_RISK_REVIEW_REQUIRED")
        self.assertEqual(result["original_occurrences_missing_metadata"], 1)
        self.assertEqual(result["sources"]["discevisita-tr"]["missing_extinf_sha256"],
                         [sha(broken)])
        self.assertNotIn("Turkish TV", str(result))

    def test_corrected_real_source_uri_not_claimed_playable(self):
        line = "#EXTINF:-1 tvg-id=\"T.tr\",Turkish TV"
        src = {"sources": {k: [] for k in SOURCES}}
        src["sources"]["discevisita-tr"] = [sha(line)]
        docs = {k: "#EXTM3U\n" for k in SOURCES}
        docs["discevisita-tr"] = (
            "#EXTM3U\n" + line + "\nhttps://example.org/verified-source-uri.m3u8\n")
        result = reconcile_immutable_sources(src, docs)
        self.assertEqual(result["status"], "NO_ORIGINAL_METADATA_IDENTITY_LOSS")
        self.assertEqual(result["original_occurrences_with_current_valid_source_uri"], 1)
        self.assertFalse(result["playback_verified"])
        self.assertNotIn("example.org", str(result))

    def test_existing_orphan_record_stays_protected(self):
        line = "#EXTINF:-1,Missing URI"
        src = {"sources": {k: [] for k in SOURCES}}
        src["sources"]["github-auto-24"] = [sha(line)]
        docs = {k: "#EXTM3U\n" for k in SOURCES}
        docs["github-auto-24"] = "#EXTM3U\n" + line + "\n"
        result = reconcile_immutable_sources(src, docs)
        self.assertEqual(result["original_occurrences_still_unpaired"], 1)
        self.assertEqual(result["original_occurrences_missing_metadata"], 0)

    def test_unrecognized_additional_broken_record_is_reported(self):
        line = "#EXTINF:-1,Brand new orphan"
        src = {"sources": {k: [] for k in SOURCES}}
        docs = {k: "#EXTM3U\n" for k in SOURCES}
        docs["onureroz-turk-all"] = "#EXTM3U\n" + line + "\n"
        result = reconcile_immutable_sources(src, docs)
        self.assertEqual(result["new_orphan_occurrences"], 1)
        self.assertEqual(result["status"], "NO_ORIGINAL_METADATA_IDENTITY_LOSS")

    def test_rejects_missing_provider_documents(self):
        with self.assertRaisesRegex(ValueError, "four"):
            reconcile_immutable_sources({"sources": {k: [] for k in SOURCES}},
                                        {"discevisita-tr": "#EXTM3U\n"})


if __name__ == "__main__":
    unittest.main()
