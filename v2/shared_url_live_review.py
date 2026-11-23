#!/usr/bin/env python3
"""Read-only bounded review of the canonical playlist's shared URL conflicts."""
import argparse
from collections import Counter, defaultdict
import datetime
import hashlib
import json
from pathlib import Path

from discover import entries
from shared_url_identity import normalized_url
from shared_url_safe_probe import inspect_url

ROOT = Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
DEFAULT_REPORT = ROOT / "v2/reports/shared-url-live-review.json"


def inventory(data):
    by_url = defaultdict(list)
    for item in entries(data):
        url = normalized_url(item["url"])
        if url:
            by_url[url].append(item)
    conflicts = []
    for url, records in by_url.items():
        identities = {(x["name"].casefold().strip(), x["tvg_id"].casefold().strip(),
                       x.get("program_number")) for x in records}
        if len(identities) <= 1:
            continue
        names = sorted({x["name"] for x in records})
        ids = sorted({x["tvg_id"] for x in records if x["tvg_id"]})
        groups = sorted({x["group"] for x in records})
        conflicts.append((url, {
            "url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "names": names,
            "tvg_ids": ids,
            "groups": groups,
            "records": len(records),
            "same_url_multiple_labels": len(names) > 1,
            "same_url_multiple_tvg_ids": len(ids) > 1,
            "playlist_program_selectors": sorted({
                r["program_number"] for r in records if
                isinstance(r.get("program_number"), int)
            }),
        }))
    return sorted(conflicts, key=lambda x: x[1]["url_sha256"])


def review(playlist_text, live=True, probe=inspect_url):
    findings = inventory(playlist_text)
    result = []
    for url, item in findings[:100]:
        evidence = probe(url) if live else {
            "status": "NOT_LIVE_CHECKED",
            "programs": [], "sample_bytes": 0,
            "distinct_broadcasters_verified": False,
            "audio_video_decoded_verified": False,
        }
        result.append({
            **item, "evidence": evidence,
            "identity_result": "INCONCLUSIVE_NO_BROADCASTER_IDENTITY_PROOF",
            "safe_to_remove_or_merge": False,
        })
    counts = Counter(row["evidence"]["status"] for row in result)
    return {
        "schema": 1,
        "policy": "READ_ONLY; no deletion, retagging, or broadcaster identity claim",
        "matched_url_groups": len(findings),
        "reviewed_url_groups": len(result),
        "truncated": len(findings) > 100,
        "live_requested": live,
        "status_counts": dict(sorted(counts.items())),
        "validated_distinct_broadcasters": 0,
        "modified_playlist": False,
        "findings": result,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", type=Path, default=PLAYLIST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--offline", action="store_true",
                    help="Metadata-only dry run: no network requests")
    args = ap.parse_args()
    original = args.playlist.read_bytes()
    report = review(original.decode("utf-8-sig"), live=not args.offline)
    report["created_utc"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()
    report["playlist_sha256"] = hashlib.sha256(original).hexdigest()
    if args.playlist.read_bytes() != original:
        raise SystemExit("Playlist changed during read-only audit")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        report, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n", encoding="utf-8")
    print(json.dumps({
        "matched_url_groups": report["matched_url_groups"],
        "reviewed_url_groups": report["reviewed_url_groups"],
        "status_counts": report["status_counts"],
        "modified_playlist": False,
        "no_broadcast_identity_claims": True,
        "report_written": True,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
