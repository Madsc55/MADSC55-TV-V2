#!/usr/bin/env python3
"""Read-only classification of backup channels from independently collected evidence.

This module never edits playlists, contacts streams, or treats metadata as
proof of spoken language. Run after an independently audited AV/language pass.
"""
from collections import Counter
import json
from pathlib import Path

LANGUAGES = {"TR", "FOREIGN", "UNKNOWN"}
HEALTH = {"WORKING", "NOT_WORKING", "UNKNOWN"}
CATEGORIES = {
    ("TR", "WORKING"): "TURK_WORKING",
    ("TR", "NOT_WORKING"): "TURK_NOT_WORKING",
    ("FOREIGN", "WORKING"): "FOREIGN_WORKING",
    ("FOREIGN", "NOT_WORKING"): "FOREIGN_NOT_WORKING",
}

def classify(row):
    """Require positive evidence; uncertain results must remain UNKNOWN."""
    if not isinstance(row, dict):
        raise ValueError("Invalid evidence row")
    key = row.get("url_sha256")
    if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("Missing or invalid channel identity")
    language = row.get("language", "UNKNOWN")
    health = row.get("health", "UNKNOWN")
    if language not in LANGUAGES or health not in HEALTH:
        raise ValueError("Unsupported evidence state")
    if language != "UNKNOWN" and row.get("language_evidence_verified") is not True:
        language = "UNKNOWN"
    if health == "WORKING" and row.get("decoded_av_verified") is not True:
        health = "UNKNOWN"
    if health == "NOT_WORKING" and (row.get("retries_exhausted") is not True or row.get("terminal_failure_verified") is not True):
        health = "UNKNOWN"
    category = CATEGORIES.get((language, health), "UNCERTAIN")
    return {"url_sha256": key, "language": language, "health": health,
            "category": category, "retry": health == "UNKNOWN",
            "manual_review": language == "UNKNOWN"}

def build_report(rows, expected_count=None):
    if not isinstance(rows, list):
        raise ValueError("Evidence must be a list")
    if expected_count is not None and (not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 1 or len(rows) != expected_count):
        raise ValueError("Incomplete backup inventory")
    if not rows:
        raise ValueError("Empty backup inventory")
    seen = set()
    results = []
    for row in rows:
        result = classify(row)
        if result["url_sha256"] in seen:
            raise ValueError("Duplicate channel identity")
        seen.add(result["url_sha256"])
        results.append(result)
    return {"policy": "READ_ONLY_NO_PLAYLIST_MUTATION",
            "total": len(results),
            "counts": dict(Counter(r["category"] for r in results)),
            "retry_count": sum(r["retry"] for r in results),
            "manual_review_count": sum(r["manual_review"] for r in results),
            "channels": results}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=None)
    args = parser.parse_args()
    if args.expected_count is not None and args.expected_count < 1:
        parser.error("Expected count must be positive")
    if args.evidence.resolve() == args.output.resolve():
        parser.error("Input and output must be different")
    payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("channels"), list):
        parser.error("Expected JSON object with channels array")
    report = build_report(payload["channels"], args.expected_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: an existing report or protected playlist can never be replaced.
    with args.output.open("x", encoding="utf-8") as destination:
        destination.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"total": report["total"], "counts": report["counts"]}))

if __name__ == "__main__":
    main()
