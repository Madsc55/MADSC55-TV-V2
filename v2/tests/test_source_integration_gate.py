#!/usr/bin/env python3
"""Grouped source-to-channel-scan acceptance regressions, offline and read-only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_integration_gate as gate


def report_fixture(name):
    data = {}
    for field, definition in gate.SHAPES[name]:
        data[field] = definition() if isinstance(definition, type) else definition
    if name == "source_availability":
        data.update(source_count=0, playback_verified=False)
    if name == "github_gist":
        data.update(sources_found=0, playback_verified=False, limits_hit=[])
    if name == "gitlab_codeberg":
        data.update(source_count=0, playback_verified=False, limits_hit=[])
    if name in ("official_live_pages", "webpage_indexes"):
        data["playback_verified"] = False
    if name == "youtube":
        data["queries"] = ["Turkish broadcaster live"]
        data["live_verified"] = 0
    if name == "document_platforms":
        data.update(
            platforms={key: {"queries": 1, "errors": 0}
                       for key in ("scribd", "slideshare", "internet-archive")},
            playback_verified=False, validated_m3u_source_count=0)
    if name == "channel_scan":
        data.update(candidate_status="UNVERIFIED",
                    coverage_status="COMPLETE_SOURCE_FETCH")
    return data


class IntegrationGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.config = root / "sources.json"
        self.reports = {k: root / (k + ".json") for k in gate.REPORTS}
        self.c1 = patch.object(gate, "CONFIG", self.config)
        self.c2 = patch.object(gate, "REPORTS", self.reports)
        self.c1.start()
        self.c2.start()
        self.addCleanup(self.c1.stop)
        self.addCleanup(self.c2.stop)
        self.write_sources(sorted(gate.REQUIRED))
        for name in self.reports:
            self.write_report(name, report_fixture(name))

    def write_sources(self, ids):
        self.config.write_text(json.dumps({
            "policy": "discovery-only; never modify live playlist",
            "sources": [{"id": item, "url": "https://example.org/" + item + ".m3u"}
                        for item in ids]
        }), encoding="utf-8")

    def write_report(self, name, data):
        self.reports[name].write_text(json.dumps(data), encoding="utf-8")

    def test_all_real_adapter_signatures_and_channel_scan_are_wired(self):
        result = gate.audit()
        self.assertEqual(result["status"], "INTEGRATED_REFERENCES_NOT_AV_VERIFIED")
        self.assertEqual(len(result["adapter_reports"]), 11)
        self.assertTrue(all(x == "VALID" for x in result["adapter_reports"].values()))
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["av_verified"])
        self.assertFalse(result["spoken_language_verified"])
        self.assertFalse(result["ibo_device_verified"])
        self.assertFalse(result["main_playlist_modified"])
        self.assertEqual(result["routing"]["youtube"],
                         "EXACT_LIVE_UPLOADER_TO_M3U_IDENTITY_LINK_ONLY_NO_DIRECT_IBO_HLS")

    def test_routing_matrix_all_requested_families_still_not_playback_accepted(self):
        result = gate.audit()
        self.assertTrue(result["adapter_wiring_valid"])
        self.assertTrue(result["channel_candidate_scan_present"])
        self.assertTrue(result["external_source_coverage_complete"])
        self.assertFalse(result["full_av_playback_accepted"])
        self.assertEqual(len(result["source_families"]), 13)
        for key in ("youtube_turkish_live", "scribd_slideshare_internet_archive",
                    "azerbaijan_azerice", "europe_world_turkish",
                    "gunes_rec_gopik", "github_gist", "gitlab_codeberg"):
            self.assertIn(key, result["source_families"])
        self.assertFalse(result["source_families"]["youtube_turkish_live"]["direct_ibo_hls_verified"])

    def test_partial_external_source_errors_do_not_hide_valid_wiring(self):
        github = report_fixture("github_gist")
        github["coverage_status"] = "PARTIAL_API"
        github["errors"] = [{"reason": "TEMPORARY_HTTP_ERROR"}]
        self.write_report("github_gist", github)
        result = gate.audit()
        self.assertTrue(result["adapter_wiring_valid"])
        self.assertFalse(result["external_source_coverage_complete"])
        self.assertEqual(result["status"], "PARTIAL_REFERENCES_NOT_AV_VERIFIED")
        self.assertFalse(result["full_av_playback_accepted"])

    def test_missing_document_report_rejects_structural_routing(self):
        self.reports["document_handoff"].unlink()
        result = gate.audit()
        self.assertFalse(result["adapter_wiring_valid"])
        self.assertIn("INCOMPLETE_ADAPTER_HANDOFF", result["errors"])

    def test_live_page_inspection_is_not_misreported_as_no_adapter_handoff(self):
        scan = report_fixture("channel_scan")
        scan["approved_live_page_handoff"] = {
            "schema": 1, "new_pages_queued": 27, "pages_inspected": 27,
            "pages_unavailable": 5, "pages_with_m3u_links": 0,
            "playback_verified": False}
        self.write_report("channel_scan", scan)
        result = gate.audit()
        live = result["source_families"]["live_tv_websites"]
        self.assertTrue(live["approved_page_inspection_complete"])
        self.assertEqual(live["approved_pages_inspected"], 27)
        self.assertEqual(live["unavailable_pages"], 5)
        self.assertEqual(live["m3u_links_found"], 0)
        self.assertFalse(live["av_playback_verified"])
        self.assertIn("PARTIAL_LIVE_PAGE_INSPECTION", result["errors"])

    def test_real_dynamic_and_live_page_handoff_must_match_actual_scan(self):
        scan = report_fixture("channel_scan")
        scan["public_source_reference_handoff"] = {
            "schema": 1, "report_checked": {
                "github_gist": True, "gitlab_codeberg": True},
            "accepted_for_inspection": {"github_gist": 2, "gitlab_codeberg": 1},
            "bounded_truncation": {"github_gist": 0, "gitlab_codeberg": 0},
            "inspection_records": 3, "parsed_channel_playlists": 3,
            "failed_source_fetches": 0, "playback_verified": False}
        scan["approved_live_page_handoff"] = {
            "new_pages_queued": 2, "pages_inspected": 2,
            "pages_unavailable": 0, "playback_verified": False}
        self.write_report("channel_scan", scan)
        passed = gate.audit()
        self.assertEqual(passed["errors"], [])
        self.assertEqual(passed["actual_candidate_handoff"]
                         ["github_gist_and_gitlab_codeberg"]
                         ["parsed_channel_playlists"], 3)
        scan["public_source_reference_handoff"]["bounded_truncation"]["github_gist"] = -1
        self.write_report("channel_scan", scan)
        self.assertEqual(gate.audit()["adapter_reports"]["channel_scan"], "INVALID")
        scan["public_source_reference_handoff"]["bounded_truncation"]["github_gist"] = 0
        scan["public_source_reference_handoff"]["inspection_records"] = 2
        self.write_report("channel_scan", scan)
        self.assertEqual(gate.audit()["adapter_reports"]["channel_scan"], "INVALID")
        scan["public_source_reference_handoff"]["inspection_records"] = 3
        scan["approved_live_page_handoff"]["pages_inspected"] = 1
        self.write_report("channel_scan", scan)
        self.assertEqual(gate.audit()["adapter_reports"]["channel_scan"], "INVALID")

    def test_static_core_sources_not_dropped(self):
        self.write_sources(sorted(gate.REQUIRED - {"iptv-org-az"}))
        self.assertIn("MISSING_STATIC_SOURCES", gate.audit()["errors"])

    def test_static_duplicates_fail_closed(self):
        self.write_sources(sorted(gate.REQUIRED) + ["iptv-org"])
        self.assertIn("DUPLICATE_SOURCE_IDS", gate.audit()["errors"])

    def test_missing_adapters_and_m3u_scan_fail_closed(self):
        self.reports["channel_scan"].unlink()
        d = gate.audit()
        self.assertEqual(d["adapter_reports"]["channel_scan"], "MISSING")
        self.assertIn("INCOMPLETE_ADAPTER_HANDOFF", d["errors"])

    def test_empty_dictionary_is_not_fake_success(self):
        for name in gate.REPORTS:
            with self.subTest(name=name):
                self.write_report(name, {})
                self.assertEqual(gate.audit()["adapter_reports"][name], "INVALID")
                self.write_report(name, report_fixture(name))

    def test_corrupt_live_adapters_and_youtube_playback_separation(self):
        self.write_report("youtube", {"results": []})
        self.assertEqual(gate.audit()["adapter_reports"]["youtube"], "INVALID")
        self.write_report("youtube", report_fixture("youtube"))
        bad = report_fixture("official_live_pages")
        bad["playback_verified"] = True
        self.write_report("official_live_pages", bad)
        self.assertEqual(gate.audit()["adapter_reports"]["official_live_pages"], "INVALID")

    def test_partial_real_source_fetch_never_green(self):
        scan = report_fixture("channel_scan")
        scan["coverage_status"] = "PARTIAL_SOURCE_FETCH"
        self.write_report("channel_scan", scan)
        d = gate.audit()
        self.assertEqual(d["status"], "PARTIAL_REFERENCES_NOT_AV_VERIFIED")
        self.assertIn("PARTIAL_ADAPTER_COVERAGE", d["errors"])

    def test_document_reference_count_must_match_validated_handoff(self):
        doc = report_fixture("document_platforms")
        doc["validated_m3u_source_count"] = 2
        self.write_report("document_platforms", doc)
        self.assertIn("DOCUMENT_SOURCE_HANDOFF_MISMATCH", gate.audit()["errors"])

    def test_missing_platform_or_inconsistent_official_counts_not_accepted(self):
        doc = report_fixture("document_platforms")
        del doc["platforms"]["slideshare"]
        self.write_report("document_platforms", doc)
        self.assertEqual(gate.audit()["adapter_reports"]["document_platforms"], "INVALID")
        self.write_report("document_platforms", report_fixture("document_platforms"))
        official = report_fixture("official_sites")
        official["count"] = 1
        self.write_report("official_sites", official)
        self.assertEqual(gate.audit()["adapter_reports"]["official_sites"], "INVALID")


if __name__ == "__main__":
    unittest.main()
