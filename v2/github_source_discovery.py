#!/usr/bin/env python3
"""Read-only GitHub/Gist M3U source discovery; never change configured sources or live IBO."""
import datetime
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
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
    with opener.open(urllib.request.Request(url, headers=headers), timeout=18) as r:
        payload = r.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("GitHub API response too large")
    return json.loads(payload.decode("utf-8"))

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
    # Public Gists are not searchable through the repository search API.
    # Explicitly search public gist metadata through the GitHub Gist endpoint
    # only for owners already discovered in relevant repository results.
    gist_owners = sorted({name.split("/", 1)[0] for name in repos})[:30]
    for owner in gist_owners:
        if len(found) >= MAX_FILES:
            break
        try:
            gists = api("https://api.github.com/users/" + urllib.parse.quote(owner, safe="") + "/gists?per_page=30")
            if not isinstance(gists, list):
                continue
            for gist in gists:
                for filename, meta in gist.get("files", {}).items():
                    if len(found) >= MAX_FILES:
                        break
                    if not re.search(r"(?i)\\.(m3u8?|txt)$", filename):
                        continue
                    raw = meta.get("raw_url", "")
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
       "sources_found": len(found), "sources": found, "errors": errors}, ensure_ascii=False, indent=2) + "\n")
    print("Repositories:", len(repos), "parsed new sources:", len(found), "errors:", len(errors))
    if errors:
        raise SystemExit("GitHub/Gist source discovery incomplete; inspect sanitized report")

if __name__ == "__main__":
    main()
