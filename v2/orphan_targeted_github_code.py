#!/usr/bin/env python3
"""Bounded, exact-metadata-oriented GitHub public code search for V2 orphan repair.

GitHub Code Search identifies source M3U files ONLY. The resulting pinned raw
files must still be parsed against the original immutable EXTINF metadata and
their candidate streams decoded/probed independently. Never return a stream URL.
"""
import hashlib
import json
import re
import urllib.error
from collections import Counter
from urllib.parse import quote, urlencode
import time

from stage3_historical_source_recovery import _read

MAX_QUERIES = 26  # Both M3U and M3U8 across up to 13 identities
MAX_REFERENCES = 80
PER_QUERY = 6
REPO_PATH = re.compile(
    r"https://github[.]com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/blob/"
    r"([0-9a-f]{40})/(.+)\Z")
SAFE_EPG = re.compile(r"[A-Za-z0-9_.-]{3,80}\Z")


def _channel_name(extinf):
    in_quote = False
    for i, char in enumerate(extinf):
        if char == '"':
            in_quote = not in_quote
        elif char == "," and not in_quote:
            return " ".join(extinf[i + 1:].split())
    return ""


def query_for_metadata(extinf, extension="m3u"):
    """A name may locate a source; it NEVER by itself validates the channel."""
    if extension not in ("m3u", "m3u8"):
        raise ValueError("Only M3U and M3U8 discovery extensions are accepted")
    if not isinstance(extinf, str) or not extinf.startswith("#EXTINF:"):
        return None
    found = re.search(r'\btvg-id="([^"]+)"', extinf, flags=re.I)
    channel_id = found.group(1).strip() if found else ""
    if SAFE_EPG.fullmatch(channel_id):
        return '"' + channel_id + '" extension:' + extension
    name = _channel_name(extinf)
    if not 4 <= len(name) <= 88:
        return None
    # Prevent arbitrary advanced search filters and URL/token-bearing queries.
    if any(ord(char) < 32 or char in '"\\' for char in name):
        return None
    if "://" in name or "=" in name or ":" in name:
        return None
    return '"' + name + '" extension:' + extension


def pinned_public_file(row):
    if not isinstance(row, dict):
        return None
    repo = row.get("repository")
    if not isinstance(repo, dict) or repo.get("private") is not False:
        return None
    html = row.get("html_url")
    path = row.get("path")
    if not isinstance(html, str) or not isinstance(path, str):
        return None
    found = REPO_PATH.fullmatch(html)
    if not found:
        return None
    owner, name, commit, html_path = found.groups()
    if repo.get("full_name", "").casefold() != (owner + "/" + name).casefold():
        return None
    if (len(path) > 512 or not path.casefold().endswith((".m3u", ".m3u8"))
            or html_path != path
            or any(piece in ("", ".", "..") for piece in path.split("/"))
            or any(ord(c) < 32 for c in path)):
        return None
    size = row.get("size")
    if type(size) is int and not 0 < size <= 6_000_000:
        return None
    return ("https://raw.githubusercontent.com/" + owner + "/" + name + "/"
            + commit + "/" + quote(path, safe="/"))


def targeted_source_references(orphan_rows, known_urls, *, fetcher=_read,
                               pause=time.sleep, max_queries=MAX_QUERIES):
    if (not isinstance(known_urls, set) or type(max_queries) is not int
            or not 1 <= max_queries <= MAX_QUERIES):
        raise ValueError("Invalid targeted source discovery budget")
    deduped = {}
    for row in orphan_rows:
        if not isinstance(row, dict):
            continue
        digest, extinf = row.get("extinf_sha256"), row.get("extinf")
        if not (isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest)
                and isinstance(extinf, str)
                and hashlib.sha256(extinf.encode("utf-8")).hexdigest() == digest):
            raise ValueError("Orphan identity is not exact immutable metadata")
        deduped[digest] = extinf
    queries = []
    seen_queries = set()
    for digest, extinf in sorted(deduped.items()):
        for extension in ("m3u", "m3u8"):
            query = query_for_metadata(extinf, extension=extension)
            if query is not None and query not in seen_queries:
                queries.append(query)
                seen_queries.add(query)
    selected = queries[:max_queries]
    skipped_count = max(0, len(queries) - len(selected))
    refs = []
    known = set(known_urls)
    errors = invalid = incomplete = 0
    error_categories = Counter()
    actual_queries = rate_limit_deferred = 0
    for index, query in enumerate(selected):
        # Authenticated GitHub Code Search has a separate rate limit.
        if index:
            pause(8)
        if index and index % 8 == 0:
            pause(65)
        uri = ("https://api.github.com/search/code?"
               + urlencode({"q": query, "per_page": PER_QUERY, "page": 1}))
        actual_queries += 1
        try:
            try:
                raw = fetcher(uri, api=True)
            except urllib.error.HTTPError as limit_error:
                if limit_error.code != 429:
                    raise
                # Honor GitHub's explicit Retry-After only when bounded.
                # No speculative rate-limit bypass or repeated hammering.
                headers = limit_error.headers or {}
                delay = headers.get("Retry-After", "")
                if not isinstance(delay, str) or not delay.isdecimal() or not 1 <= int(delay) <= 60:
                    raise
                pause(int(delay))
                raw = fetcher(uri, api=True)
            response = json.loads(raw)
            items = response.get("items") if isinstance(response, dict) else None
            if not isinstance(items, list) or len(items) > PER_QUERY:
                raise ValueError("GitHub code search response has no bounded results")
            if response.get("incomplete_results") is True:
                incomplete += 1
            for row in items:
                url = pinned_public_file(row)
                if not url or url in known:
                    invalid += 1
                    continue
                if len(refs) >= MAX_REFERENCES:
                    skipped_count += 1
                    continue
                hashed = hashlib.sha256(url.encode("utf-8")).hexdigest()
                refs.append({"id": "orphan-code-" + hashed[:24],
                             "url": url, "origin": "orphan-discovery-reference",
                             "scope": "candidate", "kind": "m3u"})
                known.add(url)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
            errors += 1
            # Log only fixed categories: HTTP error bodies and exception
            # strings may expose query metadata, source URLs or credentials.
            if isinstance(exc, urllib.error.HTTPError):
                bucket = "HTTP_" + str(exc.code) if exc.code in (
                    401, 403, 404, 422, 429, 500, 502, 503, 504) else "HTTP_OTHER"
            elif isinstance(exc, TimeoutError):
                bucket = "TIMEOUT"
            elif isinstance(exc, OSError):
                bucket = "NETWORK_OR_RATE_LIMIT"
            else:
                bucket = "INVALID_SEARCH_RESPONSE"
            error_categories[bucket] += 1
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
                # Explicitly defer remaining searches; an HTTP 429 says
                # NOTHING about whether any orphan stream currently exists.
                rate_limit_deferred = len(selected) - index - 1
                break
    status = ("NO_QUERYABLE_TARGETS" if not selected else
              "PARTIAL_PUBLIC_CODE_SEARCH" if errors or incomplete or skipped_count or rate_limit_deferred else
              "PUBLIC_CODE_REFERENCES_ONLY")
    return refs, {
        "schema": 1, "kind": "ORPHAN_EXACT_METADATA_PUBLIC_CODE_SEARCH",
        "status": status, "distinct_orphan_identities_supplied": len(deduped),
        "distinct_queries_available": len(queries),
        "queries_attempted": actual_queries, "queries_selected": len(selected),
        "queries_deferred_due_rate_limit": rate_limit_deferred,
        "query_budget": max_queries,
        "source_references_added": len(refs),
        "unavailable_or_failed_queries": errors,
        "anonymous_error_categories": dict(sorted(error_categories.items())),
        "incomplete_search_queries": incomplete,
        "truncated_queries_or_references": skipped_count,
        "invalid_or_duplicate_public_references": invalid,
        "pinned_public_git_commit_only": True,
        "source_reference_not_media_url": True,
        "playback_verified": False, "ibo_playlist_modified": False,
    }
