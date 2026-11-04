#!/usr/bin/env python3
"""Opt-in, bounded live-page reference scan from explicitly approved public HTTPS pages.

This extracts references only. No HLS inference, playback checks, logins or
changes to IBO playlists. Never prints query strings from discovered links.
"""
import argparse
import hashlib
import json
import time
from collections import Counter
import urllib.error
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

def safe_page_redirect(origin_url, target_url):
    """Permit only public HTTPS redirects between the same host and www alias."""
    if not approved_page(target_url):
        return False
    origin = urlsplit(origin_url).hostname.lower()
    target = urlsplit(target_url).hostname.lower()
    return origin.removeprefix("www.") == target.removeprefix("www.")


def fetch_page(url):
    if not approved_page(url):
        raise ValueError("Only approved public HTTPS page URLs are allowed")
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            if not approved_page(newurl):
                raise ValueError("Unsafe live page redirect: INVALID_TARGET")
            if not safe_page_redirect(url, newurl):
                raise ValueError("Unsafe live page redirect: CROSS_HOST")
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-LiveReference/1.0"})
    for attempt in range(3):
        try:
            with opener.open(request, timeout=12) as response:
                content = response.read(MAX_BYTES + 1)
            break
        except urllib.error.HTTPError as exc:
            # Retry only transient HTTP failures; do not bypass 403 or
            # pretend a blocked publisher page has been inspected.
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(min(2 ** attempt, 3))
        except (urllib.error.URLError, TimeoutError):
            # The official AZTV site has intermittently failed DNS/network
            # lookups. Retry bounded transport failures only, retaining
            # the original error if no actual page was fetched.
            if attempt == 2:
                raise
            time.sleep(min(2 ** attempt, 3))
    if len(content) > MAX_BYTES:
        raise ValueError("Live page too large")
    return content.decode("utf-8", errors="replace")

def error_kind(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP_" + str(exc.code)
    if isinstance(exc, ValueError):
        # Categorize our own security decisions without publishing the
        # redirected destination, query parameters, or a token-bearing URL.
        code = str(exc).removeprefix("Unsafe live page redirect: ")
        if code in ("INVALID_TARGET", "CROSS_HOST"):
            return "REDIRECT_" + code
    return type(exc).__name__


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
            errors.append({"page_id": page_id, "error": error_kind(exc)})
    return {"schema": 1, "kind": "references-only", "pages_checked": len(pages),
            "coverage_status": ("NO_APPROVED_PAGES" if not pages else
                                "PARTIAL_APPROVED_PAGES" if errors else "APPROVED_PAGES_CHECKED"),
            "references": result, "errors": errors,
            "anonymous_error_summary": dict(sorted(Counter(x["error"] for x in errors).items())),
            "playback_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-approved-live-pages", action="store_true", required=True)
    args = parser.parse_args()
    pages = json.loads(CONFIG.read_text(encoding="utf-8"))["pages"]
    report = scan(pages)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Live-page references:", len(report["references"]), "errors:", len(report["errors"]),
          "anonymous_error_summary:", json.dumps(report["anonymous_error_summary"], sort_keys=True))
    if report["errors"]:
        print("WARNING: Partial approved live-page scan; review saved page IDs")
if __name__ == "__main__":
    main()
