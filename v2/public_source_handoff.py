#!/usr/bin/env python3
"""V2 source-reference handoff to read-only public candidate discovery.

Unapproved GitHub/Gist and GitLab/Codeberg M3U references may be inspected in
a bounded explicit scan, NOT automatically accepted for playback or publishing.
Only approved public website origins can create optional M3U index scans.
"""
import hashlib
import json
from pathlib import Path
import re

from orphan_source_expansion import safe_reference_url
from run_live_page_discovery import approved_page

MAX_PER_PROVIDER = 24
MAX_LIVE_PAGES = 100
PUBLIC_SOURCE_STATUS = "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def staged_references(github_report, forge_report, existing_urls,
                      max_per_provider=MAX_PER_PROVIDER):
    """Return immutable provenance plus URLs for bounded validation and parsing.

    The source documents still must pass public DNS, M3U pair parsing, and
    candidate-level verification by the calling read-only scan.
    """
    if type(max_per_provider) is not int or not 1 <= max_per_provider <= MAX_PER_PROVIDER:
        raise ValueError("Invalid public source inspection limit")
    if not isinstance(existing_urls, set):
        raise ValueError("Existing source URLs must be a set")
    seen = set(existing_urls)
    report = {"schema": 1, "kind": "V2_PUBLIC_SOURCE_REFERENCE_HANDOFF",
              "report_checked": {}, "accepted_for_inspection": {},
              "skipped_unreviewed_or_duplicate": {}, "bounded_truncation": {},
              "playback_verified": False, "ibo_playlist_modified": False}
    selected = []
    for origin, report_path in (("github_gist", github_report),
                                ("gitlab_codeberg", forge_report)):
        try:
            data = json.loads(Path(report_path).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError("Missing or corrupted public source discovery: " + origin) from exc
        if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
            raise ValueError("Malformed public source discovery: " + origin)
        if len(data["sources"]) > 2000:
            raise ValueError("Oversized public source discovery: " + origin)
        if origin == "github_gist":
            if (data.get("policy") != "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT"
                    or data.get("sources_found") != len(data["sources"])):
                raise ValueError("Invalid GitHub/Gist source report provenance")
        elif (data.get("schema") != 1 or data.get("status") != "source_references_only"
              or data.get("source_count") != len(data["sources"])):
            raise ValueError("Invalid GitLab/Codeberg source report provenance")
        report["report_checked"][origin] = True
        good = rejected = truncated = 0
        for row in data["sources"]:
            if not isinstance(row, dict):
                rejected += 1
                continue
            if origin == "github_gist":
                url = row.get("url")
                allowed = (row.get("status") == PUBLIC_SOURCE_STATUS
                           and type(row.get("entries")) is int and row["entries"] > 0)
            else:
                url = row.get("source_url")
                allowed = row.get("forge") in ("gitlab", "codeberg")
            if not allowed or not safe_reference_url(url) or url in seen:
                rejected += 1
                continue
            if good >= max_per_provider:
                truncated += 1
                continue
            seen.add(url)
            digest = _digest(url)
            selected.append({"id": "publicref-" + digest[:24],
                             "kind": "m3u", "scope": "candidate", "url": url,
                             "origin": "reviewed-public-source-reference",
                             "discovery_family": origin})
            good += 1
        report["accepted_for_inspection"][origin] = good
        report["skipped_unreviewed_or_duplicate"][origin] = rejected
        report["bounded_truncation"][origin] = truncated
    return selected, report


def approved_live_index_sources(live_pages_json, existing_urls):
    """Actual live-page HTML is inspected only after approved origin checks."""
    data = json.loads(Path(live_pages_json).read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema") != 1
            or data.get("policy") !=
            "explicitly reviewed public HTTPS origins only; no inferred playback"
            or not isinstance(data.get("pages"), list)
            or len(data["pages"]) > MAX_LIVE_PAGES):
        raise ValueError("Invalid approved live site inventory")
    known = set(existing_urls)
    rows = []
    ids = set()
    for item in data["pages"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid approved live page")
        ident, url = item.get("id"), item.get("url")
        if (not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9-]{3,90}", ident)
                or not approved_page(url) or ident in ids):
            raise ValueError("Unsafe or duplicate live page")
        ids.add(ident)
        if url not in known:
            rows.append({"id": "live-index-" + ident, "url": url,
                         "kind": "html", "scope": "candidate",
                         "origin": "approved-live-page-index"})
            known.add(url)
    return rows, {"schema": 1, "kind": "V2_APPROVED_LIVE_PAGE_M3U_INSPECTION",
                  "pages_configured": len(data["pages"]),
                  "new_pages_queued": len(rows),
                  "channel_streams_inferred": 0, "playback_verified": False}
