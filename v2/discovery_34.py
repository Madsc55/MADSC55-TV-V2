#!/usr/bin/env python3
"""#34: read-only source discovery; offline by default. No playlist writes."""
import argparse
import ipaddress
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

QUERIES = ("turkiye.m3u", "tr.m3u8", "turkish-iptv", "canli-tv", "yerel-tv", "iptv-turkiye")
SOURCES = ("github", "gitlab", "codeberg", "official", "youtube", "m3u")
MAX_BYTES = 2_000_000

def identity(source, url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("https", "http") or not p.hostname:
        raise ValueError("Invalid public URL")
    if p.username or p.password:
        raise ValueError("Credential-bearing URL")
    try:
        _ = p.port
    except ValueError as exc:
        raise ValueError("Invalid URL port") from exc
    host = p.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Private hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Non-public IP address")
    if source not in SOURCES:
        raise ValueError("Unknown adapter")
    expected_hosts = {"github": "github.com", "gitlab": "gitlab.com", "codeberg": "codeberg.org", "youtube": "www.youtube.com"}
    if source in expected_hosts and (p.scheme != "https" or host != expected_hosts[source]):
        raise ValueError("Unexpected source host or insecure scheme")
    return {"source": source, "source_id": source + ":" + host + p.path, "url": url, "verified_av": False}

def search_url(source, query):
    q = urllib.parse.quote(query, safe="")
    if source == "github":
        return "https://api.github.com/search/repositories?q=" + q + "&per_page=20"
    if source == "gitlab":
        return "https://gitlab.com/api/v4/projects?search=" + q + "&per_page=20"
    if source == "codeberg":
        return "https://codeberg.org/api/v1/repos/search?q=" + q + "&limit=20"
    raise ValueError("Adapter uses curated identifiers, not repository search")

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Reject redirects before a second network request is made."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect refused")

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-V2-Discovery/1.0", "Accept": "application/json"})
    with urllib.request.build_opener(_NoRedirect).open(req, timeout=15) as res:
        if urllib.parse.urlsplit(res.url).hostname != urllib.parse.urlsplit(url).hostname:
            raise ValueError("Cross-host redirect refused")
        data = res.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Response too large")
    return json.loads(data)

def repository_candidates(source, payload):
    if source == "github":
        items = payload.get("items", [])
        url_key = "html_url"
    elif source == "gitlab":
        items = payload
        url_key = "web_url"
    elif source == "codeberg":
        items = payload.get("data", [])
        url_key = "html_url"
    else:
        raise ValueError("Not a repository adapter")
    results = []
    if not isinstance(items, list):
        raise ValueError("Invalid repository response")
    if source in ("github", "codeberg") and (("items" if source == "github" else "data") not in payload):
        raise ValueError("Missing repository result field")
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get(url_key, "")
        if not isinstance(url, str):
            continue
        try:
            results.append(identity(source, url))
        except ValueError:
            continue
    return results

def curated_candidates(source, records):
    """Official broadcaster URLs, YouTube watch IDs, and public M3U URLs.
    These are candidate identities only; never treat them as AV proof.
    """
    if source not in ("official", "youtube", "m3u"):
        raise ValueError("Not a curated adapter")
    out = []
    for item in records:
        if not isinstance(item, dict):
            continue
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if source == "youtube":
            video_id = item.get("video_id", "")
            if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                continue
            url = "https://www.youtube.com/watch?v=" + video_id
        if not isinstance(url, str):
            continue
        try:
            candidate = identity(source, url)
            if source == "youtube":
                candidate["source_id"] = "youtube:" + video_id
            out.append(candidate)
        except ValueError:
            continue
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", action="store_true", help="Explicit opt-in repository metadata queries")
    parser.add_argument("--output", default="v2/reports/discovery-34-candidates.json")
    parser.add_argument("--curated-input", type=Path, help="Offline JSON mapping of official/youtube/m3u candidates")
    args = parser.parse_args()
    candidates, errors = [], []
    if args.curated_input is not None:
        curated = json.loads(args.curated_input.read_text(encoding="utf-8"))
        if not isinstance(curated, dict) or any(
                key not in ("official", "youtube", "m3u") or not isinstance(value, list)
                for key, value in curated.items()):
            parser.error("curated input must map official/youtube/m3u to arrays")
        for source, records in curated.items():
            candidates.extend(curated_candidates(source, records))
    if args.network:
        for source in ("github", "gitlab", "codeberg"):
            for query in QUERIES:
                try:
                    candidates.extend(repository_candidates(source, fetch_json(search_url(source, query))))
                except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    errors.append({"source": source, "query": query, "error": type(exc).__name__})
    unique = {item["source_id"]: item for item in candidates}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"mode": "network" if args.network else "offline", "candidates": list(unique.values()), "errors": errors, "av_verified": 0}, indent=2) + "\n", encoding="utf-8")
    print("Candidate identities:", len(unique), "Errors:", len(errors))

if __name__ == "__main__":
    main()
