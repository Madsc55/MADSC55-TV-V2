#!/usr/bin/env python3
"""Offline source-coverage regression comparison; never accesses stream URLs."""
import argparse
import json
import re
from pathlib import Path

def index(report):
    if not isinstance(report, dict) or not isinstance(report.get("source_audit", []), list):
        raise ValueError("Malformed source audit report")
    result = {}
    for item in report.get("source_audit", []):
        if not isinstance(item, dict):
            raise ValueError("Malformed source audit record")
        source = item.get("source")
        if not isinstance(source, str) or not source.strip() or source in result:
            raise ValueError("Missing or duplicate source identifier")
        result[source] = item
    return result

def candidate_hashes(report):
    """Return candidate SHA256 identities only when the report contains a full candidate list.

    A missing or explicitly truncated list cannot prove historical URL survival.
    """
    if "candidates" not in report or report.get("candidates_truncated"):
        return None
    records = report["candidates"]
    if not isinstance(records, list):
        raise ValueError("Invalid candidate list")
    result = set()
    for row in records:
        if not isinstance(row, dict) or not re.fullmatch(
                r"[0-9a-f]{64}", str(row.get("url_sha256", ""))):
            raise ValueError("Invalid candidate SHA256")
        if row["url_sha256"] in result:
            raise ValueError("Duplicate candidate SHA256")
        result.add(row["url_sha256"])
    return result


def compare(previous, current, threshold=0.5):
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    old, new = index(previous), index(current)
    findings = []
    for source_map in (old, new):
        for item in source_map.values():
            if item.get("status") == "FETCH_FAILED":
                continue
            count = item.get("distinct_stream_urls", item.get("entries", 0))
            if type(count) is not int or count < 0:
                raise ValueError("Invalid source count")
    if not old or not new:
        return {"previous_sources": len(old), "current_sources": len(new),
                "findings": [{"reason": "MISSING_SOURCE_AUDIT", "previous": len(old), "current": len(new)}],
                "status": "REVIEW_REQUIRED"}
    for source, before in sorted(old.items()):
        prior = before.get("distinct_stream_urls", before.get("entries", 0))
        if type(prior) is not int or prior < 0:
            raise ValueError("Invalid previous source count")
        after = new.get(source)
        if after is None:
            findings.append({"source": source, "reason": "SOURCE_MISSING", "previous": prior, "current": None})
            continue
        if after.get("status") == "FETCH_FAILED":
            findings.append({"source": source, "reason": "FETCH_FAILED", "previous": prior, "current": None})
            continue
        now = after.get("distinct_stream_urls", after.get("entries", 0))
        if type(now) is not int or now < 0:
            raise ValueError("Invalid source count")
        if prior and now < prior * threshold:
            findings.append({"source": source, "reason": "SOURCE_DROP", "previous": prior, "current": now})
    previous_hashes = candidate_hashes(previous)
    current_hashes = candidate_hashes(current)
    candidate_audit = {"status": "NOT_COMPARABLE",
                       "reason": "CANDIDATE_DATA_MISSING_OR_TRUNCATED"}
    if previous_hashes is not None and current_hashes is not None:
        missing = previous_hashes - current_hashes
        candidate_audit = {
            "status": "REVIEW_REQUIRED" if missing else "NO_CANDIDATE_LOSS",
            "previous_unique": len(previous_hashes),
            "current_unique": len(current_hashes),
            "same_identities": len(previous_hashes & current_hashes),
            "absent_from_current_candidates": len(missing),
            "new_candidate_identities": len(current_hashes - previous_hashes),
            "absent_sha256_full": sorted(missing),
            "absent_sha256_sample": sorted(missing)[:100],
            "note": "Absent from current discovery is not proof of a dead stream; a channel may move to the live playlist.",
        }
        if missing:
            findings.append({"reason": "HISTORICAL_CANDIDATES_ABSENT",
                             "previous": len(previous_hashes),
                             "current": len(current_hashes),
                             "missing": len(missing)})
    return {"previous_sources": len(old), "current_sources": len(new),
            "candidate_audit": candidate_audit, "findings": findings,
            "status": ("REVIEW_REQUIRED" if findings else
                       "SOURCE_COUNTS_OK_CANDIDATE_PROOF_MISSING" if
                       candidate_audit["status"] == "NOT_COMPARABLE" else
                       "NO_LARGE_REGRESSION")}

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
