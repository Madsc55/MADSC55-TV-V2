#!/usr/bin/env python3
"""Exact-ID alternatives for blocked official TR live pages: source-only evidence.

Inspect previously approved public M3U files, not forbidden publisher websites.
All stream URLs remain private in RSA-encrypted transit, never logs/reports.
Source matching does not prove HTTP stream access, video+audio, rights or IBO.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from discover import entries, fetch
from historical_url_recovery import validate_url
from stage3_sealed_export import seal_rows
from webpage_source_discovery import candidate_url

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config/sources.json"
PUBLIC_KEY = ROOT / "config/stage3_transit_public.pem"

# IDs come from reviewed publisher watchlist + existing IPTV-org TVG registry.
# Only exact TVG ID + compatible channel display name are admissible.
TARGETS = {
    "trt-spor-official": ("trtspor.tr", "trt spor"),
    "tv100-official": ("tv100.tr", "tv 100"),
    "benguturk-official": ("benguturktv.tr", "benguturk tv"),
    "ulusal-kanal-official": ("ulusalkanal.tr", "ulusal kanal"),
    "halk-tv-official": ("halktv.tr", "halk tv"),
}
# Approved, already configured sources. No external search results promoted.
SOURCES = frozenset({
    "iptv-org-tr", "iptv-org-tr-streams", "iptv-turk-tr",
    "hayatiptv-tr-master", "discevisita-tr", "sayatsirinoglu-tr",
})
MAX_ENTRIES_PER_SOURCE = 25000
MAX_CONFIGURED_SOURCES = 64


def normalized_name(s):
    if not isinstance(s, str) or len(s) > 200:
        return ""
    # Strip playlist annotations, not arbitrary channel words.
    s = re.sub(r"\([^)]*\)|\[[^]]*\]", "", s)
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ı", "i").replace("ø", "o")
    s = re.sub(r"(?i)\b(?:full\s*hd|fhd|uhd|qhd|hd|sd|4k)\b\s*$", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def exact_target(entry):
    channel_id = entry.get("tvg_id", "")
    if not isinstance(channel_id, str):
        return None
    channel_id = channel_id.split("@", 1)[0].casefold()
    name = normalized_name(entry.get("name", ""))
    for page_id, (expected_id, expected_name) in TARGETS.items():
        if channel_id == expected_id and name == normalized_name(expected_name):
            return page_id
    return None


def audit(config, *, reader=fetch):
    """Use every configured active M3U feed, keeping six mandatory sources.

    Additional configured sources are only candidate references, never auto-
    approved playback. Exact TVG identity + display name is required for every
    stream; FFprobe and real FFmpeg evidence are a separate validation step.
    """
    if not isinstance(config, dict) or not isinstance(config.get("sources"), list):
        raise ValueError("Missing configured public source inventory")
    if len(config["sources"]) > MAX_CONFIGURED_SOURCES:
        raise ValueError("Source catalog exceeds guarded search scope")
    approved, source_status, seen_ids = {}, {}, set()
    for row in config["sources"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid source entry")
        sid, url = row.get("id"), row.get("url")
        if (not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", sid)
                or sid in seen_ids):
            raise ValueError("Duplicate or invalid configured source identity")
        seen_ids.add(sid)
        if row.get("enabled", True) is False:
            continue
        if not candidate_url(url):
            if sid in SOURCES:
                raise ValueError("Unsafe mandatory source")
            source_status[sid] = "INVALID_CONFIGURED_URL"
            continue
        approved[sid] = url
    if not SOURCES <= set(approved):
        raise ValueError("Six previously approved M3U sources required")

    def read_one(pair):
        sid, url = pair
        try:
            data = reader(url)
            if (not isinstance(data, str)
                    or not data.lstrip("\ufeff\r\n\t ").startswith("#EXTM3U")):
                raise ValueError("Source not M3U")
            matches = []
            for count, entry in enumerate(entries(data), 1):
                if count > MAX_ENTRIES_PER_SOURCE:
                    raise ValueError("Oversized M3U entry inventory")
                page_id = exact_target(entry)
                stream = entry.get("url")
                if page_id is not None and validate_url(stream):
                    matches.append((page_id, stream))
            return sid, "READ_VALID_M3U", matches
        except (OSError, ValueError, TypeError, UnicodeError):
            return sid, "UNAVAILABLE_OR_INVALID", []

    candidate_by_sha, matched_pages = {}, defaultdict(set)
    # Eight bounded workers, never one network request per channel candidate.
    with ThreadPoolExecutor(max_workers=8) as pool:
        for sid, status, matches in pool.map(read_one, sorted(approved.items())):
            source_status[sid] = status
            if status != "READ_VALID_M3U":
                continue
            for page_id, stream in matches:
                digest = hashlib.sha256(stream.encode("utf-8")).hexdigest()
                row = candidate_by_sha.setdefault(digest, {
                    "url": stream, "url_sha256": digest,
                    "matched_blocked_pages": set(), "source_ids": set(),
                    "proof_rule": "EXACT_TVG_ID_AND_DISPLAY_NAME",
                    "video_audio_verified": False, "ibo_device_verified": False})
                if row["url"] != stream:
                    raise ValueError("Candidate SHA collision")
                row["matched_blocked_pages"].add(page_id)
                row["source_ids"].add(sid)
                matched_pages[page_id].add(digest)

    sealed = []
    for digest in sorted(candidate_by_sha):
        row = candidate_by_sha[digest]
        sealed.append({**row,
            "matched_blocked_pages": sorted(row["matched_blocked_pages"]),
            "source_ids": sorted(row["source_ids"])})
    valid = lambda sid: source_status.get(sid) == "READ_VALID_M3U"
    supplemental = set(source_status) - SOURCES
    report = {
        "schema": 1, "kind": "BLOCKED_OFFICIAL_PAGES_EXACT_SOURCE_ONLY",
        "target_pages": len(TARGETS),
        "configured_sources_checked": len(SOURCES),
        "configured_sources_valid": sum(valid(sid) for sid in SOURCES),
        "all_configured_active_sources_checked": len(source_status),
        "all_configured_active_sources_valid": sum(valid(sid) for sid in source_status),
        "supplemental_sources_checked": len(supplemental),
        "supplemental_sources_valid": sum(valid(sid) for sid in supplemental),
        "supplemental_sources_unavailable": sorted(
            sid for sid in supplemental if not valid(sid)),
        "full_configured_catalog_source_coverage_complete":
            all(valid(sid) for sid in source_status),
        "source_status": dict(sorted(source_status.items())),
        "candidate_url_count": len(sealed),
        "candidate_channel_counts": {key: len(matched_pages[key]) for key in TARGETS},
        "candidate_url_sha256": sorted(candidate_by_sha),
        "blocked_page_count_with_candidate":
            sum(bool(matched_pages[x]) for x in TARGETS),
        "blocked_page_ids_without_exact_candidate":
            sorted(x for x in TARGETS if not matched_pages[x]),
        "remaining_official_http_access_errors_resolved": False,
        "external_source_coverage_complete": False,
        "video_audio_verified": False, "ibo_device_verified": False,
        "protected_ibo_playlist_modified": False,
        "no_plaintext_stream_urls": True,
    }
    return report, sealed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exact-source-handoff", action="store_true", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--sealed", type=Path, required=True)
    args = parser.parse_args()
    if (args.report.resolve() == args.sealed.resolve()
            or args.report.exists() or args.report.is_symlink()
            or args.sealed.exists() or args.sealed.is_symlink()):
        parser.error("Refusing evidence overwrite")
    source_config = json.loads(CONFIG.read_text(encoding="utf-8"))
    report, private = audit(source_config)
    if private:
        seal_rows(private, PUBLIC_KEY, args.sealed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BLOCKED_OFFICIAL_EXACT_SOURCE", json.dumps({
        k: report[k] for k in (
            "target_pages", "configured_sources_checked", "configured_sources_valid",
            "all_configured_active_sources_checked",
            "all_configured_active_sources_valid",
            "supplemental_sources_unavailable",
            "candidate_url_count", "candidate_channel_counts",
            "blocked_page_count_with_candidate", "blocked_page_ids_without_exact_candidate",
            "remaining_official_http_access_errors_resolved", "video_audio_verified"
        )}, sort_keys=True))


if __name__ == "__main__":
    main()
