#!/usr/bin/env python3
"""Strict source-to-channel-scan handoff. URLs stay private; no AV/device claims.

Static M3U feeds and separately approved dynamic M3U sources enter discover.py.
YouTube, live HTML pages and official broadcaster websites are advisory only.
Incomplete reports never count as a fully integrated source run.
"""
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
        if any(type(x.get("queries")) is not int for x in data["platforms"].values()
               if isinstance(x, dict)):
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
    source_scan = loaded.get("channel_scan", {})
    dynamic_handoff = source_scan.get("public_source_reference_handoff", {})
    live_handoff = source_scan.get("approved_live_page_handoff", {})
    if (dynamic_handoff.get("status") not in (None, "NOT_REQUESTED")
            and (dynamic_handoff.get("failed_source_fetches", 0) > 0
                 or any(dynamic_handoff.get("bounded_truncation", {}).values()))):
        errors.append("PARTIAL_DYNAMIC_SOURCE_INSPECTION")
    if (live_handoff.get("status") not in (None, "NOT_REQUESTED")
            and live_handoff.get("pages_unavailable", 0) > 0):
        errors.append("PARTIAL_LIVE_PAGE_INSPECTION")
    status = ("INCOMPLETE" if errors and "INCOMPLETE_ADAPTER_HANDOFF" in errors or
              "MISSING_STATIC_SOURCES" in errors or "DUPLICATE_SOURCE_IDS" in errors or
              "DOCUMENT_SOURCE_HANDOFF_MISMATCH" in errors
              else "PARTIAL_REFERENCES_NOT_AV_VERIFIED" if errors
              else "INTEGRATED_REFERENCES_NOT_AV_VERIFIED")
    return {
        "schema": 2, "kind": "V2_END_TO_END_CHANNEL_SOURCE_ROUTING_AUDIT",
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
            "official_broadcaster_sites": "OFFICIAL_METADATA_IDENTITY_REVIEW_ONLY",
            "youtube": "LIVE_PAGE_METADATA_ONLY_NO_DIRECT_IBO_HLS",
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
            "github_gist_and_gitlab_codeberg": dynamic_handoff,
            "approved_live_page_indexes": live_handoff,
            "candidate_scan_report_available": "channel_scan" in loaded,
        },
        "av_verified": False, "spoken_language_verified": False,
        "ibo_device_verified": False, "main_playlist_modified": False,
        "private_candidate_urls_exported": False,
    }

if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not result["errors"] else 1)
