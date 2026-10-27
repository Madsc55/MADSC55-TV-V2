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
QUERIES = ["turkish iptv m3u", "turkiye m3u", "tr iptv playlist", "turkish tv playlist"]
MAX_REPOS = 50
MAX_FILES = 80
MAX_BYTES = 2_000_000

def api(url):
    headers = {"User-Agent": "MADSC55-TV-V2-Discovery/1.0", "Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=18) as r:
        return json.loads(r.read(MAX_BYTES).decode("utf-8"))

def main():
    configured = {x["url"] for x in json.loads(CONFIG.read_text())["sources"]}
    repos, errors, found = {}, [], []
    for query in QUERIES:
        try:
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": query, "per_page": 20, "sort": "updated"})
            for item in api(url).get("items", []):
                if not item.get("fork") and not item.get("archived"):
                    repos[item["full_name"]] = item.get("default_branch", "main")
        except Exception as exc:
            errors.append({"query": query, "error": type(exc).__name__})
    for name, branch in list(repos.items())[:MAX_REPOS]:
        if len(found) >= MAX_FILES:
            break
        try:
            tree = api("https://api.github.com/repos/" + name + "/git/trees/" + urllib.parse.quote(branch, safe="") + "?recursive=1")
            paths = [x["path"] for x in tree.get("tree", []) if x.get("type") == "blob" and re.search(r"(?i)\\.(m3u8?|txt)$", x.get("path", ""))]
            for path in paths[:4]:
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
                                  "tr_name_hints": sum(bool(re.search(r"(?i)\\b(trt|türk|turk|kanal|haber)\\b", x["name"])) for x in sample),
                                  "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED"})
                except Exception as exc:
                    errors.append({"repository": name, "path": path, "error": type(exc).__name__})
        except Exception as exc:
            errors.append({"repository": name, "error": type(exc).__name__})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "policy": "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT", "repositories_discovered": len(repos),
       "sources_found": len(found), "sources": found, "errors": errors}, ensure_ascii=False, indent=2) + "\n")
    print("Repositories:", len(repos), "parsed new sources:", len(found), "errors:", len(errors))

if __name__ == "__main__":
    main()
