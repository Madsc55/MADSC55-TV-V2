#!/usr/bin/env python3
"""Bounded, read-only public GitLab/Codeberg playlist reference discovery."""
import argparse
import datetime
import json
import pathlib
import urllib.parse
import urllib.request

from forge_source_discovery import (GITLAB_API, CODEBERG_API, TERMS, MAX_PROJECTS,
                                    gitlab_projects, codeberg_projects,
                                    parse_tree_paths, playlist_sources)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "v2/reports/forge-source-discovery.json"
MAX_RESPONSE = 2_000_000
HOSTS = {"gitlab.com", "codeberg.org"}


def api_json(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 443):
        raise ValueError("Untrusted forge API URL")
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            t = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl))
            if t.scheme != "https" or t.hostname not in HOSTS or t.username or t.password or t.port not in (None, 443):
                raise ValueError("Unsafe forge API redirect")
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SafeRedirect())
    with opener.open(urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-Forge/1.0"}), timeout=15) as response:
        payload = response.read(MAX_RESPONSE + 1)
    if len(payload) > MAX_RESPONSE:
        raise ValueError("Forge API response too large")
    return json.loads(payload.decode("utf-8"))


def scan(request=api_json, terms=TERMS):
    sources, errors, seen = [], [], set()
    for term in terms:
        for forge in ("gitlab", "codeberg"):
            try:
                if forge == "gitlab":
                    url = GITLAB_API + "?" + urllib.parse.urlencode({"search": term, "per_page": MAX_PROJECTS, "simple": "true"})
                    projects = gitlab_projects(request(url))
                else:
                    url = CODEBERG_API + "?" + urllib.parse.urlencode({"q": term, "limit": MAX_PROJECTS})
                    projects = codeberg_projects(request(url))
            except (OSError, ValueError, TypeError, KeyError) as exc:
                errors.append({"forge": forge, "stage": "search", "term": term, "error": type(exc).__name__})
                continue
            for project in projects:
                try:
                    if forge == "gitlab":
                        tree = "https://gitlab.com/api/v4/projects/" + str(project["id"]) + "/repository/tree?" + urllib.parse.urlencode({"ref": project["branch"], "recursive": "true", "per_page": 100})
                        paths = parse_tree_paths(request(tree))
                    else:
                        tree = ("https://codeberg.org/api/v1/repos/" + urllib.parse.quote(project["owner"], safe="") + "/" + urllib.parse.quote(project["name"], safe="") + "/git/trees/" + urllib.parse.quote(project["branch"], safe="") + "?recursive=true")
                        payload = request(tree)
                        paths = parse_tree_paths(payload.get("tree", [])) if isinstance(payload, dict) else []
                    for source_url in playlist_sources(project, paths):
                        if source_url not in seen:
                            seen.add(source_url)
                            sources.append({"forge": forge, "source_url": source_url, "status": "REFERENCE_ONLY_NOT_PLAYBACK_VERIFIED"})
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    errors.append({"forge": forge, "stage": "tree", "error": type(exc).__name__})
    return {"schema": 1, "policy": "READ_ONLY_NO_AUTOMATIC_SOURCE_OR_PLAYLIST_IMPORT",
            "sources": sources, "errors": errors, "source_count": len(sources),
            "coverage_status": "PARTIAL_API_ERRORS" if errors else "COMPLETE_REQUESTS",
            "playback_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    report = ({"schema": 1, "sources": [], "errors": [], "source_count": 0,
               "coverage_status": "OFFLINE_NO_NETWORK", "playback_verified": False}
              if args.offline else scan())
    report["created_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Forge sources:", report["source_count"], "API errors:", len(report["errors"]))


if __name__ == "__main__":
    main()
