#!/usr/bin/env python3
"""Read-only GitHub/Gist M3U source discovery; never change configured sources or live IBO."""
import datetime
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
import urllib.error
import time
from webpage_source_discovery import public_hostname
from discover import ROOT, entries, fetch

CONFIG = ROOT / "v2/config/sources.json"
OUT = ROOT / "v2/reports/github-source-discovery.json"
QUERIES = ["turkish iptv m3u", "turkiye m3u", "tr iptv playlist", "turkish tv playlist", "türkçe canlı tv m3u", "turk kanallari m3u", "turkish channels iptv", "iptv tr m3u8", "türk televizyon m3u", "turkish live tv playlist", "azerbaijan iptv m3u", "azerbaycan tv m3u", "azeri iptv playlist", "turk azeri iptv", "free turkish tv m3u", "turkish live channels m3u8", "türk iptv ücretsiz", "canlı tv izle m3u", "turkish diaspora iptv", "tr az channels playlist", "güneş tv canlı yayın m3u", "rec tv canlı yayın m3u", "gopik tv canlı yayın m3u", "azerbaycan türkçe canlı tv m3u", "turkish television germany m3u", "turkish tv netherlands m3u"]
MAX_REPOS = 320
MAX_FILES = 320
MAX_BYTES = 2_000_000

def api(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "api.github.com"
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("GitHub API must use trusted HTTPS host")
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            target = urllib.parse.urlsplit(newurl)
            if (target.scheme != "https" or target.hostname != "api.github.com"
                    or target.username or target.password
                    or target.port not in (None, 443)):
                raise ValueError("Unsafe GitHub API redirect")
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    headers = {"User-Agent": "MADSC55-TV-V2-Discovery/1.0", "Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(url, headers=headers)
    # Retry transient service failures only; credential/rate-budget exhaustion
    # and missing repositories remain visible as partial external coverage.
    for attempt in range(3):
        try:
            with opener.open(request, timeout=18) as r:
                payload = r.read(MAX_BYTES + 1)
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(min(2 ** attempt, 3))
    if len(payload) > MAX_BYTES:
        raise ValueError("GitHub API response too large")
    return json.loads(payload.decode("utf-8"))

def eligible_playlist_path(path):
    """Inspect M3U/M3U8 files and only playlist-named text exports.

    Arbitrary .txt files waste GitHub's public raw-file budget and cause
    avoidable fetch errors without adding plausible channel candidates.
    """
    if not isinstance(path, str) or path.startswith("/") or "\\" in path or ".." in path.split("/"):
        return False
    if re.search(r"(?i)\.m3u8?$", path):
        return True
    basename = path.rsplit("/", 1)[-1].casefold()
    return bool(basename.endswith(".txt") and
                re.search(r"iptv|m3u|playlist|channel|stream|kanal|turk|azer|^tv[._-]", basename))


def main():
    configured = {x["url"] for x in json.loads(CONFIG.read_text())["sources"]}
    repos, errors, found = {}, [], []
    limits_hit = []
    for query in QUERIES:
        try:
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": query, "per_page": 50, "sort": "updated"})
            page = api(url)
            if not isinstance(page, dict) or not isinstance(page.get("items"), list):
                raise ValueError("Invalid GitHub repository search response")
            if isinstance(page.get("total_count"), int) and page["total_count"] > len(page["items"]):
                limits_hit.append("GITHUB_SEARCH_FIRST_PAGE_LIMIT")
            for item in page["items"]:
                if not isinstance(item, dict) or item.get("fork") or item.get("archived"):
                    continue
                name, branch = item.get("full_name"), item.get("default_branch")
                if (isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name)
                        and isinstance(branch, str) and branch.strip()):
                    repos[name] = branch
        except Exception as exc:
            errors.append({"query": query, "error": type(exc).__name__})
    if len(repos) > MAX_REPOS:
        limits_hit.append("MAX_REPOS")
    for name, branch in sorted(repos.items(), key=lambda item: item[0].casefold())[:MAX_REPOS]:
        if len(found) >= MAX_FILES:
            limits_hit.append("MAX_FILES")
            break
        try:
            tree = api("https://api.github.com/repos/" + name + "/git/trees/" + urllib.parse.quote(branch, safe="") + "?recursive=1")
            if tree.get("truncated"):
                limits_hit.append("TRUNCATED_GITHUB_TREE")
            paths = [x["path"] for x in tree.get("tree", [])
                     if isinstance(x, dict) and x.get("type") == "blob"
                     and eligible_playlist_path(x.get("path"))]
            if len(paths) > 8:
                limits_hit.append("GITHUB_REPO_PLAYLIST_FILE_LIMIT")
            for path in sorted(paths, key=str.casefold)[:8]:
                if path.startswith("/") or ".." in path.split("/") or "\\" in path:
                    continue
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
    # Public Gists are not searchable through the repository search API.
    # Explicitly search public gist metadata through the GitHub Gist endpoint
    # only for owners already discovered in relevant repository results.
    all_gist_owners = sorted({name.split("/", 1)[0] for name in repos})
    if len(all_gist_owners) > 30:
        limits_hit.append("MAX_GIST_OWNERS")
    if len(found) >= MAX_FILES:
        limits_hit.append("MAX_FILES")
    gist_owners = all_gist_owners[:30]
    for owner in gist_owners:
        if len(found) >= MAX_FILES:
            break
        try:
            gists = api("https://api.github.com/users/" + urllib.parse.quote(owner, safe="") + "/gists?per_page=30")
            if not isinstance(gists, list):
                continue
            if len(gists) >= 30:
                limits_hit.append("GITHUB_GIST_FIRST_PAGE_LIMIT")
            for gist in gists:
                if not isinstance(gist, dict) or not isinstance(gist.get("files"), dict):
                    continue
                for filename, meta in gist["files"].items():
                    if not isinstance(filename, str) or not isinstance(meta, dict):
                        continue
                    if len(found) >= MAX_FILES:
                        break
                    if not re.search(r"(?i)\.(m3u8?|txt)$", filename):
                        continue
                    raw = meta.get("raw_url", "")
                    if not isinstance(raw, str):
                        continue
                    p = urllib.parse.urlsplit(raw)
                    if (p.scheme != "https" or p.hostname not in ("gist.githubusercontent.com", "raw.githubusercontent.com")
                            or p.username or p.password or p.port not in (None, 443)
                            or raw in configured):
                        continue
                    try:
                        content = fetch(raw)
                        sample = list(entries(content))
                        if sample:
                            found.append({"repository": owner + "/gist", "path": filename, "url": raw,
                                          "entries": len(sample), "tr_name_hints": 0,
                                          "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"})
                    except Exception as exc:
                        errors.append({"repository": owner + "/gist", "path": filename, "error": type(exc).__name__})
        except Exception as exc:
            errors.append({"repository": owner + "/gist", "error": type(exc).__name__})
    found.sort(key=lambda item: (item["repository"].casefold(), item["path"].casefold()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "policy": "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT", "repositories_discovered": len(repos),
       "sources_found": len(found), "sources": found, "errors": errors,
       "limits_hit": sorted(set(limits_hit)),
       "coverage_status": "PARTIAL_API_ERRORS" if errors else "PARTIAL_LIMITS" if limits_hit else "COMPLETE_QUERIES",
       "playback_verified": False}, ensure_ascii=False, indent=2) + "\n")
    print("Repositories:", len(repos), "parsed new sources:", len(found), "errors:", len(errors))
    if errors or limits_hit:
        print("WARNING: Partial GitHub/Gist discovery; inspect errors and limits in saved report")

if __name__ == "__main__":
    main()
