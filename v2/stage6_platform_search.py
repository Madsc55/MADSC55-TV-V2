#!/usr/bin/env python3
"""Opt-in, read-only public repository discovery. No playlist edits or AV claims."""
import argparse
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request

from stage6_search_plan import TERMS

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "v2/reports/stage6-platform-search.json"
ENDPOINTS = {
    "github": "https://api.github.com/search/repositories",
    "gitlab": "https://gitlab.com/api/v4/projects",
    "codeberg": "https://codeberg.org/api/v1/repos/search",
    "gist": "https://api.github.com/gists/public",
}
UA = "MADSC55-TV-V2-Stage6/1.0"

def request_url(platform, term, page=1, per_page=10):
    if platform not in ENDPOINTS:
        raise ValueError("Unsupported platform")
    if not 1 <= page <= 10 or not 1 <= per_page <= 50:
        raise ValueError("Search bounds exceeded")
    if platform == "github":
        params = {"q": term, "page": page, "per_page": per_page}
    elif platform == "gitlab":
        params = {"search": term, "page": page, "per_page": per_page, "simple": "true"}
    elif platform == "codeberg":
        params = {"q": term, "page": page, "limit": per_page}
    else:
        params = {"page": page, "per_page": per_page}
    return ENDPOINTS[platform] + "?" + urllib.parse.urlencode(params)

def extract(platform, payload, term):
    if platform == "github":
        records = payload.get("items", [])
    elif platform == "codeberg":
        records = payload.get("data", [])
    else:
        records = payload
    if not isinstance(records, list):
        raise ValueError("Unexpected API response")
    result = []
    for item in records:
        if not isinstance(item, dict):
            continue
        if platform == "gist":
            files = item.get("files") or {}
            matched = [f for f in files.values() if isinstance(f, dict) and
                       str(f.get("filename", "")).lower().endswith((".m3u", ".m3u8"))]
            if not matched:
                continue
        url = item.get("html_url") or item.get("web_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        result.append({"platform": platform, "query": term,
                       "url": url, "kind": "PUBLIC_METADATA_NOT_STREAM_PROOF"})
    return result

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        if response.status != 200:
            raise ValueError("Unexpected HTTP status")
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Response too large")
        return json.loads(data)

def run(platforms, terms, max_results):
    records, failures = [], []
    seen = set()
    for platform in platforms:
        # Public Gist API is a chronological feed, not keyword search.
        # Fetch it once, then filter M3U filenames; do not claim full Gist coverage.
        queries = ["public_recent_m3u"] if platform == "gist" else terms
        for term in queries:
            try:
                rows = extract(platform, fetch_json(request_url(platform, term, per_page=max_results)), term)
                for row in rows:
                    if row["url"] not in seen:
                        records.append(row)
                        seen.add(row["url"])
            except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
                failures.append({"platform": platform, "query": term, "reason": type(exc).__name__})
    return {"kind": "PUBLIC_METADATA_DISCOVERY_NOT_AV_EVIDENCE",
            "platforms_attempted": platforms, "queries_attempted": terms,
            "gist_coverage": "RECENT_PUBLIC_ONLY_NOT_KEYWORD_SEARCH",
            "results": records, "failures": failures,
            "complete": not failures and "gist" not in platforms,
            "existing_channels_modified": False, "av_verified": False}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="explicitly enable public network discovery")
    ap.add_argument("--platforms", nargs="+", choices=tuple(ENDPOINTS), default=list(ENDPOINTS))
    ap.add_argument("--max-results", type=int, default=10)
    ap.add_argument("--output", type=pathlib.Path, default=OUTPUT)
    args = ap.parse_args()
    if not 1 <= args.max_results <= 50:
        ap.error("--max-results must be between 1 and 50")
    if not args.execute:
        ap.error("Network discovery is deferred; pass --execute after system acceptance")
    report = run(args.platforms, TERMS, args.max_results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"results": len(report["results"]), "failures": len(report["failures"]),
                      "complete": report["complete"]}))
    if report["failures"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
