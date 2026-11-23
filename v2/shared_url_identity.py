#!/usr/bin/env python3
"""Read-only shared IPTV URL review; stream identity is never inferred from labels."""
from collections import defaultdict
import hashlib
from urllib.parse import urlsplit, urlunsplit


def normalized_url(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            return None
        # Keep the entire path/query. In particular, token and program query
        # parameters can select different resources and must not be stripped.
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(),
                           parsed.path, parsed.query, ""))
    except ValueError:
        return None


def label(value):
    return " ".join(str(value or "").casefold().split())


def summarize_shared_urls(records):
    """Report every same-URL identity conflict, without altering source records.

    Names/TVG IDs and VLC program selectors are only *hints*. Different labels
    do not prove that distinct broadcasts are available on one stream.
    """
    by_url = defaultdict(list)
    count = 0
    for item in records:
        count += 1
        url = normalized_url(item.get("url"))
        if url:
            by_url[url].append(item)

    collisions = []
    metadata_conflicts = []
    multiplex_hints = []
    exact_repeats = 0
    for url, entries in by_url.items():
        distinct = {
            (label(e.get("name")), label(e.get("tvg_id")), e.get("program_number"))
            for e in entries
        }
        exact_repeats += len(entries) - len(distinct)
        if len(distinct) < 2:
            continue
        names = {label(e.get("name")) for e in entries if label(e.get("name"))}
        tvg_ids = {label(e.get("tvg_id")) for e in entries if label(e.get("tvg_id"))}
        programs = {e.get("program_number") for e in entries
                    if type(e.get("program_number")) is int}
        if len(programs) > 1:
            reason = "SAME_URL_MULTIPLE_PROGRAM_SELECTORS"
        elif len(names) > 1:
            reason = "SAME_URL_DIFFERENT_DISPLAY_NAMES"
        elif len(tvg_ids) > 1:
            reason = "SAME_NAME_CONFLICTING_TVG_IDS"
        else:
            reason = "SAME_URL_METADATA_VARIANTS"
        variants = sorted({
            (str(e.get("name") or ""), str(e.get("tvg_id") or ""),
             str(e.get("group") or ""), str(e.get("source") or ""),
             e.get("program_number"))
            for e in entries
        }, key=lambda x: tuple(str(v) for v in x))
        finding = {
            "url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "reason": reason,
            "record_count": len(entries),
            "channels": sorted({str(e.get("name") or "") for e in entries}),
            "tvg_ids": sorted({str(e.get("tvg_id") or "") for e in entries
                               if e.get("tvg_id")}),
            "groups": sorted({str(e.get("group") or "") for e in entries}),
            "sources": sorted({str(e.get("source") or "") for e in entries}),
            "program_selectors": sorted(programs),
            "variants": [
                {"name": name, "tvg_id": tvg, "group": group, "source": source,
                 "program_number": program}
                for name, tvg, group, source, program in variants
            ],
            "broadcast_identity_verified": False,
            "automatic_merge_or_delete_allowed": False,
        }
        if len(names) > 1:
            collisions.append(finding)
        else:
            metadata_conflicts.append(finding)
        if len(programs) > 1:
            multiplex_hints.append(finding["url_sha256"])

    return {
        "policy": "READ_ONLY_METADATA_REVIEW; same URL or different labels do not prove broadcast identity",
        "playlist_entries_examined": count,
        "distinct_urls": len(by_url),
        "same_identity_repeated_entries": exact_repeats,
        "cross_channel_url_collision_count": len(collisions),
        "cross_channel_url_collisions": collisions,
        "identity_metadata_conflict_count": len(metadata_conflicts),
        "identity_metadata_conflicts": metadata_conflicts,
        "multiple_program_selector_hint_count": len(multiplex_hints),
        "multiple_program_selector_url_hashes": sorted(multiplex_hints),
        "verified_distinct_broadcasts": 0,
        "playlist_modified": False,
    }
