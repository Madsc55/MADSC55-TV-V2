#!/usr/bin/env python3
"""Read-only GitHub/Gist M3U source discovery; never change configured sources or live IBO."""
import datetime
import json
import re
import urllib.error
import urllib.parse
from discover import ROOT, entries, fetch
from discovery_34 import (
    fetch_json as api, fetch_with_retry, incomplete_repository_response, repository_items,
)
from discovery_provider_requests import REQUEST_ERRORS, http_error_details, provider_rate_limited

CONFIG = ROOT / "v2/config/sources.json"
OUT = ROOT / "v2/reports/github-source-discovery.json"
QUERIES = ["turkish iptv m3u", "turkiye m3u", "tr iptv playlist", "turkish tv playlist", "türkçe canlı tv m3u", "turk kanallari m3u", "turkish channels iptv", "iptv tr m3u8", "türk televizyon m3u", "turkish live tv playlist", "azerbaijan iptv m3u", "azerbaycan tv m3u", "azeri iptv playlist", "turk azeri iptv", "free turkish tv m3u", "turkish live channels m3u8", "türk iptv ücretsiz", "canlı tv izle m3u", "turkish diaspora iptv", "tr az channels playlist", "güneş tv canlı yayın m3u", "rec tv canlı yayın m3u", "gopik tv canlı yayın m3u", "azerbaycan türkçe canlı tv m3u", "turkish television germany m3u", "turkish tv netherlands m3u"]
MAX_REPOS = 320
MAX_FILES = 320
MAX_GIST_PAGES = 10
GIST_PAGE_SIZE = 20
MAX_GIST_SOURCES = 200

def _request_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        if provider_rate_limited(http_error_details(exc)):
            return "RATE_LIMITED"
        return "HTTP_" + str(exc.code)
    return type(exc).__name__


def discover_gists(api_fn=api, fetch_fn=fetch, configured_urls=None):
    """Inspect a bounded recent window of public Gists for parseable M3U/M3U8 files."""
    seen = set(configured_urls or ())
    found, errors = [], []
    checked = 0
    for page in range(1, MAX_GIST_PAGES + 1):
        endpoint = ("https://api.github.com/gists/public?" +
                    urllib.parse.urlencode({"per_page": GIST_PAGE_SIZE, "page": page}))
        try:
            payload = fetch_with_retry(endpoint, fetch=api_fn)
            if not isinstance(payload, list):
                raise ValueError("Invalid public Gist response")
            if not payload:
                break
            for gist in payload:
                checked += 1
                if not isinstance(gist, dict):
                    continue
                gist_id = gist.get("id")
                files = gist.get("files")
                if not isinstance(gist_id, str) or not isinstance(files, dict):
                    continue
                for filename, item in files.items():
                    if len(found) >= MAX_GIST_SOURCES:
                        return found, errors, checked
                    if not isinstance(filename, str) or not filename.lower().endswith((".m3u", ".m3u8", ".txt")):
                        continue
                    if not isinstance(item, dict):
                        continue
                    raw = item.get("raw_url")
                    parsed = urllib.parse.urlsplit(raw) if isinstance(raw, str) else None
                    if (parsed is None or parsed.scheme != "https"
                            or parsed.hostname != "gist.githubusercontent.com"
                            or parsed.username or parsed.password or raw in seen):
                        continue
                    seen.add(raw)
                    try:
                        sample = list(entries(fetch_with_retry(raw, fetch=fetch_fn)))
                        if not sample:
                            continue
                        found.append({
                            "repository": "gist:" + gist_id,
                            "path": filename,
                            "url": raw,
                            "entries": len(sample),
                            "tr_name_hints": sum(bool(re.search(
                                r"(?i)\b(trt|türk|turk|kanal|haber)\b", row["name"]))
                                for row in sample),
                            "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED",
                        })
                    except REQUEST_ERRORS as exc:
                        reason = _request_error(exc)
                        errors.append({"gist": gist_id, "file": filename, "error": reason})
                        if reason == "RATE_LIMITED":
                            return found, errors, checked
        except REQUEST_ERRORS as exc:
            errors.append({"gist_page": page, "error": _request_error(exc)})
            break
    return found, errors, checked


def main():
    if OUT.exists() or OUT.is_symlink():
        raise SystemExit("GitHub discovery report already exists")
    configured = {x["url"] for x in json.loads(CONFIG.read_text())["sources"]}
    repos, errors, found = {}, [], []
    rate_limited = False
    for index, query in enumerate(QUERIES):
        try:
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": query, "per_page": 50, "sort": "updated"})
            payload = fetch_with_retry(url, fetch=api)
            items = repository_items("github", payload)
            if incomplete_repository_response("github", payload):
                errors.append({"query": query, "error": "incomplete_repository_response"})
            for item in items:
                if not isinstance(item, dict) or item.get("fork") or item.get("archived"):
                    continue
                name, branch = item.get("full_name"), item.get("default_branch") or "main"
                if (isinstance(name, str) and re.fullmatch(r"[\w.-]+/[\w.-]+", name)
                        and not any(part in (".", "..") for part in name.split("/"))
                        and isinstance(branch, str)):
                    repos[name] = branch
        except REQUEST_ERRORS as exc:
            reason = _request_error(exc)
            errors.append({"query": query, "error": reason})
            if reason == "RATE_LIMITED":
                rate_limited = True
                errors.extend({"query": skipped, "error": "provider_rate_limit_skipped"}
                              for skipped in QUERIES[index + 1:])
                break
    for name, branch in sorted(repos.items(), key=lambda item: item[0].casefold())[:MAX_REPOS]:
        if rate_limited or len(found) >= MAX_FILES:
            break
        try:
            endpoint = "https://api.github.com/repos/" + name + "/git/trees/" + urllib.parse.quote(branch, safe="") + "?recursive=1"
            tree = fetch_with_retry(endpoint, fetch=api)
            if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
                raise ValueError("Invalid GitHub tree response")
            if tree.get("truncated") is True:
                errors.append({"repository": name, "error": "incomplete_tree_response"})
            paths = [row["path"] for row in tree["tree"] if isinstance(row, dict)
                     and row.get("type") == "blob" and isinstance(row.get("path"), str)
                     and re.search(r"(?i)\.(m3u8?|txt)$", row["path"])]
            for path in sorted(paths, key=str.casefold)[:8]:
                if len(found) >= MAX_FILES:
                    break
                raw = "https://raw.githubusercontent.com/" + name + "/" + urllib.parse.quote(branch, safe="") + "/" + urllib.parse.quote(path, safe="/")
                if raw in configured:
                    continue
                try:
                    content = fetch_with_retry(raw, fetch=fetch)
                    sample = list(entries(content))
                    if not sample:
                        continue
                    found.append({"repository": name, "path": path, "url": raw, "entries": len(sample),
                                  "tr_name_hints": sum(bool(re.search(r"(?i)\b(trt|türk|turk|kanal|haber)\b", x["name"])) for x in sample),
                                  "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"})
                except REQUEST_ERRORS as exc:
                    reason = _request_error(exc)
                    errors.append({"repository": name, "path": path, "error": reason})
                    if reason == "RATE_LIMITED":
                        rate_limited = True
                        break
        except REQUEST_ERRORS as exc:
            reason = _request_error(exc)
            errors.append({"repository": name, "error": reason})
            rate_limited = reason == "RATE_LIMITED"
    gist_sources, gist_errors, gists_checked = [], [], 0
    if not rate_limited:
        gist_sources, gist_errors, gists_checked = discover_gists(
            api_fn=api, fetch_fn=fetch, configured_urls=configured)
    found.extend(gist_sources)
    errors.extend(gist_errors)
    found.sort(key=lambda item: (item["repository"].casefold(), item["path"].casefold()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "policy": "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT",
        "repositories_discovered": len(repos),
        "gists_checked": gists_checked, "gist_sources_found": len(gist_sources),
        "status": "error" if errors else "ok", "sources_found": len(found),
        "sources": found, "errors": errors,
    }
    with OUT.open("x", encoding="utf-8") as output:
        output.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Repositories:", len(repos), "parsed new sources:", len(found), "errors:", len(errors))
    if errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
