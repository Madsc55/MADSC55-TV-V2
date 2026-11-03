#!/usr/bin/env python3
"""Source-service availability only. Never scans stream URLs or changes IBO playlists."""
import argparse
import datetime
import json
import pathlib
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "reports/source-adapter-service-health.json"
ALLOWED_HOSTS = {"iptv-org.github.io", "raw.githubusercontent.com",
                 "api.github.com", "gitlab.com", "codeberg.org"}
MAX_JSON_BYTES = 128000
SOURCES = (
    {"id": "iptv-org-tr", "url": "https://iptv-org.github.io/iptv/countries/tr.m3u", "type": "m3u"},
    {"id": "free-tv-independent", "url": "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8", "type": "m3u"},
    {"id": "github-repository-search-api", "url": "https://api.github.com/search/repositories?q=iptv&per_page=1", "type": "github"},
    {"id": "github-gist-public-api", "url": "https://api.github.com/gists/public?per_page=1", "type": "gist"},
    {"id": "gitlab-public-projects-api", "url": "https://gitlab.com/api/v4/projects?search=iptv&per_page=1", "type": "gitlab"},
    {"id": "codeberg-repository-search-api", "url": "https://codeberg.org/api/v1/repos/search?q=iptv&limit=1", "type": "codeberg"},
)


def safe_source_url(url):
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and p.hostname in ALLOWED_HOSTS
                and not p.username and not p.password and not p.fragment
                and p.port in (None, 443))
    except (ValueError, TypeError):
        return False


def probe(service):
    url, source_type = service["url"], service["type"]
    if not safe_source_url(url):
        return {"status": "INVALID_SOURCE_URL"}
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            p = urlsplit(newurl)
            if not safe_source_url(newurl) or p.hostname != urlsplit(req.full_url).hostname:
                raise ValueError("Unsafe source redirect")
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SafeRedirect())
    headers = {"User-Agent": "MADSC55-TV-V2-SourceServiceHealth/1.0",
               "Accept": "application/json" if source_type != "m3u" else "*/*"}
    if source_type == "m3u":
        headers["Range"] = "bytes=0-1023"
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(req, timeout=8) as response:
            data = response.read(1024 if source_type == "m3u" else MAX_JSON_BYTES + 1)
            status_code = response.status
        if source_type == "m3u":
            valid = data.removeprefix(b"\xef\xbb\xbf").lstrip().startswith(b"#EXTM3U")
        elif len(data) > MAX_JSON_BYTES:
            valid = False
        else:
            document = json.loads(data.decode("utf-8"))
            valid = {
                "github": lambda d: isinstance(d, dict) and isinstance(d.get("items"), list),
                "gist": lambda d: isinstance(d, list),
                "gitlab": lambda d: isinstance(d, list),
                "codeberg": lambda d: isinstance(d, dict) and isinstance(d.get("data"), list),
            }[source_type](document)
        return {"status": "AVAILABLE" if valid else "INVALID_RESPONSE", "http_status": status_code}
    except urllib.error.HTTPError as exc:
        return {"status": "HTTP_ERROR", "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, ValueError, UnicodeError, OSError, json.JSONDecodeError) as exc:
        return {"status": "FETCH_ERROR", "error": type(exc).__name__}


def audit(sources=SOURCES, check=probe):
    results = [{"source_id": source["id"], "type": source["type"], **check(source)}
               for source in sources]
    available = sum(item["status"] == "AVAILABLE" for item in results)
    return {"schema": 1, "kind": "source-service-health-not-channel-playback",
            "checked": len(results), "available": available,
            "unavailable": len(results) - available,
            "coverage_status": "COMPLETE" if available == len(results) else
                               "PARTIAL" if available else "UNAVAILABLE",
            "results": results, "streams_scanned": 0, "playback_verified": False,
            "playlist_modified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-source-services", action="store_true", required=True)
    parser.parse_args()
    report = audit()
    report["created_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Source service health:", report["available"], "/", report["checked"],
          "available; coverage:", report["coverage_status"])


if __name__ == "__main__":
    main()
