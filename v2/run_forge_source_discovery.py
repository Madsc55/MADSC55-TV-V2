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
from forge_source_discovery import (GITLAB_API, CODEBERG_API, TERMS, MAX_PATHS,
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

def scan(request=None, terms=None):
    # Late binding keeps runtime configuration and offline mock injection consistent.
    if request is None:
        request = api_json
    if terms is None:
        terms = TERMS
    found, errors, seen, limits_hit, found_urls = [], [], set(), set(), set()
    for term in dict.fromkeys(terms):
        queries = [
            ("gitlab", GITLAB_API + "?" + urlencode({"search": term, "simple": "true", "per_page": 12})),
            ("codeberg", CODEBERG_API + "?" + urlencode({"q": term, "limit": 12})),
        ]
        for forge, url in queries:
            try:
                payload = request(url)
                projects = gitlab_projects(payload) if forge == "gitlab" else codeberg_projects(payload)
                # Follow bounded search pagination rather than silently dropping
                # repositories beyond the first response.
                first_count = len(payload) if forge == "gitlab" and isinstance(payload, list) else (
                    len(payload.get("data", [])) if isinstance(payload, dict) else 0)
                if first_count >= 12:
                    for page in (2, 3):
                        next_url = url + (("&page=" + str(page)) if forge == "gitlab"
                                          else ("&page=" + str(page)))
                        more = request(next_url)
                        more_items = gitlab_projects(more) if forge == "gitlab" else codeberg_projects(more)
                        projects.extend(more_items)
                        raw_count = len(more) if forge == "gitlab" and isinstance(more, list) else (
                            len(more.get("data", [])) if isinstance(more, dict) else 0)
                        if raw_count < 12:
                            break
                    else:
                        limits_hit.add(forge.upper() + "_PROJECT_PAGE_LIMIT")
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
                    listing = request(tree)
                    if forge == "gitlab" and isinstance(listing, list) and len(listing) >= 100:
                        combined = list(listing)
                        for page in (2, 3):
                            more = request(tree + "&page=" + str(page))
                            if not isinstance(more, list):
                                raise ValueError("Invalid GitLab tree page")
                            combined.extend(more)
                            if len(more) < 100:
                                break
                        else:
                            limits_hit.add("GITLAB_TREE_PAGE_LIMIT")
                        listing = combined
                    if forge == "codeberg" and isinstance(listing, dict):
                        if listing.get("truncated"):
                            limits_hit.add("CODEBERG_TRUNCATED_TREE")
                        listing = listing.get("tree", [])
                    paths = parse_tree_paths(listing)
                    if sum(isinstance(p, str) and p.lower().endswith((".m3u", ".m3u8")) for p in paths) > MAX_PATHS:
                        limits_hit.add(forge.upper() + "_PLAYLIST_PATH_LIMIT")
                    for link in playlist_sources(project, paths):
                        if link not in found_urls:
                            found_urls.add(link)
                            found.append({"forge": forge, "source_url": link, "playback_verified": False})
                except (ValueError, OSError, TimeoutError) as exc:
                    errors.append({"forge": forge, "project": identity, "error": type(exc).__name__})
    return {"schema": 1, "status": "source_references_only",
            "coverage_status": "PARTIAL_API_ERRORS" if errors else "PARTIAL_LIMITS" if limits_hit else "COMPLETE_QUERIES",
            "limits_hit": sorted(limits_hit),
            "sources": found, "source_count": len(found), "playback_verified": False,
            "errors": errors, "projects_examined": len(seen)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-public-forges", action="store_true", required=True)
    args = parser.parse_args()
    report = scan()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Forge source references:", len(report["sources"]), "errors:", len(report["errors"]))
    if report["errors"] or report["limits_hit"]:
        print("WARNING: Partial forge source discovery; inspect saved errors and limits")
if __name__ == "__main__":
    main()
