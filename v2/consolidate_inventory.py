#!/usr/bin/env python3
"""Offline, lossless consolidation of real V2 candidate JSONL inventories.

No network requests, playlist edits or synthetic channel records. Input files
must be real JSONL records from prior scans. Output is encrypted with the V2
archive format and verified by decrypting it before reporting success.
"""
import argparse
import hashlib
import json
import os
import io
from pathlib import Path
from urllib.parse import urlsplit
from secure_archive import encrypt, decrypt, atomic_write

def valid_url(url):
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    return parsed.scheme in ("http", "https") and bool(parsed.hostname) and not parsed.username and not parsed.password

def merge_records(paths, encrypted_paths=(), passphrase=None):
    merged = {}
    counts = {}
    for path in list(paths) + list(encrypted_paths):
        count = 0
        if path in encrypted_paths:
            stream = io.StringIO(decrypt(path.read_bytes(), passphrase).decode("utf-8-sig"))
        else:
            stream = open(path, encoding="utf-8-sig")
        with stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{number}: invalid JSON") from exc
                if not isinstance(record, dict) or not valid_url(record.get("url")):
                    raise ValueError(f"{path}:{number}: invalid candidate URL")
                url = record["url"]
                if url not in merged:
                    merged[url] = dict(record)
                    merged[url]["source_ids"] = []
                    merged[url]["observations"] = []
                target = merged[url]
                sources = record.get("source_ids", [])
                if not isinstance(sources, list):
                    raise ValueError(f"{path}:{number}: source_ids must be a list")
                for source in sources:
                    if isinstance(source, str) and source and source not in target["source_ids"]:
                        target["source_ids"].append(source)
                # Never replace a known value with a blank field.
                for field in ("name", "group", "tvg_id", "logo", "country", "language"):
                    if not target.get(field) and record.get(field):
                        target[field] = record[field]
                target["observations"].append({
                    "input": path.name,
                    "status": record.get("http_hls_status", record.get("status", "UNVERIFIED")),
                    "ibo_device_tested": record.get("ibo_device_tested", False),
                })
                count += 1
        counts[path.name] = count
    return merged, counts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", default=[],\n                        help="Plaintext real candidate JSONL; repeat for multiple inputs")
    parser.add_argument("--encrypted-input", type=Path, action="append", default=[],\n                        help="Previously encrypted V2 JSONL inventory")
    parser.add_argument("--encrypted-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    secret = os.environ.get("V2_ARCHIVE_PASSPHRASE", "")
    if len(secret) < 16:
        parser.error("V2_ARCHIVE_PASSPHRASE must contain at least 16 characters")
    if args.encrypted_output.resolve() == args.report.resolve():
        parser.error("Archive and report paths must differ")
    if not (args.input or args.encrypted_input):\n        parser.error("At least one --input or --encrypted-input is required")\n    if args.encrypted_output in args.input + args.encrypted_input:\n        parser.error("Refusing to overwrite an input archive")\n    if not all(path.is_file() for path in args.input + args.encrypted_input):
        parser.error("Every input JSONL file must exist")
    records, counts = merge_records(args.input, args.encrypted_input, secret)
    if not records:
        parser.error("No real candidates found; refusing empty archive")
    raw = "".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"
                  for value in records.values()).encode("utf-8")
    blob = encrypt(raw, secret)
    if decrypt(blob, secret) != raw:
        raise RuntimeError("Archive restoration check failed")
    atomic_write(args.encrypted_output, blob)
    if decrypt(args.encrypted_output.read_bytes(), secret) != raw:
        raise RuntimeError("On-disk archive restoration check failed")
    report = {
        "status": "OFFLINE_ARCHIVE_VERIFIED",
        "inputs": counts,
        "unique_urls": len(records),
        "observations_preserved": sum(len(x["observations"]) for x in records.values()),
        "archive_sha256": hashlib.sha256(blob).hexdigest(),
        "restore_test_passed": True,
        "network_scan_performed": False,
        "protected_playlist_modified": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
