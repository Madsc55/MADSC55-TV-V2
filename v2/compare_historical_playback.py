#!/usr/bin/env python3
"""Read-only comparison of historical playback aggregates. Never publishes channels."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not data.get("coverage_complete") or data.get("unique_tested") != len(data["channel_results"]):
        raise ValueError("Incomplete or inconsistent historical aggregate: " + path)
    by_hash = {}
    for item in data["channel_results"]:
        key = item.get("url_sha256")
        if not isinstance(key, str) or len(key) != 64:
            raise ValueError("Missing hashed stream identity")
        if key in by_hash:
            raise ValueError("Duplicate hashed stream identity")
        by_hash[key] = item
    return data, by_hash

def decoded(item):
    return item.get("status") == "VIDEO_DECODED" or item.get("video_decoded") is True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    old, a = load(args.old)
    new, b = load(args.new)
    missing = [a[k] for k in sorted(a.keys() - b.keys())]
    recovered = [x for x in missing if decoded(x)]
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    fields = ["url_sha256", "source", "name", "status", "width", "height"]
    with (output / "historical-decoded-not-retested.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({k: item.get(k, "") for k in fields} for item in recovered)
    summary = {
        "policy": "HISTORICAL_EVIDENCE_ONLY_NO_LIVE_RETEST_NO_AUTOPUBLISH",
        "old_tested": len(a), "new_tested": len(b),
        "overlap": len(a.keys() & b.keys()),
        "old_only": len(missing), "new_only": len(b.keys() - a.keys()),
        "old_decoded_not_retested": len(recovered),
        "old_only_by_source": dict(Counter(x.get("source", "") for x in missing).most_common()),
        "warning": "Old decoded is not evidence of current availability, Turkish language, or channel identity."
    }
    (output / "historical-comparison.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k != "old_only_by_source"}, ensure_ascii=False))
    if not recovered:
        raise SystemExit("No historical decoded candidates recovered; check status schema")

if __name__ == "__main__":
    main()
