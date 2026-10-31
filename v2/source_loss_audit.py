#!/usr/bin/env python3
"""Offline source-coverage regression comparison; never accesses stream URLs."""
import argparse
import json
from pathlib import Path

def index(report):
    result = {}
    for item in report.get("source_audit", []):
        source = item.get("source")
        if not source or source in result:
            raise ValueError("Missing or duplicate source identifier")
        result[source] = item
    return result

def compare(previous, current, threshold=0.5):
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    old, new = index(previous), index(current)
    findings = []
    for source, before in sorted(old.items()):
        after = new.get(source)
        prior = before.get("distinct_stream_urls", before.get("entries", 0))
        if after is None:
            findings.append({"source": source, "reason": "SOURCE_MISSING", "previous": prior, "current": None})
            continue
        if after.get("status") == "FETCH_FAILED":
            findings.append({"source": source, "reason": "FETCH_FAILED", "previous": prior, "current": None})
            continue
        now = after.get("distinct_stream_urls", after.get("entries", 0))
        if not isinstance(prior, int) or not isinstance(now, int) or min(prior, now) < 0:
            raise ValueError("Invalid source count")
        if prior and now < prior * threshold:
            findings.append({"source": source, "reason": "SOURCE_DROP", "previous": prior, "current": now})
    return {"previous_sources": len(old), "current_sources": len(new), "findings": findings,
            "status": "REVIEW_REQUIRED" if findings else "NO_LARGE_REGRESSION"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    result = compare(json.loads(args.previous.read_text()), json.loads(args.current.read_text()), args.threshold)
    print(json.dumps(result, indent=2))
    if result["findings"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
