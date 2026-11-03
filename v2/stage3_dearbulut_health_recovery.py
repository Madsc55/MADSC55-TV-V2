#!/usr/bin/env python3
"""Exact original-URL recovery from historical Dearbulut health evidence.

Reads date-pinned PUBLIC GitHub state/health.json files; no stream probes,
new channel discovery or V2 main playlist changes. Only URL SHA256 and
historical commit provenance enter the public report (never raw URLs).
"""
import argparse
import hashlib
import json
from pathlib import Path
from historical_local_match import validate_index
from historical_url_recovery import validate_url
from stage3_historical_source_recovery import _read

HEALTH_STATE_REVISIONS = (
    ("2026-10-28T09:09Z", "9d6be2e58c3d7d6951940fd48ac124913bf56e71"),
    ("2026-10-27T19:47Z", "385521184366c16c064e44ef8ebc8f539f6f03df"),
    ("2026-10-27T08:32Z", "5145c140d40626e12a18868f7d72938f94a91179"),
)


def audit_health(history):
    hashes = validate_index(history, 4955)
    found, source_details = {}, []
    for timestamp, sha in HEALTH_STATE_REVISIONS:
        item = {"historical_utc": timestamp, "state_commit": sha,
                "exact_url_hash_matches": 0}
        try:
            url = ("https://raw.githubusercontent.com/dearbulut/iptv/" + sha +
                   "/health.json")
            data = json.loads(_read(url).decode("utf-8-sig", errors="replace"))
            if not isinstance(data, list):
                raise ValueError("Expected a historical health record list")
            matched = set()
            for row in data:
                if not isinstance(row, dict):
                    continue
                raw = row.get("url")
                if not validate_url(raw):
                    continue
                identity = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                if identity in hashes:
                    matched.add(identity)
                    found.setdefault(identity, {"url": raw, "url_sha256": identity,
                                                "source": "dearbulut-online",
                                                "source_ids": ["dearbulut-health-" + sha[:12]]})
            item.update(status="HISTORICAL_HEALTH_READ", health_rows=len(data),
                        exact_url_hash_matches=len(matched))
        except Exception as exc:
            # Exception details could contain URLs, so report type only.
            item.update(status="HISTORICAL_HEALTH_UNAVAILABLE",
                        error_type=type(exc).__name__)
        source_details.append(item)
    result = {
        "schema": 1,
        "policy": "HISTORICAL_PUBLIC_HEALTH_ONLY_SHA256_NO_PLAYBACK",
        "historical_hash_identities": 4955,
        "recovered_unique_url_hashes": len(found),
        "still_unmatched_in_health": 4955-len(found),
        "matched_hashes": sorted(found),
        "source_audit": source_details,
        "protected_main_playlist_modified": False,
        "new_channels_discovered": 0,
        "stream_media_reverified": False,
        "device_verified": False,
        "public_report_has_plaintext_urls": False,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink() or args.report.resolve() == args.index.resolve():
        parser.error("Refusing report overwrite or collision")
    history = [json.loads(line) for line in args.index.read_text(encoding="utf-8").splitlines() if line]
    report = audit_health(history)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("Dearbulut historical state snapshots: recovered exact hash identities",
          report["recovered_unique_url_hashes"], "from", len(HEALTH_STATE_REVISIONS),
          "date-pinned health archives")


if __name__ == "__main__":
    main()
