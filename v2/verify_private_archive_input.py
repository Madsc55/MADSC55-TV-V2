#!/usr/bin/env python3
"""Verify private/public V2 candidate inventories before secure archival.

Offline and read-only. Does not print or persist stream URLs. This does not
provide encryption, permanent storage, or restore capability on its own.
"""
import argparse
import hashlib
import json
from pathlib import Path


def verify(private_path, public_path):
    private = json.loads(Path(private_path).read_text(encoding="utf-8"))
    public = json.loads(Path(public_path).read_text(encoding="utf-8"))
    private_rows = private["candidates"]
    public_rows = public["candidates"]
    if public.get("candidates_truncated"):
        raise ValueError("Public inventory is truncated")
    if len(private_rows) != len(public_rows) or len(public_rows) != public["total_unique_candidates"]:
        raise ValueError("Candidate counts differ")

    identities = {}
    for row in private_rows:
        digest = hashlib.sha256(row["url"].encode("utf-8")).hexdigest()
        if digest in identities:
            raise ValueError("Duplicate stream URL identity")
        source_ids = row["source_ids"]
        if not source_ids or len(source_ids) != len(set(source_ids)) or row["source"] not in source_ids:
            raise ValueError("Invalid private source attribution")
        identities[digest] = set(source_ids)

    seen = set()
    for row in public_rows:
        digest = row["url_sha256"]
        if digest in seen or digest not in identities:
            raise ValueError("Public/private URL identity mismatch")
        seen.add(digest)
        if set(row["source_ids"]) != identities[digest]:
            raise ValueError("Public/private source attribution mismatch")
    return len(identities)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private", required=True)
    parser.add_argument("--public", required=True)
    args = parser.parse_args()
    count = verify(args.private, args.public)
    print(f"Verified {count} candidate URL identities and provenance records")


if __name__ == "__main__":
    main()
