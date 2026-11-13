#!/usr/bin/env python3
"""Bounded read-only GitLab/Codeberg repository M3U discovery.

Only public repository metadata and public playlist files are read. Discovered
feeds remain candidates; this module never edits a playlist or verifies playback.
"""
import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from discover import ROOT, entries
from discovery_34 import QUERIES, fetch_json, search_url, _NoRedirect
from discovery_34_live_contract import provider_rate_limited, retry_delay

MAX_PROJECTS = 60
MAX_FILES = 160
MAX_FILE_BYTES = 2_000_000
MAX_ATTEMPTS = 3
FEDERATED_QUERIES = tuple(dict.fromkeys(QUERIES + (
    "iptv", "m3u", "m3u8", "playlist", "live tv", "television",
)))
UA = "MADSC55-TV-V2-Discovery/1.0"


def _request_json(url, provider, fetch_json_fn=fetch_json, sleep_fn=None):
    import time
    sleep_fn = sleep_fn or time.sleep
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch_json_fn(url), None
        except urllib.error.HTTPError as exc:
            row = {
                "http_status": exc.code,
                "http_reason": str(getattr(exc, "reason", "")),
                "rate_limit_remaining": (exc.headers.get("X-RateLimit-Remaining")
                                         or exc.headers.get("x-ratelimit-remaining"))
                                        if exc.headers else None,
            }
            if exc.code == 429 and attempt < MAX_ATTEMPTS:
                sleep_fn(retry_delay(exc, attempt))
                continue
            if provider_rate_limited(row):
                return None, "RATE_LIMITED"
            return None, "HTTP_" + str(exc.code)
        except (OSError, TimeoutError, ValueError, TypeError) as exc:
            return None, type(exc).__name__
    return None, "RETRY_EXHAUSTED"


def _raw_fetch(url, expected_host):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != expected_host or parsed.username or parsed.password:
        raise ValueError("Unsafe raw source URL")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.build_opener(_NoRedirect).open(req, timeout=18) as response:
        if urllib.parse.urlsplit(response.url).hostname != expected_host:
            raise ValueError("Cross-host raw redirect refused")
        data = response.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Playlist file too large")
    return data.decode("utf-8-sig", errors="replace")


def _project_items(provider, payload):
    """Reject HTTP 200 API error objects instead of treating them as zero results."""
    if provider == "gitlab":
        if not isinstance(payload, list):
            raise ValueError("Invalid GitLab project search response")
        return payload
    if provider == "codeberg":
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("Invalid Codeberg project search response")
        return payload["data"]
    raise ValueError("Unsupported provider")


def _project_identity(provider, item):
    if provider == "gitlab":
        project_id = item.get("id")
        namespace = item.get("path_with_namespace")
        branch = item.get("default_branch") or "main"
        if project_id is None or not isinstance(namespace, str) or "/" not in namespace:
            return None
        return str(project_id), namespace, branch
    full_name = item.get("full_name")
    owner = item.get("owner")
    if not isinstance(full_name, str) and isinstance(owner, dict):
        login = owner.get("login")
        name = item.get("name")
        if isinstance(login, str) and isinstance(name, str):
            full_name = login + "/" + name
    branch = item.get("default_branch") or "main"
    if not isinstance(full_name, str) or "/" not in full_name:
        return None
    return full_name, full_name, branch


def _tree_url(provider, key, namespace, branch):
    ref = urllib.parse.quote(branch, safe="")
    if provider == "gitlab":
        return ("https://gitlab.com/api/v4/projects/" + urllib.parse.quote(key, safe="")
                + "/repository/tree?recursive=true&per_page=100&ref=" + ref)
    owner, name = namespace.split("/", 1)
    return ("https://codeberg.org/api/v1/repos/" + urllib.parse.quote(owner, safe="")
            + "/" + urllib.parse.quote(name, safe="") + "/git/trees/" + ref + "?recursive=true")


def _tree_paths(provider, payload):
    """A 200 API error body is not an empty repository tree."""
    if provider == "gitlab":
        if not isinstance(payload, list):
            raise ValueError("Invalid GitLab repository tree response")
        rows = payload
    elif provider == "codeberg":
        if not isinstance(payload, dict) or not isinstance(payload.get("tree"), list):
            raise ValueError("Invalid Codeberg repository tree response")
        rows = payload["tree"]
    else:
        raise ValueError("Unsupported provider")
    return sorted({row.get("path") for row in rows
                   if isinstance(row, dict) and row.get("type") in ("blob", "file")
                   and isinstance(row.get("path"), str)
                   and re.search(r"(?i)\.(m3u8?|txt)$", row["path"])},
                  key=str.casefold)


def _raw_url(provider, namespace, branch, path):
    b = urllib.parse.quote(branch, safe="")
    p = urllib.parse.quote(path, safe="/")
    if provider == "gitlab":
        return "https://gitlab.com/" + urllib.parse.quote(namespace, safe="/") + "/-/raw/" + b + "/" + p
    owner, name = namespace.split("/", 1)
    return ("https://codeberg.org/" + urllib.parse.quote(owner, safe="") + "/"
            + urllib.parse.quote(name, safe="") + "/raw/branch/" + b + "/" + p)


def discover_provider(provider, fetch_json_fn=fetch_json, fetch_text_fn=_raw_fetch,
                      sleep_fn=None, queries=FEDERATED_QUERIES, configured_urls=None):
    if provider not in ("gitlab", "codeberg"):
        raise ValueError("provider must be gitlab or codeberg")
    configured = set(configured_urls or ())
    projects, sources, errors, query_results = {}, [], [], []
    rate_limited = False
    for index, query in enumerate(queries):
        payload, error = _request_json(search_url(provider, query), provider,
                                      fetch_json_fn=fetch_json_fn, sleep_fn=sleep_fn)
        if error:
            query_results.append({"query": query, "status": "error", "reason": error})
            if error == "RATE_LIMITED":
                rate_limited = True
                query_results.extend({"query": skipped, "status": "skipped",
                                      "reason": "provider_rate_limit_circuit_open"}
                                     for skipped in queries[index + 1:])
                break
            continue
        try:
            rows = _project_items(provider, payload)
        except (ValueError, TypeError):
            query_results.append({"query": query, "status": "error", "reason": "InvalidResponse"})
            continue
        query_results.append({"query": query, "status": "ok", "projects": len(rows)})
        for item in rows:
            if not isinstance(item, dict):
                continue
            identity = _project_identity(provider, item)
            if identity:
                key, namespace, branch = identity
                projects[key] = (namespace, branch)
        if len(projects) >= MAX_PROJECTS:
            query_results.extend({"query": skipped, "status": "skipped",
                                  "reason": "project_limit_reached"}
                                 for skipped in queries[index + 1:])
            break

    for key, (namespace, branch) in list(sorted(projects.items(), key=lambda pair: pair[0].casefold()))[:MAX_PROJECTS]:
        tree_payload, error = _request_json(_tree_url(provider, key, namespace, branch),
                                            provider, fetch_json_fn=fetch_json_fn,
                                            sleep_fn=sleep_fn)
        if error:
            errors.append({"project": namespace, "error": error})
            if error == "RATE_LIMITED":
                rate_limited = True
                break
            continue
        try:
            paths = _tree_paths(provider, tree_payload)[:8]
        except (ValueError, TypeError):
            errors.append({"project": namespace, "error": "InvalidTreeResponse"})
            continue
        for path in paths:
            if len(sources) >= MAX_FILES:
                break
            raw = _raw_url(provider, namespace, branch, path)
            if raw in configured:
                continue
            try:
                content = fetch_text_fn(raw, provider + (".com" if provider == "gitlab" else ".org"))
                sample = list(entries(content))
                if not sample:
                    continue
                configured.add(raw)
                sources.append({
                    "repository": namespace, "path": path, "url": raw,
                    "entries": len(sample),
                    "tr_name_hints": sum(bool(re.search(
                        r"(?i)\b(trt|türk|turk|kanal|haber)\b", row["name"]))
                        for row in sample),
                    "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED",
                })
            except urllib.error.HTTPError as exc:
                reason = "HTTP_" + str(exc.code)
                errors.append({"project": namespace, "path": path, "error": reason})
                if provider_rate_limited({
                    "http_status": exc.code,
                    "http_reason": str(getattr(exc, "reason", "")),
                    "rate_limit_remaining": (exc.headers.get("X-RateLimit-Remaining")
                                             or exc.headers.get("x-ratelimit-remaining"))
                                            if exc.headers else None,
                }):
                    rate_limited = True
                    break
            except (OSError, ValueError, TypeError) as exc:
                errors.append({"project": namespace, "path": path,
                               "error": type(exc).__name__})
        if rate_limited or len(sources) >= MAX_FILES:
            break

    checked = sum(row["status"] in ("ok", "error") for row in query_results)
    skipped = sum(row["status"] == "skipped" for row in query_results)
    failed = sum(row["status"] == "error" for row in query_results)
    return {
        "provider": provider,
        "status": "error" if errors or rate_limited or any(x["status"] == "error" for x in query_results) else "ok",
        "queries_total": len(queries),
        "queries_checked": checked,
        "queries_skipped": skipped,
        "queries_failed": failed,
        "rate_limited": rate_limited,
        "projects_discovered": len(projects),
        "sources_found": len(sources),
        "sources": sources,
        "query_results": query_results,
        "errors": errors,
    }


def main():
    configured = set()
    config = ROOT / "v2/config/sources.json"
    try:
        configured = {row["url"] for row in json.loads(config.read_text(encoding="utf-8"))["sources"]
                      if isinstance(row, dict) and isinstance(row.get("url"), str)}
    except (OSError, ValueError, TypeError, KeyError):
        pass
    for provider in ("gitlab", "codeberg"):
        result = discover_provider(provider, configured_urls=configured)
        path = ROOT / "v2/reports" / (provider + "-m3u-source-discovery.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "policy": "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT",
            **result,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        configured.update(row["url"] for row in result["sources"])
        print(provider, "projects:", result["projects_discovered"],
              "M3U sources:", result["sources_found"], "status:", result["status"])


if __name__ == "__main__":
    main()
