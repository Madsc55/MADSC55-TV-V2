#!/usr/bin/env python3
"""Read-only GitLab and Codeberg public repository playlist discovery.

No credentials. Output only candidate public HTTPS playlist source URLs.
No channel URL playback, no private repository access, no playlist writes.
"""
import json
from urllib.parse import quote, urlsplit
from webpage_source_discovery import candidate_url

GITLAB_API = "https://gitlab.com/api/v4/projects"
CODEBERG_API = "https://codeberg.org/api/v1/repos/search"
TERMS = ("iptv tr", "turkish iptv", "azerbaijan iptv", "m3u turk")
MAX_PROJECTS = 12
MAX_PATHS = 30

def gitlab_projects(payload):
    if not isinstance(payload, list):
        return []
    result = []
    for item in payload[:MAX_PROJECTS]:
        if not isinstance(item, dict):
            continue
        project_id = item.get("id")
        branch = item.get("default_branch")
        if isinstance(project_id, int) and project_id > 0 and isinstance(branch, str) and branch:
            result.append({"forge": "gitlab", "id": project_id, "branch": branch})
    return result

def codeberg_projects(payload):
    items = payload.get("data", []) if isinstance(payload, dict) else []
    result = []
    for item in items[:MAX_PROJECTS]:
        if not isinstance(item, dict):
            continue
        owner = item.get("owner", {})
        owner_name = owner.get("login", "") if isinstance(owner, dict) else ""
        name, branch = item.get("name", ""), item.get("default_branch", "")
        if all(isinstance(x, str) and x and "/" not in x for x in (owner_name, name, branch)):
            result.append({"forge": "codeberg", "owner": owner_name, "name": name, "branch": branch})
    return result

def playlist_sources(project, paths):
    """Only explicitly listed playlist files; no speculative URL guessing."""
    result = []
    for path in paths[:MAX_PATHS]:
        if not isinstance(path, str) or not path.lower().endswith((".m3u", ".m3u8")):
            continue
        if path.startswith("/") or ".." in path.split("/"):
            continue
        if project["forge"] == "gitlab":
            url = ("https://gitlab.com/api/v4/projects/" + str(project["id"])
                   + "/repository/files/" + quote(path, safe="")
                   + "/raw?ref=" + quote(project["branch"], safe=""))
            # GitLab API raw URLs are not extension-suffixed; allowlist explicitly.
            result.append(url)
        else:
            url = ("https://codeberg.org/" + quote(project["owner"], safe="")
                   + "/" + quote(project["name"], safe="")
                   + "/raw/branch/" + quote(project["branch"], safe="")
                   + "/" + quote(path, safe="/"))
            if candidate_url(url):
                result.append(url)
    return result

def parse_tree_paths(items):
    if not isinstance(items, list):
        return []
    return [x["path"] for x in items if isinstance(x, dict)
            and x.get("type") in ("blob", "file")
            and isinstance(x.get("path"), str)]
