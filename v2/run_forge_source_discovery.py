#!/usr/bin/env python3
"""Opt-in, bounded public GitLab/Codeberg source discovery.

Writes only M3U source references to a separate report. Does not fetch stream
URLs, alter the live playlist or automatically promote unknown sources.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode, quote, urlsplit
from webpage_source_discovery import public_hostname
import urllib.request
import urllib.error
import time
from collections import Counter
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
    for attempt in range(3):
        try:
            with opener.open(request, timeout=12) as response:
                payload = response.read(2_000_001)
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(min(2 ** attempt, 3))
        except (TimeoutError, urllib.error.URLError):
            # Only bounded transport retries; never bypass 403/404 or unsafe redirects.
            if attempt == 2:
                raise
            time.sleep(min(2 ** attempt, 3))
    if len(payload) > 2_000_000:
        raise ValueError("Forge response too large")
    return json.loads(payload)

def error_kind(exc):
    return ("HTTP_" + str(exc.code)) if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__


def error_summary(rows):
    counts = Counter(str(row.get("forge", "?")) + ":" + str(row.get("error", "?")) for row in rows)
    return dict(sorted(counts.items()))


def scan(request=None, terms=None):
    # Late binding keeps runtime configuration and offline mock injection consistent.
    if request is None:
        request = api_json
    if terms is None:
        terms = TERMS
    found, errors, seen, limits_hit, found_urls = [], [], set(), set(), set()
    confirmed_empty_projects, stale_branches_refreshed = set(), 0
    relocated_projects_recovered = 0
    gitlab_default_ref_tree_recoveries = 0
    gitlab_public_branch_listing_recoveries = 0
    for term in dict.fromkeys(terms):
        queries = [
            ("gitlab", GITLAB_API + "?" + urlencode({"search": term, "simple": "true", "per_page": 12})),
            ("codeberg", CODEBERG_API + "?" + urlencode({"q": term, "limit": 12})),
        ]
        for forge, url in queries:
            try:
                payload = request(url)
                if (forge == "gitlab" and not isinstance(payload, list)) or (forge == "codeberg" and not isinstance(payload, dict)):
                    raise ValueError("Invalid forge search response")
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
                errors.append({"forge": forge, "term": term, "error": error_kind(exc)})
                continue
            for project in projects:
                identity = json.dumps(project, sort_keys=True)
                if identity in seen:
                    continue
                seen.add(identity)
                if forge == "gitlab":
                    tree = (GITLAB_API + "/" + str(project["id"]) + "/repository/tree?"
                            + urlencode({"ref": project["branch"], "recursive": "true", "per_page": 100, "pagination": "keyset"}))
                else:
                    tree = ("https://codeberg.org/api/v1/repos/"
                            + quote(project["owner"], safe="") + "/"
                            + quote(project["name"], safe="") + "/git/trees/"
                            + quote(project["branch"], safe="") + "?recursive=true")
                try:
                    try:
                        listing = request(tree)
                    except urllib.error.HTTPError as exc:
                        if forge != "gitlab" or exc.code != 404:
                            raise
                        # A public GitLab search index may retain a stale
                        # default branch or an empty repository. Recheck the
                        # *exact* publicly indexed project ID before treating
                        # the 404 as a lost source; never suppress an unknown
                        # 404 or try an unauthorised project.
                        previous_id, previous_branch = project["id"], project["branch"]
                        from_verified_path = False
                        try:
                            detail = request(GITLAB_API + "/" + str(previous_id))
                        except urllib.error.HTTPError as detail_error:
                            original_path = project.get("path_with_namespace")
                            if detail_error.code != 404 or not original_path:
                                raise
                            # Recover only via the exact public path supplied
                            # by the original GitLab search metadata.
                            detail = request(GITLAB_API + "/" + quote(original_path, safe=""))
                            from_verified_path = True
                        if not isinstance(detail, dict):
                            raise ValueError("Malformed GitLab project refresh")
                        refreshed_id = detail.get("id")
                        if not isinstance(refreshed_id, int) or refreshed_id <= 0:
                            raise ValueError("Invalid refreshed GitLab project ID")
                        if (from_verified_path and
                                detail.get("path_with_namespace") != project["path_with_namespace"]):
                            raise ValueError("GitLab project path changed unexpectedly")
                        if not from_verified_path and refreshed_id != previous_id:
                            raise ValueError("GitLab project ID mismatch")
                        if detail.get("empty_repo") is True:
                            confirmed_empty_projects.add(previous_id)
                            continue
                        branch = detail.get("default_branch")
                        if not isinstance(branch, str) or not branch:
                            raise
                        project = dict(project, id=refreshed_id, branch=branch)
                        tree = (GITLAB_API + "/" + str(project["id"]) + "/repository/tree?"
                                + urlencode({"ref": project["branch"], "recursive": "true",
                                             "per_page": 100, "pagination": "keyset"}))
                        try:
                            if branch != previous_branch or refreshed_id != previous_id:
                                try:
                                    listing = request(tree)
                                except urllib.error.HTTPError as retry_exc:
                                    if retry_exc.code != 404:
                                        raise
                                    # Public default root, no speculative ref.
                                    tree = (GITLAB_API + "/" + str(project["id"])
                                            + "/repository/tree?"
                                            + urlencode({"recursive": "true", "per_page": 100,
                                                         "pagination": "keyset"}))
                                    listing = request(tree)
                                    gitlab_default_ref_tree_recoveries += 1
                            else:
                                tree = (GITLAB_API + "/" + str(project["id"])
                                        + "/repository/tree?"
                                        + urlencode({"recursive": "true", "per_page": 100,
                                                     "pagination": "keyset"}))
                                listing = request(tree)
                                gitlab_default_ref_tree_recoveries += 1
                        except urllib.error.HTTPError as root_exc:
                            if root_exc.code != 404:
                                raise
                            # If GitLab's default metadata is stale, inspect
                            # only the exact verified *public* project's listed
                            # default branch. Never guess main/master, or
                            # follow an arbitrary ref or private repository.
                            branch_rows = request(
                                GITLAB_API + "/" + str(project["id"]) +
                                "/repository/branches?per_page=20")
                            if not isinstance(branch_rows, list) or len(branch_rows) > 20:
                                raise ValueError("Invalid public GitLab branch list")
                            approved = [x["name"] for x in branch_rows
                                        if isinstance(x, dict) and
                                        x.get("default") is True and
                                        isinstance(x.get("name"), str) and
                                        1 <= len(x["name"]) <= 120 and
                                        x["name"] not in (".", "..") and
                                        ".." not in x["name"].split("/") and
                                        re.fullmatch(
                                            r"[A-Za-z0-9_.\-/]+", x["name"])]
                            if len(approved) != 1 or approved[0] == branch:
                                raise root_exc
                            project = dict(project, branch=approved[0])
                            tree = (GITLAB_API + "/" + str(project["id"])
                                    + "/repository/tree?"
                                    + urlencode({"ref": project["branch"],
                                                 "recursive": "true", "per_page": 100,
                                                 "pagination": "keyset"}))
                            listing = request(tree)
                            gitlab_public_branch_listing_recoveries += 1
                        if branch != previous_branch:
                            stale_branches_refreshed += 1
                        if refreshed_id != previous_id:
                            relocated_projects_recovered += 1
                    if forge == "gitlab":
                        if not isinstance(listing, list):
                            raise ValueError("Invalid GitLab repository tree")
                        if len(listing) >= 100:
                            combined = list(listing)
                            current_page = listing
                            for page in (2, 3):
                                # GitLab 15+ repository trees use keyset pagination.
                                # Falling back to &page= on a keyset URL is invalid
                                # and can manufacture HTTP errors or duplicate pages.
                                last_id = current_page[-1].get("id") if isinstance(current_page[-1], dict) else None
                                if not isinstance(last_id, str) or not last_id:
                                    limits_hit.add("GITLAB_TREE_KEYSET_TOKEN_UNAVAILABLE")
                                    break
                                next_url = tree + "&page_token=" + quote(last_id, safe="")
                                more = request(next_url)
                                if not isinstance(more, list):
                                    raise ValueError("Invalid GitLab tree page")
                                if more == current_page:
                                    limits_hit.add("GITLAB_TREE_REPEAT_PAGE")
                                    break
                                combined.extend(more)
                                current_page = more
                                if len(more) < 100:
                                    break
                            else:
                                limits_hit.add("GITLAB_TREE_PAGE_LIMIT")
                            listing = combined
                    else:
                        if not isinstance(listing, dict) or not isinstance(listing.get("tree"), list):
                            raise ValueError("Invalid Codeberg repository tree")
                        if listing.get("truncated"):
                            limits_hit.add("CODEBERG_TRUNCATED_TREE")
                        listing = listing["tree"]
                    paths = parse_tree_paths(listing)
                    if sum(isinstance(p, str) and p.lower().endswith((".m3u", ".m3u8")) for p in paths) > MAX_PATHS:
                        limits_hit.add(forge.upper() + "_PLAYLIST_PATH_LIMIT")
                    for link in playlist_sources(project, paths):
                        if link not in found_urls:
                            found_urls.add(link)
                            found.append({"forge": forge, "source_url": link, "playback_verified": False})
                except (ValueError, OSError, TimeoutError) as exc:
                    errors.append({"forge": forge, "project": identity, "error": error_kind(exc)})
    return {"schema": 1, "status": "source_references_only",
            "coverage_status": "PARTIAL_API_ERRORS" if errors else "PARTIAL_LIMITS" if limits_hit else "COMPLETE_QUERIES",
            "limits_hit": sorted(limits_hit),
            "sources": found, "source_count": len(found), "playback_verified": False,
            "errors": errors, "anonymous_error_summary": error_summary(errors),
            "projects_examined": len(seen),
            "gitlab_confirmed_empty_projects_skipped": len(confirmed_empty_projects),
            "gitlab_stale_branch_recoveries": stale_branches_refreshed,
            "gitlab_relocated_projects_recovered": relocated_projects_recovered,
            "gitlab_default_ref_tree_recoveries": gitlab_default_ref_tree_recoveries,
            "gitlab_public_branch_listing_recoveries": gitlab_public_branch_listing_recoveries}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-public-forges", action="store_true", required=True)
    args = parser.parse_args()
    report = scan()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Forge source references:", len(report["sources"]), "errors:", len(report["errors"]),
          "anonymous_error_summary:", json.dumps(
              report.get("anonymous_error_summary", error_summary(report.get("errors", []))),
              sort_keys=True))
    if report.get("errors") or report.get("limits_hit"):
        print("WARNING: Partial forge source discovery; inspect saved errors and limits")
if __name__ == "__main__":
    main()
