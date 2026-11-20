#!/usr/bin/env python3
"""Turkish-only authorized stream inventory; offline, no DRM bypass or discovery.

Private JSONL is encrypted using the existing secure_archive module. Never log URLs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from secure_archive import backup, restore

ALLOWED_ACCESS = {"public", "licensed", "subscriber"}
ALLOWED_STATUS = {"accessible", "authorization_required", "unverified"}
MAX_RECORDS = 100000

def validate_record(record):
    if not isinstance(record, dict):
        raise ValueError("Invalid record")
    required = {"channel_id", "country", "language", "url", "access",
                "authorization_evidence", "provenance", "first_seen",
                "last_seen", "status", "version", "decision_history"}
    if not required.issubset(record):
        raise ValueError("Missing required fields")
    if record["country"] not in {"TR", "CY-TR"} and record["language"] != "tr":
        raise ValueError("Non-Turkish stream excluded")
    if record["access"] not in ALLOWED_ACCESS or record["status"] not in ALLOWED_STATUS:
        raise ValueError("Invalid authorization or status")
    if record["access"] != "public" and not record["authorization_evidence"]:
        raise ValueError("Authorization evidence required")
    if not isinstance(record["channel_id"], str) or not record["channel_id"].strip():
        raise ValueError("Invalid channel identity")
    url = record["url"]
    if not isinstance(url, str) or urlsplit(url).scheme not in {"https", "http"} or not urlsplit(url).netloc:
        raise ValueError("Invalid stream URL")
    if not isinstance(record["provenance"], str) or not record["provenance"].strip():
        raise ValueError("Missing provenance")
    if not all(isinstance(record[k], str) and record[k] for k in ("first_seen", "last_seen")):
        raise ValueError("Missing observation history")
    if not isinstance(record["version"], int) or record["version"] < 1:
        raise ValueError("Invalid record version")
    if not isinstance(record["decision_history"], list):
        raise ValueError("Invalid decision history")
    return record

def validate_inventory(raw):
    seen = set()
    count = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        count += 1
        if count > MAX_RECORDS:
            raise ValueError("Inventory too large")
        record = validate_record(json.loads(line))
        key = (record["channel_id"], record["url"])
        if key in seen:
            raise ValueError("Duplicate channel URL")
        seen.add(key)
    return count

def archive_private(source, encrypted, secret):
    source, encrypted = Path(source), Path(encrypted)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Private inventory must be a regular file")
    raw = source.read_bytes()
    count = validate_inventory(raw)
    result = backup(source, encrypted, secret)
    return {"records": count, "encrypted": True,
            "restore_test_passed": result["restore_test_passed"],
            "plaintext_sha256": hashlib.sha256(raw).hexdigest()}

def restore_private(encrypted, destination, secret):
    encrypted, destination = Path(encrypted), Path(destination)
    if encrypted.is_symlink() or not encrypted.is_file():
        raise ValueError("Encrypted archive must be a regular file")
    # Verify plaintext in an isolated temporary directory before publishing it.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="turkish-archive-") as directory:
        staged = Path(directory) / "private.jsonl"
        restore(encrypted, staged, secret)
        count = validate_inventory(staged.read_bytes())
    digest = restore(encrypted, destination, secret)
    return {"records": count, "restored_sha256": digest}

def main():
    parser = argparse.ArgumentParser(description="Offline Turkish authorized archive")
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    secret = os.environ.get("V2_ARCHIVE_PASSPHRASE", "")
    result = (archive_private(args.source, args.destination, secret)
              if args.action == "backup" else
              restore_private(args.source, args.destination, secret))
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
