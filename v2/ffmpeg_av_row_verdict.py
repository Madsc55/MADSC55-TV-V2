#!/usr/bin/env python3
"""Fail-closed per-row AV evidence classification. No network or playlist writes."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

STATES = ("AV_DECODED", "VIDEO_ONLY", "AUDIO_ONLY", "DECODE_ERROR",
          "TIMEOUT_OR_RATE_LIMIT", "UNSAFE_OR_UNSUPPORTED_TRANSPORT",
          "HASH_ONLY_HISTORICAL", "NOT_IN_REPORT", "PENDING_RETRY")

def classify(row):
    if not isinstance(row, dict):
        raise ValueError("row must be an object")
    if row.get("confirmed_failed") is True:
        raise ValueError("cannot confirm failure from a single historical AV row")
    a, v = row.get("audio_decoded"), row.get("video_decoded")
    if a is True and v is True:
        return "AV_DECODED"
    if a is True and v is False:
        return "AUDIO_ONLY"
    if v is True and a is False:
        return "VIDEO_ONLY"
    if a not in (True, False, None) or v not in (True, False, None):
        raise ValueError("decode flags must be booleans or null")
    reason = row.get("reason")
    mapping = {
        "decode_error": "DECODE_ERROR",
        "timeout": "TIMEOUT_OR_RATE_LIMIT",
        "rate_limit": "TIMEOUT_OR_RATE_LIMIT",
        "http_403": "TIMEOUT_OR_RATE_LIMIT",
        "http_429": "TIMEOUT_OR_RATE_LIMIT",
        "unsafe_transport": "UNSAFE_OR_UNSUPPORTED_TRANSPORT",
        "unsupported_hls_dash": "UNSAFE_OR_UNSUPPORTED_TRANSPORT",
        "hash_only": "HASH_ONLY_HISTORICAL",
        "not_in_report": "NOT_IN_REPORT",
        "recheck_required": "PENDING_RETRY",
    }
    if reason not in mapping:
        raise ValueError("unrecognized or missing evidence reason")
    if a is True or v is True:
        raise ValueError("partial decode evidence must not be overwritten by reason")
    return mapping[reason]

def summarize(rows, expected=None):
    counts = collections.Counter()
    seen = set()
    for row in rows:
        identity = row.get("channel_sha256")
        if not isinstance(identity, str) or len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
            raise ValueError("invalid immutable channel identity")
        if identity in seen:
            raise ValueError("duplicate immutable channel identity")
        seen.add(identity)
        counts[classify(row)] += 1
    if expected is not None and len(seen) != expected:
        raise ValueError("evidence row count mismatch")
    return {"total": len(seen), "counts": {k: counts[k] for k in STATES},
            "confirmed_failed": 0, "playlist_written": False,
            "live_test_performed": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--expected", type=int, default=None)
    p.add_argument("--sha256", required=True, help="SHA256 of immutable source JSONL bytes")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    raw = args.input.read_bytes()
    if len(raw) > 64 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != args.sha256:
        p.error("source too large or SHA256 mismatch")
    if args.output.exists() or args.output.is_symlink():
        p.error("output already exists")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    result = summarize(rows, expected=args.expected)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
