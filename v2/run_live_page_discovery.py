#!/usr/bin/env python3
"""Opt-in, bounded live-page reference scan from explicitly approved public HTTPS pages.

This extracts references only. No HLS inference, playback checks, logins or
changes to IBO playlists. Never prints query strings from discovered links.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request
from webpage_source_discovery import public_hostname
from live_page_discovery import extract_live_references

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "live-pages.json"
REPORT = ROOT / "reports" / "live-page-references.json"
MAX_BYTES = 2_000_000

def approved_page(url):
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and bool(p.hostname) and public_hostname(p.hostname)
                and not p.username and not p.password and p.port in (None, 443)
                and not p.fragment and not p.query)
    except ValueError:
        return False

def fetch_page(url):
    if not approved_page(url):
        raise ValueError("Only approved public HTTPS page URLs are allowed")
    host = urlsplit(url).hostname
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            p = urlsplit(newurl)
            if not approved_page(newurl) or p.hostname != host:
                raise ValueError("Unsafe live page redirect")
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-LiveReference/1.0"})
    with opener.open(request, timeout=12) as response:
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("Live page too large")
    return content.decode("utf-8", errors="replace")

def scan(pages, fetcher=fetch_page):
    if len(pages) > 100:
        raise ValueError("Approved live-page inventory exceeds the 100-page scan limit")
    result, errors, seen = [], [], set()
    for item in pages:
        page_id, url = item["id"], item["url"]
        if not approved_page(url):
            errors.append({"page_id": page_id, "error": "UNSAFE_PAGE"})
            continue
        try:
            refs = extract_live_references(url, fetcher(url))
            for ref in refs:
                digest = hashlib.sha256(ref["url"].encode()).hexdigest()
                if digest not in seen:
                    seen.add(digest)
                    result.append({"page_id": page_id, "url_sha256": digest,
                                   "kind": ref["kind"], "playback_verified": False})
        except (ValueError, OSError, TimeoutError) as exc:
            errors.append({"page_id": page_id, "error": type(exc).__name__})
    return {"schema": 1, "kind": "references-only", "pages_checked": len(pages),
            "coverage_status": ("NO_APPROVED_PAGES" if not pages else
                                "PARTIAL_APPROVED_PAGES" if errors else "APPROVED_PAGES_CHECKED"),
            "references": result, "errors": errors, "playback_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-approved-live-pages", action="store_true", required=True)
    args = parser.parse_args()
    pages = json.loads(CONFIG.read_text(encoding="utf-8"))["pages"]
    report = scan(pages)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Live-page references:", len(report["references"]), "errors:", len(report["errors"]))
    if report["errors"]:
        print("WARNING: Partial approved live-page scan; review saved page IDs")
if __name__ == "__main__":
    main()
