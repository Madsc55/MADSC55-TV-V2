#!/usr/bin/env python3
"""Approved public HTML indexes: discover M3U links for manual source review only."""
import argparse
import hashlib
import json
from pathlib import Path
from run_live_page_discovery import approved_page, fetch_page
from webpage_source_discovery import discover_playlist_links

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "playlist-index-pages.json"
REPORT = ROOT / "reports" / "webpage-playlist-references.json"

def scan(pages, fetcher=fetch_page):
    if len(pages) > 100:
        raise ValueError("HTML index inventory exceeds 100 pages")
    found, errors, seen = [], [], set()
    for item in pages:
        page_id, url = item["id"], item["url"]
        if not approved_page(url):
            errors.append({"page_id": page_id, "error": "UNSAFE_PAGE"})
            continue
        try:
            for link in discover_playlist_links(url, fetcher(url))[:200]:
                digest = hashlib.sha256(link.encode("utf-8")).hexdigest()
                if digest not in seen:
                    seen.add(digest)
                    found.append({"page_id": page_id, "url_sha256": digest,
                                  "review_required": True, "playback_verified": False})
        except (OSError, ValueError, TimeoutError) as exc:
            errors.append({"page_id": page_id, "error": type(exc).__name__})
    return {"schema": 1, "kind": "playlist-references-only",
            "pages_checked": len(pages), "references": found, "errors": errors,
            "coverage_status": ("NO_APPROVED_PAGES" if not pages else
                                "PARTIAL_APPROVED_PAGES" if errors else "APPROVED_PAGES_CHECKED"),
            "playback_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-approved-index-pages", action="store_true", required=True)
    parser.parse_args()
    pages = json.loads(CONFIG.read_text(encoding="utf-8"))["pages"]
    report = scan(pages)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("HTML playlist references:", len(report["references"]), "errors:", len(report["errors"]))
    if report["errors"]:
        print("WARNING: Partial HTML index scan; review saved page IDs")
if __name__ == "__main__":
    main()
