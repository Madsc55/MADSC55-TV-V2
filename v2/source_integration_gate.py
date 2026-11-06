#!/usr/bin/env python3
"""Strict source-to-channel-scan handoff. URLs stay private; no AV/device claims.

Static M3U feeds and separately approved dynamic M3U sources enter discover.py.
YouTube, live HTML pages and official broadcaster websites are advisory only.
Incomplete reports never count as a fully integrated source run.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "v2/config/sources.json"
REPORTS = {
    "source_availability": ROOT / "v2/reports/source-availability-audit.json",
    "github_gist": ROOT / "v2/reports/github-source-discovery.json",
    "gitlab_codeberg": ROOT / "v2/reports/forge-source-discovery.json",
    "official_live_pages": ROOT / "v2/reports/live-page-references.json",
    "webpage_indexes": ROOT / "v2/reports/webpage-playlist-references.json",
    "youtube": ROOT / "v2/reports/youtube-live-candidates.json",
    "document_platforms": ROOT / "v2/reports/document-platform-references.json",
    "document_handoff": ROOT / "v2/reports/document-platform-sources.json",
    "official_sites": ROOT / "v2/reports/official-tv-sites.json",
    "official_site_matching": ROOT / "v2/reports/official-tv-gap.json",
    "channel_scan": ROOT / "v2/reports/candidates.json",
}
REQUIRED = {
    "iptv-org", "iptv-org-tr", "iptv-org-az", "iptv-org-se",
    "iptv-org-tur-language", "iptv-org-aze-language",
    "iptv-org-region-europe", "iptv-org-worldwide",
    "free-tv-independent", "dearbulut-tr", "dearbulut-online",
    "dearbulut-all-candidates", "dearbulut-best-ranked",
    "turktv-itasli-archive", "onureroz-turk-index",
    "onureroz-turk-all", "onureroz-turk-karma", "onureroz-world-index",
}
# Required fields are checked by type and exact source-report semantics.
SHAPES = {
    "source_availability": (("schema", 1), ("kind", "source-level-only"), ("results", list)),
    "github_gist": (("policy", "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT"),
                    ("sources", list), ("errors", list), ("coverage_status", str)),
    "gitlab_codeberg": (("schema", 1), ("status", "source_references_only"),
                        ("sources", list), ("errors", list), ("coverage_status", str)),
    "official_live_pages": (("schema", 1), ("kind", "references-only"),
                            ("references", list), ("errors", list)),
    "webpage_indexes": (("schema", 1), ("kind", "playlist-references-only"),
                        ("references", list), ("errors", list)),
    "youtube": (("policy", "ADVISORY_ONLY_NO_PLAYLIST_WRITES_NO_AUTOMATIC_IBO_IMPORT"),
                ("queries", list), ("results", list), ("errors", list)),
    "document_platforms": (("schema", 1), ("kind", "PUBLIC_DOCUMENT_REFERENCES_ONLY"),
                           ("platforms", dict), ("references", list), ("errors", list)),
    "document_handoff": (("schema", 1), ("kind", "DOCUMENT_PLATFORM_M3U_HANDOFF"),
                         ("sources", list)),
    "official_sites": (("policy", "READ_ONLY_NO_PLAYLIST_CHANGES_NO_DRM_BYPASS"),
                       ("channels", list), ("count", int)),
    "official_site_matching": (("matched_sites", list), ("unmatched_sites", list),
                               ("matched", int), ("not_exactly_matched", int)),
    "channel_scan": (("schema", 1), ("candidates", list),
                     ("source_audit", list), ("coverage_status", str),
                     ("playback_verified", False)),
}
NO_AV_FAMILIES = {
    "source_availability", "github_gist", "gitlab_codeberg",
    "official_live_pages", "webpage_indexes", "document_platforms",
}
PARTIAL_MARKERS = ("PARTIAL", "NO_SOURCES_ACCESSIBLE", "NO_SOURCES_REACHABLE")

def _valid(name, data):
    if not isinstance(data, dict):
        return False
    for field, expected in SHAPES[name]:
        value = data.get(field)
        if isinstance(expected, type):
            if type(value) is not expected:
                return False
        elif value != expected:
            return False
    if name in NO_AV_FAMILIES and data.get("playback_verified") is not False:
        return False
    if name == "youtube" and not data["queries"]:
        return False
    if name == "document_platforms":
        if set(("scribd", "slideshare", "internet-archive")) - set(data["platforms"]):
            return False
        if type(data.get("validated_m3u_source_count")) is not int:
            return False
        if any(not isinstance(x, dict) or type(x.get("queries")) is not int
               or x["queries"] < 0 for x in data["platforms"].values()):
            return False
    if name == "official_sites" and len(data["channels"]) != data["count"]:
        return False
    if name == "official_site_matching" and (
            data["matched"] != len(data["matched_sites"]) or
            data["not_exactly_matched"] != len(data["unmatched_sites"])):
        return False
    if name == "gitlab_codeberg" and data.get("source_count") != len(data["sources"]):
        return False
    if name == "github_gist" and data.get("sources_found") != len(data["sources"]):
        return False
    if name == "source_availability" and data.get("source_count") != len(data["results"]):
        return False
    if name == "channel_scan":
        if data.get("candidate_status") != "UNVERIFIED":
            return False
        source_handoff = data.get("public_source_reference_handoff")
        live_handoff = data.get("approved_live_page_handoff")
        advisory = data.get("advisory_channel_identity_handoff")
        if any(x is not None and not isinstance(x, dict) for x in
               (advisory, source_handoff, live_handoff)):
            return False
        if advisory is not None and (advisory.get("av_verified") is not False
                                    or advisory.get("ibo_device_verified") is not False
                                    or advisory.get("youtube_pages_are_not_m3u_streams") is not True
                                    or advisory.get("official_websites_are_not_m3u_streams") is not True
                                    or type(advisory.get("linked_m3u_candidates")) is not int
                                    or not isinstance(advisory.get("links"), list)
                                    or advisory["linked_m3u_candidates"] != len(advisory["links"])):
            return False
        if source_handoff is not None and source_handoff.get("status") != "NOT_REQUESTED":
            if (not isinstance(source_handoff.get("report_checked"), dict)
                    or set(source_handoff["report_checked"]) !=
                    {"github_gist", "gitlab_codeberg"}
                    or any(value is not True for value in source_handoff["report_checked"].values())
                    or any(type(source_handoff.get(field)) is not int for field in (
                        "inspection_records", "parsed_channel_playlists", "failed_source_fetches"))
                    or source_handoff.get("playback_verified") is not False):
                return False
            expected = sum(source_handoff.get("accepted_for_inspection", {}).values())
            if expected != source_handoff["inspection_records"]:
                return False
        if live_handoff is not None and live_handoff.get("status") != "NOT_REQUESTED":
            if (type(live_handoff.get("new_pages_queued")) is not int
                    or type(live_handoff.get("pages_inspected")) is not int
                    or live_handoff["new_pages_queued"] != live_handoff["pages_inspected"]
                    or live_handoff.get("playback_verified") is not False):
                return False
    return True

def audit():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    sources = cfg.get("sources")
    if not isinstance(sources, list) or cfg.get("policy") != "discovery-only; never modify live playlist":
        raise ValueError("Invalid immutable static source inventory")
    ids = [s.get("id") for s in sources]
    missing = sorted(REQUIRED - {s.get("id") for s in sources
                                 if s.get("enabled", True) is not False})
    duplicates = sorted({x for x in ids if ids.count(x) > 1})
    reports, counts, problems = {}, {}, []
    loaded = {}
    for name, path in REPORTS.items():
        if not path.is_file():
            reports[name] = "MISSING"
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            reports[name] = "VALID" if _valid(name, payload) else "INVALID"
            if reports[name] != "VALID":
                continue
            loaded[name] = payload
            candidates = payload.get("sources", payload.get("references",
                         payload.get("results", payload.get("channels",
                         payload.get("candidates", [])))))
            counts[name] = len(candidates) if isinstance(candidates, list) else 0
            coverage = str(payload.get("coverage_status", ""))
            if coverage.startswith(PARTIAL_MARKERS):
                problems.append(name + ":PARTIAL_COVERAGE")
            if isinstance(payload.get("errors"), list) and payload["errors"]:
                problems.append(name + ":SOURCE_ERRORS")
            if payload.get("limits_hit"):
                problems.append(name + ":DISCOVERY_BOUNDED_LIMIT")
        except (OSError, ValueError, TypeError, KeyError):
            reports[name] = "INVALID"
    errors = []
    if missing:
        errors.append("MISSING_STATIC_SOURCES")
    if duplicates:
        errors.append("DUPLICATE_SOURCE_IDS")
    if any(v != "VALID" for v in reports.values()):
        errors.append("INCOMPLETE_ADAPTER_HANDOFF")
    docs = loaded.get("document_platforms")
    handoff = loaded.get("document_handoff")
    if docs and handoff and docs["validated_m3u_source_count"] != len(handoff["sources"]):
        errors.append("DOCUMENT_SOURCE_HANDOFF_MISMATCH")
    if problems:
        errors.append("PARTIAL_ADAPTER_COVERAGE")
    # API references are metadata only. Cross-validate exact channel ID plus
    # public URL hash against the M3U scan; never invent playable candidates.
    api_crosswalk = {"status": "API_REPORT_NOT_PRESENT"}
    api_report = ROOT / "v2/reports/ci/traz-api-source-audit.json"
    if api_report.exists() and "channel_scan" in loaded:
        try:
            from traz_api_m3u_bridge import load_and_join
            api_crosswalk = load_and_join(
                api_report, REPORTS["channel_scan"])
            api_crosswalk["status"] = "EXACT_HASH_AND_ID_AUDITED"
        except (OSError, ValueError, TypeError, KeyError):
            api_crosswalk = {"status": "INVALID_API_CROSSWALK",
                             "av_verified": False}
            problems.append("traz_api:INVALID_CROSSWALK")
    source_scan = loaded.get("channel_scan", {})
    dynamic_handoff = source_scan.get("public_source_reference_handoff", {})
    live_handoff = source_scan.get("approved_live_page_handoff", {})
    advisory_handoff = source_scan.get("advisory_channel_identity_handoff", {})
    if (dynamic_handoff.get("status") not in (None, "NOT_REQUESTED")
            and (dynamic_handoff.get("failed_source_fetches", 0) > 0
                 or any(dynamic_handoff.get("bounded_truncation", {}).values()))):
        errors.append("PARTIAL_DYNAMIC_SOURCE_INSPECTION")
    # Live-page handoff has no mandatory 'status' field: the page counters
    # themselves are evidence. Never hide unreachable pages because status
    # is omitted in an otherwise valid scan report.
    if (live_handoff.get("pages_unavailable", 0) > 0
            or live_handoff.get("pages_inspected", 0) <
               live_handoff.get("new_pages_queued", 0)):
        errors.append("PARTIAL_LIVE_PAGE_INSPECTION")
    status = ("INCOMPLETE" if errors and "INCOMPLETE_ADAPTER_HANDOFF" in errors or
              "MISSING_STATIC_SOURCES" in errors or "DUPLICATE_SOURCE_IDS" in errors or
              "DOCUMENT_SOURCE_HANDOFF_MISMATCH" in errors
              else "PARTIAL_REFERENCES_NOT_AV_VERIFIED" if errors
              else "INTEGRATED_REFERENCES_NOT_AV_VERIFIED")
    # Independent measures: complete adapter wiring does not guarantee
    # third-party availability, completed AV decoding, language or IBO playback.
    hard_failures = {"MISSING_STATIC_SOURCES", "DUPLICATE_SOURCE_IDS",
                     "INCOMPLETE_ADAPTER_HANDOFF", "DOCUMENT_SOURCE_HANDOFF_MISMATCH"}
    adapter_wiring_valid = not bool(hard_failures.intersection(errors))
    family = {
        "turkish_m3u_m3u8": {
            "source_configured": not bool(missing), "candidate_scan_connected": "channel_scan" in loaded,
            "av_playback_complete": False},
        "iptv_org_world_tr_az_and_language": {
            "source_configured": not bool(missing), "candidate_scan_connected": "channel_scan" in loaded,
            "spoken_language_verified": False},
        "free_tv": {"source_configured": "free-tv-independent" in ids,
                    "candidate_scan_connected": "channel_scan" in loaded},
        "github_gist": {"adapter_report_valid": "github_gist" in loaded,
                        "candidate_scan_handoff": dynamic_handoff.get("report_checked", {}).get("github_gist") is True},
        "gitlab_codeberg": {"adapter_report_valid": "gitlab_codeberg" in loaded,
                            "candidate_scan_handoff": dynamic_handoff.get("report_checked", {}).get("gitlab_codeberg") is True},
        "live_tv_websites": {
            "adapter_report_valid": "official_live_pages" in loaded,
            "approved_page_inspection_complete": (
                type(live_handoff.get("new_pages_queued")) is int
                and type(live_handoff.get("pages_inspected")) is int
                and live_handoff["pages_inspected"] == live_handoff["new_pages_queued"]),
            "approved_pages_inspected": live_handoff.get("pages_inspected", 0),
            "unavailable_pages": live_handoff.get("pages_unavailable", 0),
            "m3u_links_found": live_handoff.get("pages_with_m3u_links", 0),
            "av_playback_verified": False},
        "official_broadcaster_sites": {"adapter_report_valid": "official_sites" in loaded,
                                      "identity_review_connected": "official_site_matching" in loaded,
                                      "av_playback_complete": False},
        "youtube_turkish_live": {"adapter_report_valid": "youtube" in loaded,
                                 "metadata_live_verified_count": loaded.get("youtube", {}).get("live_verified", 0),
                                 "direct_ibo_hls_verified": False},
        "azerbaijan_azerice": {"source_configured": not bool(missing),
                               "spoken_language_verified": False},
        "europe_world_turkish": {"source_configured": not bool(missing),
                                 "diaspora_completeness_verified": False},
        "gunes_rec_gopik": {"exact_metadata_watchlist_connected": "channel_scan" in loaded,
                            "av_playback_complete": False},
        "turktv_dearbulut_onureroz": {"source_configured": not bool(missing),
                                     "candidate_scan_connected": "channel_scan" in loaded},
        "scribd_slideshare_internet_archive": {
            "adapter_report_valid": "document_platforms" in loaded,
            "validated_public_m3u_sources": len(handoff.get("sources", [])) if handoff else 0,
            "candidate_scan_connected": "channel_scan" in loaded,
            "platforms": {
                platform: {
                    "queries": loaded.get("document_platforms", {}).get("platforms", {}).get(platform, {}).get("queries", 0),
                    "sources_discovered": loaded.get("document_platforms", {}).get("platforms", {}).get(platform, {}).get("candidate_sources", 0)}
                for platform in ("scribd", "slideshare", "internet-archive")},
            "av_playback_complete": False},
    }
    return {
        "schema": 2, "kind": "V2_END_TO_END_CHANNEL_SOURCE_ROUTING_AUDIT",
        "adapter_wiring_valid": adapter_wiring_valid,
        "external_source_coverage_complete": not bool(errors),
        "channel_candidate_scan_present": "channel_scan" in loaded,
        "full_av_playback_accepted": False,
        "source_families": family,
        "status": status, "static_source_count": len(sources),
        "missing_static_sources": missing, "duplicate_source_ids": duplicates,
        "adapter_reports": reports, "anonymous_row_counts": counts,
        "degraded_source_families": sorted(set(problems)), "errors": errors,
        "routing": {
            "iptv_org_tr_az_world_and_languages": "CONFIGURED_M3U_CHANNEL_SCAN",
            "free_tv_dearbulut_turktv_onureroz": "CONFIGURED_M3U_CHANNEL_SCAN",
            "github_gist": "HASH_APPROVED_M3U_ONLY",
            "gitlab_codeberg": "HASH_APPROVED_M3U_ONLY",
            "document_platforms": "VALIDATED_PUBLIC_M3U_ONLY",
            "live_web_pages": "REFERENCE_ONLY_UNLESS_APPROVED_INDEX_M3U_PARSED",
            "official_broadcaster_sites": "EXACT_OFFICIAL_CATALOG_ID_AND_NAME_TO_M3U_LINK_NOT_AV",
            "youtube": "EXACT_LIVE_UPLOADER_TO_M3U_IDENTITY_LINK_ONLY_NO_DIRECT_IBO_HLS",
            "turkish_m3u": "STATIC_M3U_CHANNEL_CANDIDATE_SCAN_NOT_AV",
            "iptv_org": "WORLD_TR_AZ_TUR_AZE_COUNTRY_LANGUAGE_SOURCE_CANDIDATES",
            "free_tv": "INDEPENDENT_M3U_SOURCE_CANDIDATES",
            "europe_diaspora": "WORLD_AND_EUROPE_METADATA_ONLY_SPOKEN_LANGUAGE_UNKNOWN",
            "azerbaijan_azerice": "AZ_AND_AZE_SOURCES_SPOKEN_LANGUAGE_NOT_VERIFIED",
            "live_tv_websites": "APPROVED_HTML_PAGES_M3U_LIST_LINKS_ONLY",
            "official_broadcaster_streams": "WEBSITE_DIRECTORY_NOT_HLS_OR_AV",
            "gunes_rec_gopik": "EXACT_NAME_WATCHLIST_NOT_AV",
            "document_adapters": "SCRIBD_SLIDESHARE_INTERNET_ARCHIVE_PUBLIC_M3U_ONLY",
        },
        "actual_candidate_handoff": {
            "official_sites_and_youtube_exact_metadata": advisory_handoff,
            "github_gist_and_gitlab_codeberg": dynamic_handoff,
            "approved_live_page_indexes": live_handoff,
            "candidate_scan_report_available": "channel_scan" in loaded,
        },
        "av_verified": False, "spoken_language_verified": False,
        "ibo_device_verified": False, "main_playlist_modified": False,
        "private_candidate_urls_exported": False,
        "traz_api_exact_crosswalk": api_crosswalk,
    }

def main():
    parser = argparse.ArgumentParser(description="Separate source wiring from live coverage and AV acceptance")
    parser.add_argument("--accept-partial-routing", action="store_true",
                        help="Exit zero for structurally connected sources while reporting partial external coverage; NEVER approve playback")
    args = parser.parse_args()
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.accept_partial_routing:
        return 0 if not result["errors"] else 1
    if not result["adapter_wiring_valid"]:
        return 1
    if not result["channel_candidate_scan_present"]:
        return 1
    if result["full_av_playback_accepted"] or result["av_verified"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
