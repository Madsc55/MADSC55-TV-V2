#!/usr/bin/env python3
"""Opt-in, bounded public GitLab/Codeberg source discovery.

Writes only M3U source references to a separate report. Does not fetch stream
URLs, alter the live playlist or automatically promote unknown sources.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode, quote, urlsplit
from webpage_source_discovery import public_hostname
import urllib.request
from forge_source_discovery import (GITLAB_API, CODEBERG_API, TERMS,
    gitlab_projects, codeberg_projects, parse_tree_paths, playlist_sources)

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "reports" / "forge-source-discovery.json"

def api_json(url):
    p = urlsplit(url)
    if (p.scheme != "https" or not p.hostname or not public_hostname(p.hostname)
            or p.hostname not in ("gitlab.com", "codeberg.org")
            or p.username or p.password or p.port not in (None, 443)):
        raise ValueError("Untrusted forge API host")
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            target = urlsplit(newurl)
            if (target.scheme != "https" or target.hostname != p.hostname
                    or target.username or target.password
                    or target.port not in (None, 443)):
                raise ValueError("Unsafe forge API redirect")
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-Discovery/1.0",
                                                    "Accept": "application/json"})
    with opener.open(request, timeout=12) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("Forge response too large")
    return json.loads(payload)

def scan():
    found, errors, seen = [], [], set()
    for term in TERMS:
        queries = [
            ("gitlab", GITLAB_API + "?" + urlencode({"search": term, "simple": "true", "per_page": 12})),
            ("codeberg", CODEBERG_API + "?" + urlencode({"q": term, "limit": 12})),
        ]
        for forge, url in queries:
            try:
                payload = api_json(url)
                projects = gitlab_projects(payload) if forge == "gitlab" else codeberg_projects(payload)
            except (ValueError, OSError, TimeoutError) as exc:
                errors.append({"forge": forge, "term": term, "error": type(exc).__name__})
                continue
            for project in projects:
                identity = json.dumps(project, sort_keys=True)
                if identity in seen:
                    continue
                seen.add(identity)
                if forge == "gitlab":
                    tree = (GITLAB_API + "/" + str(project["id"]) + "/repository/tree?"
                            + urlencode({"ref": project["branch"], "recursive": "true", "per_page": 100}))
                else:
                    tree = ("https://codeberg.org/api/v1/repos/"
                            + quote(project["owner"], safe="") + "/"
                            + quote(project["name"], safe="") + "/git/trees/"
                            + quote(project["branch"], safe="") + "?recursive=true")
                try:
                    listing = api_json(tree)
                    if forge == "codeberg" and isinstance(listing, dict):
                        listing = listing.get("tree", [])
                    paths = parse_tree_paths(listing)
                    for link in playlist_sources(project, paths):
                        found.append({"forge": forge, "source_url": link, "playback_verified": False})
                except (ValueError, OSError, TimeoutError) as exc:
                    errors.append({"forge": forge, "project": identity, "error": type(exc).__name__})
    return {"schema": 1, "status": "source_references_only", "sources": found,
            "errors": errors, "projects_examined": len(seen)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-public-forges", action="store_true", required=True)
    args = parser.parse_args()
    report = scan()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Forge source references:", len(report["sources"]), "errors:", len(report["errors"]))
if __name__ == "__main__":
    main()
