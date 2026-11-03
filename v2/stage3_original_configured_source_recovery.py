#!/usr/bin/env python3
"""Read-only recovery of original #60 configured source URL SHA256 identities.

Checks pinned Oct 28 IPTV-org and Free-TV commits, plus a separately labeled
current dearbulut public feed; never probes streams or writes plaintext URLs.
"""
import argparse
import json
from pathlib import Path
from historical_local_match import validate_index
from stage3_historical_source_recovery import _read, match_feed

SOURCES = (
    ("iptv-org", "iptv-org-gh-pages-20261028",
     "https://raw.githubusercontent.com/iptv-org/iptv/d3ce1f14b78328402fcccef539febc7ee4ec0104/index.m3u",
     "PINNED_HISTORICAL_GIT_COMMIT"),
    ("free-tv-independent", "free-tv-master-20261028",
     "https://raw.githubusercontent.com/Free-TV/IPTV/5322cfc888ea41fb8dfe8ca1bba1513679d5f6b9/playlist.m3u8",
     "PINNED_HISTORICAL_GIT_COMMIT"),
    ("dearbulut-online", "dearbulut-current-public",
     "https://dearbulut.github.io/iptv/playlists/online.m3u",
     "CURRENT_PUBLISHED_FEED_NOT_HISTORICAL"),
)


def audit_configured(history):
    hashes = validate_index(history, 4955)
    found, audits = {}, []
    for source, label, url, provenance in SOURCES:
        item = {"source": source, "reference": label, "provenance": provenance,
                "matched_hashes": 0}
        try:
            text = _read(url).decode("utf-8-sig", errors="replace")
            matches, parsed = match_feed(hashes, text, source)
            item.update(status="READ", parsed_valid_urls=parsed,
                        matched_hashes=len(matches))
            for key, row in matches.items():
                if key not in found:
                    found[key] = row
        except Exception as exc:
            # Do not print exception text, which could include URL credentials.
            item.update(status="UNAVAILABLE", error_type=type(exc).__name__)
        audits.append(item)
    return {
        "schema": 1,
        "policy": "EXACT_SHA256_EXISTING_CONFIGURED_SOURCE_URL_LOOKUP",
        "historical_hash_identities": 4955,
        "matched_hashes": sorted(found),
        "unique_exact_url_hash_matches": len(found),
        "unmatched_historical_hashes": 4955-len(found),
        "source_audit": audits,
        "new_source_discovery": False,
        "playback_reverified": False,
        "device_verified": False,
        "main_playlist_modified": False,
        "plaintext_urls_logged": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink() or args.report.resolve() == args.index.resolve():
        parser.error("Refusing overwrite or report/input collision")
    history = [json.loads(line) for line in args.index.read_text(encoding="utf-8").splitlines() if line]
    result = audit_configured(history)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    print("Configured original sources: exact URL identities", result["unique_exact_url_hash_matches"],
          "unmatched in this source set:", result["unmatched_historical_hashes"])


if __name__ == "__main__":
    main()
