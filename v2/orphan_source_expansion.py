#!/usr/bin/env python3
"""Bounded public GitHub/Gist/GitLab/Codeberg source references for orphan-only repair.

Sources are NEVER automatically promoted to IPTV/IBO playlists. Each source
must later pass the protected downloader, full EXTINF metadata equality and
AV probe before its stream is counted as recovered.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from webpage_source_discovery import candidate_url

HERE = Path(__file__).resolve().parent
GITHUB_REPORT = HERE / "reports/github-source-discovery.json"
FORGE_REPORT = HERE / "reports/forge-source-discovery.json"
MAX_DISCOVERY = 80
MAX_REPORT_ROWS = 1500


def safe_reference_url(url):
    if not isinstance(url, str) or not 10 < len(url) <= 1400:
        return False
    try:
        u = urlsplit(url)
        if (u.scheme != "https" or u.username or u.password or u.fragment
                or u.port not in (None, 443)):
            return False
        host = u.hostname
        path = unquote(u.path)
        if (not host or "/../" in path or path.startswith("/../")
                or "\x00" in path or "/private/" in path.lower()):
            return False
        if host in ("raw.githubusercontent.com", "gist.githubusercontent.com"):
            return not u.query and candidate_url(url)
        if host == "codeberg.org":
            return not u.query and "/raw/branch/" in path and candidate_url(url)
        if host == "gitlab.com":
            params = parse_qs(u.query, keep_blank_values=True)
            return (u.path.startswith("/api/v4/projects/")
                    and "/repository/files/" in u.path and u.path.endswith("/raw")
                    and set(params) == {"ref"} and len(params["ref"]) == 1
                    and 0 < len(params["ref"][0]) <= 120)
    except (TypeError, ValueError):
        return False
    return False


def _load(path, field):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get(field)
    if not isinstance(data, dict) or not isinstance(rows, list) or len(rows) > MAX_REPORT_ROWS:
        raise ValueError("Invalid or oversized public source discovery report")
    return data, rows


def reviewed_source_references(known_urls, github_report=GITHUB_REPORT,
                               forge_report=FORGE_REPORT, limit=MAX_DISCOVERY):
    if not isinstance(known_urls, set) or not 1 <= limit <= MAX_DISCOVERY:
        raise ValueError("Unsafe source intake request")
    known = set(known_urls)
    result = []
    stats = {"schema": 1, "kind": "ORPHAN_ONLY_PUBLIC_SOURCE_HANDOFF",
             "github_gist_report_checked": False, "forge_report_checked": False,
             "new_source_references": 0, "source_reference_limit": limit,
             "skipped_invalid_or_duplicate": 0,
             "truncated": False, "playback_verified": False,
             "ibo_playlist_modified": False}
    for group, path in (("github_gist", github_report), ("forge", forge_report)):
        data, rows = _load(path, "sources")
        if group == "forge" and data.get("schema") != 1:
            raise ValueError("Invalid forge report schema")
        stats[group + "_report_checked"] = True
        for item in rows:
            if not isinstance(item, dict):
                stats["skipped_invalid_or_duplicate"] += 1
                continue
            url = item.get("url") if group == "github_gist" else item.get("source_url")
            approved_meta = (
                item.get("status") == "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"
                and isinstance(item.get("entries"), int) and item["entries"] > 0
                if group == "github_gist" else item.get("forge") in ("gitlab", "codeberg")
            )
            if not approved_meta or not safe_reference_url(url) or url in known:
                stats["skipped_invalid_or_duplicate"] += 1
                continue
            if len(result) >= limit:
                stats["truncated"] = True
                continue
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            result.append({"id": "orphan-ref-" + digest[:24], "url": url,
                           "scope": "candidate", "kind": "m3u",
                           "origin": "orphan-discovery-reference"})
            known.add(url)
    stats["new_source_references"] = len(result)
    return result, stats
