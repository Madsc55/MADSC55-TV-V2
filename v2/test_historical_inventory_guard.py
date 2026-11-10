#!/usr/bin/env python3
"""Offline, bulk stage 3 tests. All stream URLs in tests are synthetic test fixtures."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from encrypted_archive import restore
from historical_inventory_guard import (SCHEMA, classify, identity, preserve_to_new_archive,
                                        reconcile, verify_historical_baseline)


class HistoricalInventoryGuardTests(unittest.TestCase):
    def test_4955_historical_rows_remain_preserved_without_synthetic_export(self):
        old = [{"url": "https://fixture.example.org/%04d.m3u8" % i,
                "name": "TRT %d" % i, "scope": "TR", "source": "#60"}
               for i in range(4951)]
        old.extend([
            {"url": old[0]["url"], "logo": "https://fixture.example.org/logo.png", "source": "older"},
            {"url_sha256": hashlib.sha256(b"only-hash").hexdigest(), "source": "#60"},
            {"anonymous_id": "historical-unknown"},
            {"url": "http://127.0.0.1/invalid.m3u8", "status": "HISTORICAL_FAILED"}
        ])
        self.assertEqual(len(old), 4955)
        new = [{"url": old[0]["url"], "source": "recent", "group": "Türkiye"},
               {"url": "https://fixture.example.org/new-az.m3u8", "tvg_id": "News.az"}]
        preserved, indexed, report = reconcile(old, new, 4955)
        self.assertEqual(preserved[:4955], old)
        self.assertEqual(report["historical_records_preserved"], 4955)
        self.assertEqual(report["historical_tr_candidate_records"], 4951)
        self.assertEqual(report["historical_az_candidate_records"], 0)
        self.assertEqual(report["historical_unknown_region_records"], 4)
        self.assertEqual(report["historical_unique_real_urls"], 4951)
        self.assertEqual(report["historical_duplicate_url_rows"], 1)
        self.assertEqual(report["historical_hash_only_identities"], 1)
        self.assertEqual(report["historical_unidentified_records_preserved"], 2)
        self.assertEqual(report["unique_candidate_urls"], 4952)
        first = next(item for item in indexed if item["url"] == old[0]["url"])
        self.assertEqual(first["source_ids"], ["#60", "older", "recent"])
        self.assertTrue(first["historical_not_reverified"])
        self.assertFalse(first["device_verified"])
        self.assertFalse(report["historical_preservation_verified"])

    def test_tr_az_unknown_candidate_without_speech_claim(self):
        samples = [
            ({"scope": "AZ", "name": "News"}, "AZ", "SOURCE_GEO"),
            ({"tvg_id": "AzerTV.az", "name": "News"}, "AZ", "TVG_ID"),
            ({"name": "Azərbaycan TV"}, "AZ", "METADATA"),
            ({"scope": "TR", "name": "News"}, "TR", "SOURCE_GEO"),
            ({"tvg_id": "TRT1.tr"}, "TR", "TVG_ID"),
            ({"name": "Türk Haber"}, "TR", "METADATA"),
            ({"name": "Global News"}, "UNKNOWN", "NONE")
        ]
        for row, region, evidence in samples:
            with self.subTest(row=row):
                result = classify(row)
                self.assertEqual(result["region_candidate"], region)
                self.assertEqual(result["classification_evidence"], evidence)
                self.assertFalse(result["spoken_language_verified"])

    def test_same_url_conflicting_historical_and_current_region_stays_unknown(self):
        """Deduplication must not silently prefer a new AZ hint over old TR."""
        url = "https://fixture.example.org/region-conflict.m3u8"
        old = [{"url": url, "scope": "TR", "source_id": "historical-tr",
                "status": "VIDEO_AUDIO_DECODED", "av_verified": True}]
        current = [{"url": url, "country_code": "AZ",
                    "source_id": "current-az", "av_verified": True}]
        raw, candidates, summary = reconcile(old, current, 1)
        self.assertEqual(raw, old + current)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["source_ids"],
                         ["historical-tr", "current-az"])
        self.assertEqual(candidate["region_candidate"], "UNKNOWN")
        self.assertEqual(candidate["classification_evidence"],
                         "CONFLICTING_TR_AZ_EVIDENCE")
        self.assertFalse(candidate["spoken_language_verified"])
        self.assertFalse(candidate["av_verified"])
        self.assertFalse(candidate["decoded"])
        self.assertEqual(candidate["status"], "NOT_REVERIFIED")
        self.assertEqual(summary["conflicting_tr_az_candidate_urls"], 1)

    def test_hash_only_historical_tr_conflicts_with_current_az_url(self):
        """An exact SHA link preserves TR provenance without relabelling AZ."""
        url = "https://fixture.example.org/hash-region-conflict.m3u8"
        sha = hashlib.sha256(url.encode("utf-8")).hexdigest()
        old = [{"url_sha256": sha, "scope": "TR",
                "source_id": "historical-hash"}]
        current = [{"url": url, "scope": "AZ",
                    "source_id": "current-url",
                    "decoded": True, "video": True, "audio": True}]
        raw, candidates, summary = reconcile(old, current, 1)
        self.assertEqual(raw, old + current)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["source_ids"],
                         ["historical-hash", "current-url"])
        self.assertEqual(candidate["url_sha256"], sha)
        self.assertEqual(candidate["region_candidate"], "UNKNOWN")
        self.assertEqual(candidate["classification_evidence"],
                         "CONFLICTING_TR_AZ_EVIDENCE")
        self.assertTrue(candidate["historical_not_reverified"])
        self.assertFalse(candidate["decoded"])
        self.assertFalse(candidate["video"])
        self.assertFalse(candidate["audio"])
        self.assertFalse(candidate["av_verified"])
        self.assertEqual(candidate["status"], "NOT_REVERIFIED")
        self.assertEqual(summary["historical_hash_only_linked_to_real_urls"], 1)
        self.assertEqual(summary["conflicting_tr_az_candidate_urls"], 1)

    def test_valid_manifest_cannot_certify_view_only_archive(self):
        """Authenticated counts and digest are insufficient without raw rows."""
        from historical_inventory_guard import (
            SCHEMA_V2, _archive_payload_sha256, _verify_archive_envelope)
        candidate = {"url_sha256": hashlib.sha256(b"candidate").hexdigest(),
                     "status": "NOT_REVERIFIED", "av_verified": False}
        payload = [{"kind": "deduplicated_view", "guard_schema": SCHEMA_V2,
                    "records": [candidate]}]
        manifest = {"kind": "archive_manifest", "guard_schema": SCHEMA_V2,
                    "block_count": 1, "raw_record_count": 0,
                    "candidate_record_count": 1,
                    "payload_sha256": _archive_payload_sha256(payload)}
        with self.assertRaisesRegex(ValueError, "missing raw historical"):
            _verify_archive_envelope(payload + [manifest])

    def test_missing_or_extra_history_fail_closed(self):
        rows = [{"url": "https://fixture.example.org/a.m3u8"}]
        with self.assertRaisesRegex(ValueError, "baseline"):
            reconcile(rows, [], 4955)
        with self.assertRaisesRegex(ValueError, "Missing historical"):
            reconcile([], [], 0)

    def test_exact_stream_urls_not_normalized_or_merged_by_name(self):
        old = [{"url": "https://fixture.example.org/a.m3u8?key=FIRST", "name": "TRT 1"},
               {"url": "https://fixture.example.org/a.m3u8?key=SECOND", "name": "TRT 1"}]
        _, indexed, report = reconcile(old)
        self.assertEqual(len(indexed), 2)
        self.assertEqual(report["historical_unique_real_urls"], 2)
        self.assertEqual(len({identity(row) for row in indexed}), 2)

    def test_hash_only_history_not_mistaken_for_restored_stream(self):
        url = "https://fixture.example.org/az.m3u8"
        old = [{"url_sha256": hashlib.sha256(url.encode()).hexdigest()},
               {"anonymous_id": "missing-url"}]
        preserved, indexed, report = reconcile(old, [])
        self.assertEqual(len(indexed), 0)
        self.assertEqual(len(preserved), 2)
        self.assertEqual(report["historical_identities_not_in_current"], 1)
        protected, indexed, report = reconcile(old, [{"url": url}])
        self.assertEqual(report["historical_hash_only_linked_to_real_urls"], 1)
        self.assertEqual(len(indexed), 1)
        self.assertEqual(len(protected), 3)
        self.assertTrue(indexed[0]["historical_not_reverified"])

    def test_corrupt_new_identity_cannot_overwrite_historical_archive(self):
        old = [{"url": "https://fixture.example.org/historic.m3u8",
                "source": "historical"},
               {"url_sha256": hashlib.sha256(b"unresolved").hexdigest()}]
        preserved, indexed, _ = reconcile(old)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "historic.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
                self.assertTrue(preserve_to_new_archive(path, preserved, indexed))
                before = path.read_bytes()
                original = restore(path)
                corrupt = [{"url": "https://fixture.example.org/new.m3u8",
                            "url_sha256": "0" * 64}]
                with self.assertRaisesRegex(ValueError, "disagree"):
                    reconcile(old, corrupt)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(restore(path), original)

    def test_duplicate_current_sources_preserve_history_without_false_av(self):
        url = "https://fixture.example.org/historic.m3u8"
        old = [{"url": url, "source": "historical"},
               {"url_sha256": hashlib.sha256(b"missing").hexdigest()}]
        current = [{"url": url, "source": "current-one"},
                   {"url": url, "source": "current-two"}]
        preserved, indexed, _ = reconcile(old, current)
        self.assertEqual(preserved[:len(old)], old)
        self.assertEqual(len(preserved), 4)
        matched = [row for row in indexed if row["url"] == url]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["source_ids"],
                         ["historical", "current-one", "current-two"])
        self.assertTrue(matched[0]["historical_not_reverified"])
        self.assertFalse(matched[0]["device_verified"])

    def test_legacy_source_id_survives_duplicate_and_hash_only_merge(self):
        url = "https://fixture.example.org/legacy.m3u8"
        old = [{"url": url, "source_id": "old-source"},
               {"url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                "source_id": "hash-backup"}]
        current = [{"url": url, "source_ids": ["modern"],
                    "source_id": "new-legacy", "source": "current"}]
        raw, candidates, report = reconcile(old, current)
        self.assertEqual(raw, old + current)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_ids"],
                         ["hash-backup", "old-source", "modern",
                          "new-legacy", "current"])
        self.assertFalse(candidates[0]["av_verified"])
        self.assertEqual(report["unique_candidate_urls"], 1)

    def test_4955_duplicate_historical_records_validate_full_metadata_multiset(self):
        old=[{"url":"https://fixture.example.org/%04d.m3u8" % i,
              "source":"old","status":"HISTORICAL"} for i in range(4953)]
        old.extend([
            {"url":old[0]["url"],"source":"legacy-backup","status":"TIMEOUT"},
            {"url":old[0]["url"],"source":"legacy-backup","status":"TIMEOUT"},
        ])
        self.assertEqual(len(old),4955)
        self.assertEqual(verify_historical_baseline(list(reversed(old)),old),
                         verify_historical_baseline(old,old))
        corrupted=[dict(x) for x in old]
        corrupted[-1]["status"]="VIDEO_AUDIO_DECODED"
        with self.assertRaisesRegex(ValueError,"metadata"):
            verify_historical_baseline(corrupted,old)
        metadata_only=[dict(x) for x in old]
        metadata_only[-1]["source"]="forged-new-source"
        with self.assertRaisesRegex(ValueError,"metadata"):
            verify_historical_baseline(metadata_only,old)
        missing=old[:-1]+[dict(old[1])]
        with self.assertRaisesRegex(ValueError,"identities"):
            verify_historical_baseline(missing,old)

    def test_4955_row_encrypted_roundtrip_retains_duplicate_provenance(self):
        old=[{"url":"https://fixture.example.org/%04d.m3u8" % i,
              "source":"historical","status":"PROBE_FAILED_NETWORK_TIMEOUT"}
             for i in range(4953)]
        old.extend([
            {"url":old[0]["url"],"source":"backup-one","status":"VIDEO_AUDIO_DECODED"},
            {"url":old[0]["url"],"source":"backup-two","status":"PROBE_FAILED_HTTP_RESPONSE_ERROR"},
        ])
        new=[{"url":old[0]["url"],"source":"fresh-source","av_verified":True}]
        raw,view,summary=reconcile(old,new,4955)
        self.assertEqual(summary["historical_records_preserved"],4955)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"all-history.enc"
            with patch.dict(os.environ,{"V2_ARCHIVE_KEY_HEX":"ab"*32}):
                self.assertTrue(preserve_to_new_archive(path,raw,view))
                restored=restore(path)
                restored_raw=[row for block in restored
                              if block["kind"]=="raw_historical_and_new"
                              for row in block["records"]]
                restored_view=[row for block in restored
                               if block["kind"]=="deduplicated_view"
                               for row in block["records"]]
                self.assertEqual(restored_raw,old+new)
                self.assertEqual(restored_view,view)
                self.assertEqual(verify_historical_baseline(restored_raw[:4955],old),
                                 verify_historical_baseline(old,old))
                matched=next(x for x in restored_view if x["url"]==old[0]["url"])
                self.assertEqual(matched["source_ids"],
                                 ["historical","backup-one","backup-two","fresh-source"])
                self.assertIs(matched["av_verified"],False)
                self.assertIs(matched["device_verified"],False)

    def test_old_decoded_flags_never_become_fresh_candidate_av(self):
        url="https://fixture.example.org/old-av.m3u8"
        old=[{"url":url,"source":"historical","status":"VIDEO_AUDIO_DECODED",
              "decoded":True,"video":True,"audio":True,
              "av_verified":True,"device_verified":True,
              "ibo_device_verified":True}]
        current=[{"url":url,"source":"fresh","decoded":True,
                  "video":True,"audio":True,"av_verified":True}]
        raw,view,_=reconcile(old,current)
        self.assertEqual(raw,old+current)
        self.assertEqual(len(view),1)
        self.assertEqual(view[0]["source_ids"],["historical","fresh"])
        self.assertEqual(view[0]["status"],"NOT_REVERIFIED")
        self.assertEqual(raw[0]["status"],"VIDEO_AUDIO_DECODED")
        for flag in ("decoded","video","audio","av_verified",
                     "device_verified","ibo_device_verified"):
            with self.subTest(flag=flag):
                self.assertIs(view[0][flag],False)

    def test_duplicate_sources_preserve_history_without_promoting_claimed_av(self):
        url="https://fixture.example.org/source.m3u8"
        old=[{"url":url,"source":"historical","av_verified":True},
             {"url_sha256":hashlib.sha256(url.encode()).hexdigest(),
              "source":"hash-only"}]
        current=[{"url":url,"source":"new-a","av_verified":True},
                 {"url":url,"source":"new-b","av_verified":True}]
        raw,view,report=reconcile(old,current)
        self.assertEqual(raw,old+current)
        self.assertEqual(len(view),1)
        self.assertEqual(view[0]["source_ids"],
                         ["hash-only","historical","new-a","new-b"])
        self.assertIs(view[0]["av_verified"],False)
        self.assertIs(view[0]["device_verified"],False)
        self.assertEqual(report["current_duplicate_url_rows"],1)

    def test_encrypted_snapshot_restores_every_raw_row_and_deduplicated_view(self):
        old = [{"url": "https://fixture.example.org/a.m3u8", "source": "#60"},
               {"url": "https://fixture.example.org/a.m3u8", "logo": "old"},
               {"url_sha256": hashlib.sha256(b"lost").hexdigest()}]
        preserved, indexed, report = reconcile(old)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "historic.enc"
            with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
                self.assertTrue(preserve_to_new_archive(path, preserved, indexed))
                self.assertFalse(stat.S_IMODE(path.stat().st_mode) & 0o077)
                snapshot = restore(path)
                raw = [r for block in snapshot if block["kind"] == "raw_historical_and_new"
                       for r in block["records"]]
                view = [r for block in snapshot if block["kind"] == "deduplicated_view"
                        for r in block["records"]]
                self.assertEqual(raw, old)
                self.assertEqual(view, indexed)
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    preserve_to_new_archive(path, preserved, indexed)
        self.assertEqual(report["historical_records_preserved"], 3)


    def test_stage2_2643_lost_address_candidates_preserve_every_source_record(self):
        """#6: a bulk recovery queue must not lose duplicate provenance.

        This is an offline invariant, NOT a real FFmpeg probe or recovery.
        """
        historical = [{"url_sha256": hashlib.sha256(b"historical").hexdigest(),
                       "source_id": "immutable-history"}]
        current = []
        for index in range(2643):
            url = "https://fixture.example.org/lost/%04d.m3u8" % index
            current.append({"url": url, "source_id": "lost-address-%04d" % index})
        duplicate = dict(current[0], source_id="second-source")
        current.append(duplicate)
        raw, candidates, report = reconcile(historical, current, 1)
        self.assertEqual(raw[:1], historical)
        self.assertEqual(raw[1:], current)
        self.assertEqual(report["current_records_preserved"], 2644)
        self.assertEqual(report["current_duplicate_url_rows"], 1)
        self.assertEqual(report["unique_candidate_urls"], 2643)
        self.assertEqual(candidates[0]["source_ids"],
                         ["lost-address-0000", "second-source"])
        self.assertTrue(all(row["status"] == "NOT_REVERIFIED"
                            and row["av_verified"] is False
                            and row["device_verified"] is False
                            for row in candidates))
        self.assertEqual(report["real_streams_reverified"], 0)
        self.assertFalse(report["channel_playlist_modified"])


if __name__ == "__main__":
    unittest.main()
