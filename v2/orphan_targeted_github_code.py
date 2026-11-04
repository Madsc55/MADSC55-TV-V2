#!/usr/bin/env python3
"""Bounded, exact-metadata-oriented GitHub public code search for V2 orphan repair.

GitHub Code Search identifies source M3U files ONLY. The resulting pinned raw
files must still be parsed against the original immutable EXTINF metadata and
their candidate streams decoded/probed independently. Never return a stream URL.
"""
import hashlib
import json
import re
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
    for index, query in enumerate(selected):
        # Authenticated GitHub Code Search has a separate rate limit.
        if index:
            pause(8)
        if index and index % 8 == 0:
            pause(65)
        uri = ("https://api.github.com/search/code?"
               + urlencode({"q": query, "per_page": PER_QUERY, "page": 1}))
        try:
            response = json.loads(fetcher(uri, api=True))
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
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            errors += 1
    status = ("NO_QUERYABLE_TARGETS" if not selected else
              "PARTIAL_PUBLIC_CODE_SEARCH" if errors or incomplete or skipped_count else
              "PUBLIC_CODE_REFERENCES_ONLY")
    return refs, {
        "schema": 1, "kind": "ORPHAN_EXACT_METADATA_PUBLIC_CODE_SEARCH",
        "status": status, "distinct_orphan_identities_supplied": len(deduped),
        "distinct_queries_available": len(queries),
        "queries_attempted": len(selected), "query_budget": max_queries,
        "source_references_added": len(refs),
        "unavailable_or_failed_queries": errors,
        "incomplete_search_queries": incomplete,
        "truncated_queries_or_references": skipped_count,
        "invalid_or_duplicate_public_references": invalid,
        "pinned_public_git_commit_only": True,
        "source_reference_not_media_url": True,
        "playback_verified": False, "ibo_playlist_modified": False,
    }
