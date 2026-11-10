#!/usr/bin/env python3
"""Read-only full M3U payload completeness and historical URL SHA coverage.

Only public playlist files are downloaded. Media segment/stream URLs are NEVER
requested, emitted to logs, committed, or included in any reports.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import re

from discover import entries, has_http_url_hostname
from source_failover import fetch_once

HEX = re.compile(r"[0-9a-f]{64}\Z")


def enumerate_unpaired_reference_evidence(payload):
    """Keep SHA-only identity, line and reason for every unpaired EXTINF record.

    No channel name, URL, access token or original line is emitted in reports.
    """
    issues = []
    pending = None
    def add(reason, original):
        line_number, extinf_line = original
        issues.append({"line_number": line_number,
                       "extinf_sha256": hashlib.sha256(
                           extinf_line.encode("utf-8")).hexdigest(),
                       "reason": reason})
    for line_number, raw in enumerate(payload.splitlines(), 1):
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            if pending is not None:
                add("MISSING_URI_BEFORE_NEXT_EXTINF", pending)
            pending = (line_number, line)
        elif line and not line.startswith("#") and pending is not None:
            if line.startswith(("[NO PUBLIC STREAM]", "[NO STREAM]")):
                add("EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER", pending)
            elif line.startswith(("http://", "https://")) and not has_http_url_hostname(line):
                add("HTTP_URI_WITHOUT_HOST", pending)
            elif not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", line):
                add("INVALID_OR_RELATIVE_STREAM_REFERENCE", pending)
            pending = None
    if pending is not None:
        add("TRAILING_EXTINF_WITHOUT_URI", pending)
    return issues


def analyze_unpaired_reference_reasons(payload):
    evidence = enumerate_unpaired_reference_evidence(payload)
    return dict(sorted(Counter(item["reason"] for item in evidence).items()))


def _one(source, fetcher):
    ident = source["id"]
    if source.get("enabled", True) is False:
        return ({"source_id": ident, "status": "RETIRED_IN_ORIGINAL_INVENTORY",
                 "entries": 0, "unique_urls": 0}, set())
    try:
        # Only original #60 GitHub source URLs proven by the historic
        # discovery artifact may use the less strict headerless M3U parser.
        # Generic configured feeds still require a valid #EXTM3U header.
        if source.get("historical_source_only") and fetcher is fetch_once:
            from discover import fetch as vetted_document_fetch
            payload = vetted_document_fetch(source["url"])
        else:
            payload = fetcher(source["url"])
        if not isinstance(payload, str):
            raise ValueError("INVALID_M3U_PAYLOAD")
        normalized_historical_header = False
        payload_start = payload.lstrip("\ufeff\r\n\t ")
        if not payload_start.startswith("#EXTM3U"):
            if (source.get("historical_source_only")
                    and payload_start.startswith("#EXTINF:")
                    and not source.get("enabled", True) is False):
                payload = "#EXTM3U\n" + payload_start
                normalized_historical_header = True
            else:
                raise ValueError("INVALID_M3U_PAYLOAD")
        parsed = list(entries(payload))
        unique = {hashlib.sha256(e["url"].encode("utf-8")).hexdigest() for e in parsed}
        declared, non_http = 0, 0
        awaiting = False
        for raw in payload.splitlines():
            line = raw.strip()
            if line.startswith("#EXTINF:"):
                declared += 1
                awaiting = True
            elif line and not line.startswith("#") and awaiting:
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", line) and not line.startswith(("http://", "https://")):
                    non_http += 1
                awaiting = False
        # The existing discovery parser intentionally accepts only HTTP(S).
        # UDP/RTMP/RTSP/etc references are not deleted or described as broken.
        dangling = max(0, declared - len(parsed) - non_http)
        orphan_evidence = enumerate_unpaired_reference_evidence(payload)
        reasons = dict(sorted(Counter(x["reason"] for x in orphan_evidence).items()))
        if sum(reasons.values()) != dangling:
            raise ValueError("Malformed reference tally not internally consistent")
        intentionally_unavailable = reasons.get("EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER", 0)
        actual_malformed = dangling - intentionally_unavailable
        state = ("INCOMPLETE_EXTINF_PAIRS" if actual_malformed else
                 "PARSED_WITH_DECLARED_NO_PUBLIC_STREAM_PLACEHOLDERS"
                 if intentionally_unavailable and parsed else
                 "NON_HTTP_ONLY_REFERENCES" if not parsed and non_http else
                 "EMPTY_PLAYLIST" if not parsed else
                 "PARSED_HISTORICAL_HEADERLESS_NORMALIZED_NO_PLAYBACK"
                 if normalized_historical_header else
                 "PARSED_WITH_NON_HTTP_REFERENCES_NOT_PLAYBACK_VERIFIED" if non_http else
                 "PARSED_M3U_NOT_PLAYBACK_VERIFIED")
        return ({"source_id": ident, "status": state,
                 "entries": len(parsed), "unique_urls": len(unique),
                 "duplicate_url_entries": len(parsed) - len(unique),
                 "non_http_stream_references": non_http,
                 "unpaired_extinf": dangling,
                 "actual_malformed_extinf": actual_malformed,
                 "unpaired_reason_counts": reasons,
                 "orphan_reference_evidence": orphan_evidence,
                 "historical_header_normalized": normalized_historical_header}, unique)
    except Exception as exc:
        # Intentionally do not log exception text, request URL, or credentials.
        return ({"source_id": ident, "status": "SOURCE_CONTENT_FAILED",
                 "error_type": type(exc).__name__, "entries": 0,
                 "unique_urls": 0}, set())


def audit_contents(sources, historical_hashes, fetcher=fetch_once, workers=8, primary_source_ids=None):
    if not isinstance(sources, list) or not sources or not 1 <= workers <= 16:
        raise ValueError("Invalid M3U source inventory or parallelism")
    if len({s["id"] for s in sources}) != len(sources):
        raise ValueError("Duplicate M3U source ID")
    original = set(historical_hashes)
    if len(original) != len(historical_hashes) or not all(
            isinstance(h, str) and HEX.fullmatch(h) for h in original):
        raise ValueError("Invalid historical SHA-256 baseline")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        collected = list(pool.map(lambda s: _one(s, fetcher), sources))
    union = set()
    original_only = set()
    enriched = []
    for (row, hashes) in collected:
        union.update(hashes)
        if primary_source_ids is not None and row["source_id"] in primary_source_ids:
            original_only.update(hashes)
        enriched.append({**row,
                         "historical_4955_identifiers_in_source": len(hashes & original)})
    statuses = dict(sorted(Counter(x["status"] for x in enriched).items()))
    active = [x for x in enriched if x["status"] != "RETIRED_IN_ORIGINAL_INVENTORY"]
    valid = [x for x in active if x["status"] in (
        "PARSED_M3U_NOT_PLAYBACK_VERIFIED",
        "PARSED_WITH_NON_HTTP_REFERENCES_NOT_PLAYBACK_VERIFIED",
        "PARSED_HISTORICAL_HEADERLESS_NORMALIZED_NO_PLAYBACK",
        "PARSED_WITH_DECLARED_NO_PUBLIC_STREAM_PLACEHOLDERS")]
    historical_now = union & original
    return {
        "schema": 1,
        "kind": "FULL_M3U_SOURCE_CONTENT_READ_ONLY_NO_MEDIA_PLAYBACK",
        "configured_sources_including_retired": len(enriched),
        "active_sources": len(active),
        "fully_parsed_sources": len(valid),
        "source_content_review_required": len(active) - len(valid),
        "status": "COMPLETE_SOURCE_CONTENT_PARSED" if len(valid) == len(active)
                  else "REVIEW_REQUIRED",
        "source_status_counts": statuses,
        "non_http_reference_count": sum(x.get("non_http_stream_references", 0) for x in active),
        "unpaired_extinf_count": sum(x.get("unpaired_extinf", 0) for x in active),
        "actual_malformed_extinf_count":
            sum(x.get("actual_malformed_extinf", 0) for x in active),
        "unpaired_reason_totals": dict(sorted(
            sum((Counter(x.get("unpaired_reason_counts", {})) for x in active),
                Counter()).items())),
        "source_results": enriched,
        "union_unique_url_sha256": len(union),
        "historical_baseline_count": len(original),
        "historical_identifiers_present_in_current_sources": len(historical_now),
        "historical_identifiers_in_configured_sources_only":
            len(original_only & original) if primary_source_ids is not None else None,
        "additional_historical_identities_from_restored_source_locations":
            len(historical_now - original_only) if primary_source_ids is not None else None,
        "historical_identifiers_absent_from_current_sources":
            len(original - historical_now),
        "historical_identifiers_absent_sha256_full":
            sorted(original - historical_now),
        "historical_identifiers_absent_sha256_sample":
            sorted(original - historical_now)[:30],
        "current_streams_playback_checked": 0,
        "stream_audio_video_verified": False,
        "iban_player_device_verified": False,
        "playlist_modified": False,
        "note": "No stream URLs requested; absence from current source feeds does not mean a stream is dead.",
    }
