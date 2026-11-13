#!/usr/bin/env python3
"""Read-only GitHub/Gist M3U source discovery; never change configured sources or live IBO."""
import datetime
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
from discover import ROOT, entries, fetch

CONFIG = ROOT / "v2/config/sources.json"
OUT = ROOT / "v2/reports/github-source-discovery.json"
QUERIES = ["turkish iptv m3u", "turkiye m3u", "tr iptv playlist", "turkish tv playlist", "türkçe canlı tv m3u", "turk kanallari m3u", "turkish channels iptv", "iptv tr m3u8", "türk televizyon m3u", "turkish live tv playlist", "azerbaijan iptv m3u", "azerbaycan tv m3u", "azeri iptv playlist", "turk azeri iptv", "free turkish tv m3u", "turkish live channels m3u8", "türk iptv ücretsiz", "canlı tv izle m3u", "turkish diaspora iptv", "tr az channels playlist", "güneş tv canlı yayın m3u", "rec tv canlı yayın m3u", "gopik tv canlı yayın m3u", "azerbaycan türkçe canlı tv m3u", "turkish television germany m3u", "turkish tv netherlands m3u"]
MAX_REPOS = 320
MAX_FILES = 320
MAX_BYTES = 2_000_000
MAX_GIST_PAGES = 10
GIST_PAGE_SIZE = 20
MAX_GIST_SOURCES = 200

def api(url):
    headers = {"User-Agent": "MADSC55-TV-V2-Discovery/1.0", "Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=18) as r:
        return json.loads(r.read(MAX_BYTES).decode("utf-8"))


def discover_gists(api_fn=api, fetch_fn=fetch, configured_urls=None):
    """Inspect a bounded recent window of public Gists for parseable M3U/M3U8 files."""
    seen = set(configured_urls or ())
    found, errors = [], []
    checked = 0
    for page in range(1, MAX_GIST_PAGES + 1):
        endpoint = ("https://api.github.com/gists/public?" +
                    urllib.parse.urlencode({"per_page": GIST_PAGE_SIZE, "page": page}))
        try:
            payload = api_fn(endpoint)
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
                        sample = list(entries(fetch_fn(raw)))
                        if not sample:
                            continue
                        found.append({
                            "repository": "gist:" + gist_id,
                            "path": filename,
                            "url": raw,
                            "entries": len(sample),
                            "tr_name_hints": sum(bool(re.search(
                                r"(?i)\\b(trt|türk|turk|kanal|haber)\\b", row["name"]))
                                for row in sample),
                            "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED",
                        })
                    except Exception as exc:
                        errors.append({"gist": gist_id, "file": filename,
                                       "error": type(exc).__name__})
        except Exception as exc:
            errors.append({"gist_page": page, "error": type(exc).__name__})
            break
    return found, errors, checked


def main():
    configured = {x["url"] for x in json.loads(CONFIG.read_text())["sources"]}
    repos, errors, found = {}, [], []
    for query in QUERIES:
        try:
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": query, "per_page": 50, "sort": "updated"})
            for item in api(url).get("items", []):
                if not item.get("fork") and not item.get("archived"):
                    repos[item["full_name"]] = item.get("default_branch", "main")
        except Exception as exc:
            errors.append({"query": query, "error": type(exc).__name__})
    for name, branch in sorted(repos.items(), key=lambda item: item[0].casefold())[:MAX_REPOS]:
        if len(found) >= MAX_FILES:
            break
        try:
            tree = api("https://api.github.com/repos/" + name + "/git/trees/" + urllib.parse.quote(branch, safe="") + "?recursive=1")
            paths = [x["path"] for x in tree.get("tree", []) if x.get("type") == "blob" and re.search(r"(?i)\.(m3u8?|txt)$", x.get("path", ""))]
            for path in sorted(paths, key=str.casefold)[:8]:
                if len(found) >= MAX_FILES:
                    break
                raw = "https://raw.githubusercontent.com/" + name + "/" + urllib.parse.quote(branch, safe="") + "/" + urllib.parse.quote(path, safe="/")
                if raw in configured:
                    continue
                try:
                    content = fetch(raw)
                    sample = list(entries(content))
                    if not sample:
                        continue
                    found.append({"repository": name, "path": path, "url": raw, "entries": len(sample),
                                  "tr_name_hints": sum(bool(re.search(r"(?i)\b(trt|türk|turk|kanal|haber)\b", x["name"])) for x in sample),
                                  "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"})
                except Exception as exc:
                    errors.append({"repository": name, "path": path, "error": type(exc).__name__})
        except Exception as exc:
            errors.append({"repository": name, "error": type(exc).__name__})
    gist_sources, gist_errors, gists_checked = discover_gists(
        api_fn=api, fetch_fn=fetch, configured_urls=configured)
    found.extend(gist_sources)
    errors.extend(gist_errors)
    found.sort(key=lambda item: (item["repository"].casefold(), item["path"].casefold()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "policy": "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT", "repositories_discovered": len(repos),
       "gists_checked": gists_checked, "gist_sources_found": len(gist_sources),
       "sources_found": len(found), "sources": found, "errors": errors}, ensure_ascii=False, indent=2) + "\\n")
    print("Repositories:", len(repos), "parsed new sources:", len(found), "errors:", len(errors))

if __name__ == "__main__":
    main()
