#!/usr/bin/env python3
"""Real 4,955-row #60/#72 offline history audit. Never scans or invents URLs."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile

from encrypted_archive import restore
from historical_inventory_guard import (
    SCHEMA_V2, preserve_to_new_archive, reconcile, unpack_archive_snapshot,
    verify_historical_baseline,
)

EXPECTED_FILE_SHA = "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27"
EXPECTED_IDENTITY_SHA = "e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83"
EXPECTED_REGIONS = {"TR": 50, "AZ": 1, "UNKNOWN": 4904}
EXPECTED_EVIDENCE = {"METADATA": 51, "NONE": 4904}
EXPECTED_FIELDS = frozenset({
    "url_sha256", "source", "region_candidate", "classification_evidence",
    "playback_at_run60", "historical_not_reverified",
    "spoken_language_verified", "device_verified",
})


def audit(index):
    content = Path(index).read_bytes()
    if hashlib.sha256(content).hexdigest() != EXPECTED_FILE_SHA:
        raise ValueError("Immutable original #60 history file changed")
    rows = [json.loads(line) for line in content.decode("utf-8").splitlines()]
    if len(rows) != 4955 or any(not isinstance(x, dict) or set(x) != EXPECTED_FIELDS for x in rows):
        raise ValueError("Historical 4955 record count or schema changed")
    if (dict(Counter(x["region_candidate"] for x in rows)) != EXPECTED_REGIONS or
            dict(Counter(x["classification_evidence"] for x in rows)) != EXPECTED_EVIDENCE):
        raise ValueError("Original TR/AZ classification has changed")
    if any(x["playback_at_run60"] != "VIDEO_DECODED" or
           x["historical_not_reverified"] is not True or
           x["device_verified"] is not False or
           x["spoken_language_verified"] is not False or "url" in x for x in rows):
        raise ValueError("Historical playback claim, URL or verification flag changed")
    fingerprint = verify_historical_baseline(rows, rows)
    if fingerprint != EXPECTED_IDENTITY_SHA:
        raise ValueError("Original 4955 SHA identities changed")
    protected, candidates, counts = reconcile(rows, expected_historical_records=4955)
    assert protected == rows and candidates == [], "History lost or URL fabricated"
    for key, expected in (
        ("historical_unique_identities", 4955),
        ("historical_hash_only_identities", 4955),
        ("historical_duplicate_identity_rows", 0),
        ("total_raw_records_preserved", 4955),
        ("unique_candidate_urls", 0),
        ("historical_tr_candidate_records", 50),
        ("historical_az_candidate_records", 1),
        ("historical_unknown_region_records", 4904),
    ):
        if counts[key] != expected:
            raise ValueError("Full history reconciliation failed: " + key)
    with tempfile.TemporaryDirectory() as directory:
        encrypted = Path(directory) / "real-4955.enc"
        prior = os.environ.get("V2_ARCHIVE_KEY_HEX")
        try:
            os.environ["V2_ARCHIVE_KEY_HEX"] = secrets.token_hex(32)
            if not preserve_to_new_archive(encrypted, protected, candidates):
                raise ValueError("AES-GCM archive creation failed")
            blocks = restore(encrypted)
            if blocks[-1].get("guard_schema") != SCHEMA_V2:
                raise ValueError("Missing V2 encrypted completeness manifest")
            historic, added, view = unpack_archive_snapshot(blocks, 4955)
            if added or view or historic != rows:
                raise ValueError("Encrypted restore dropped or changed 4955 actual records")
            verify_historical_baseline(historic, rows)
        finally:
            if prior is None:
                os.environ.pop("V2_ARCHIVE_KEY_HEX", None)
            else:
                os.environ["V2_ARCHIVE_KEY_HEX"] = prior
    return {
        "schema": 1, "evidence": "REAL_ORIGINAL_HASH_ONLY",
        "original_run": 40743765437, "comparison_run": 40948768782,
        "immutable_historical_rows": 4955, "preserved_historical_rows": 4955,
        "distinct_sha256_identities": 4955, "duplicate_identities": 0,
        "region_metadata": EXPECTED_REGIONS,
        "classification_evidence": EXPECTED_EVIDENCE,
        "identity_digest": fingerprint,
        "aes_gcm_v2_complete_restore_verified": True,
        "actual_stream_urls_recovered": 0,
        "device_verified": False,
        "live_channel_scan_performed": False,
        "protected_main_playlist_modified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=Path("v2/history/stage3-4955-hash-only.jsonl"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink() or args.report.resolve() == args.index.resolve():
        parser.error("Refusing overwrite or input/output collision")
    result = audit(args.index)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print("Real 4955 original hash identities, TR/AZ metadata, and AES-GCM restore verified. URLs recovered: 0")


if __name__ == "__main__":
    main()
