#!/usr/bin/env python3
"""Production archive gate: cryptographic restore plus immutable #60 history.

This offline verifier cannot itself prove remote retrieval. Production evidence
must be created by independent_s3_restore.py after its versioned S3 download.
"""
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlsplit
from encrypted_archive import restore
from historical_inventory_guard import SCHEMA_V2, identity, unpack_archive_snapshot, verify_historical_baseline
from historical_url_recovery import validate_url

BASELINE = Path(__file__).resolve().parent / "history/stage3-4955-hash-only.jsonl"
EXPECTED_HISTORY = 4955
# Pin the complete historical metadata, not just its URL identity multiset.
# Git blob SHA1 includes the byte length and content of the immutable baseline.
BASELINE_GIT_BLOB_SHA1 = "c91c94a3f19097dec2855105da26d8b9a8329f8b"
EXPECTED_HASH = "e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83"

def private_file(value, label):
    if not isinstance(value, str) or not value:
        raise RuntimeError("Missing " + label)
    path = Path(value)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(label + " must be a regular non-symlink file")
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o077:
        raise RuntimeError(label + " must be owner-only")
    return path

def checksum(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def check(env=None):
    env = os.environ if env is None else env
    if env.get("V2_ARCHIVE_RESTORE_APPROVED") != "true":
        raise RuntimeError("Durable encrypted archive restore has not been approved")
    evidence_file = private_file(env.get("V2_ARCHIVE_RESTORE_EVIDENCE"), "Restore evidence")
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise RuntimeError("Invalid restore evidence")
    if not all(evidence.get(k) is True for k in
               ("encrypted", "durable", "restore_test_passed", "integrity_verified")):
        raise RuntimeError("Archive evidence missing required passed checks")
    if evidence.get("backup_scope") != "independent_remote_storage":
        raise RuntimeError("Local copy or expiring CI artifact is not an independent durable backup")
    if evidence.get("retrieval_method") != "aws_s3api_versioned_get_object":
        raise RuntimeError("No verified versioned remote retrieval method")
    location = evidence.get("backup_location")
    if not isinstance(location, str):
        raise RuntimeError("Missing remote backup location")
    uri = urlsplit(location)
    if (uri.scheme != "s3" or not uri.hostname or uri.username or uri.password
            or uri.path in ("", "/") or uri.query or uri.fragment or uri.port is not None):
        raise RuntimeError("Independent backup must be a versioned S3 object URI")
    version = evidence.get("remote_object_version")
    if (not isinstance(version, str) or not 1 <= len(version) <= 255 or
            version == "null" or any(ord(c) < 33 or ord(c) == 127 for c in version)):
        raise RuntimeError("Missing immutable remote object version")
    if evidence.get("historical_record_count") != EXPECTED_HISTORY:
        raise RuntimeError("Evidence does not cover all 4955 historical identities")

    expected = env.get("V2_ARCHIVE_EXPECTED_SHA256")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise RuntimeError("Missing independently pinned original archive checksum")
    if evidence.get("restore_sha256") != expected:
        raise RuntimeError("Restore evidence differs from pinned checksum")
    restored = private_file(evidence.get("restored_file"), "Restored archive")
    if checksum(restored) != expected:
        raise RuntimeError("Restored archive integrity mismatch")
    try:
        blocks = restore(restored, key_hex=env.get("V2_ARCHIVE_KEY_HEX"))
    except Exception as exc:
        raise RuntimeError("AES-GCM archive authentication/decryption failed") from exc
    if (not blocks or not isinstance(blocks[-1], dict)
            or blocks[-1].get("kind") != "archive_manifest"
            or blocks[-1].get("guard_schema") != SCHEMA_V2):
        raise RuntimeError("Authenticated V2 archive manifest missing")
    try:
        historical, newer, candidates = unpack_archive_snapshot(blocks, EXPECTED_HISTORY)
        baseline_bytes = BASELINE.read_bytes()
        blob = b"blob " + str(len(baseline_bytes)).encode("ascii") + b"\0" + baseline_bytes
        if hashlib.sha1(blob).hexdigest() != BASELINE_GIT_BLOB_SHA1:
            raise ValueError("Immutable historical baseline content changed")
        baseline = [json.loads(line) for line in baseline_bytes.decode(
            "utf-8").splitlines() if line]
        result = verify_historical_baseline(historical, baseline)
    except Exception as exc:
        raise RuntimeError("Encrypted restore lost historical identities or metadata") from exc
    if result != EXPECTED_HASH or not isinstance(newer, list) or not isinstance(candidates, list):
        raise RuntimeError("Restored historical inventory differs from immutable baseline")
    # A valid manifest authenticates what was stored, not whether the candidate
    # view actually came from the archived raw rows. Never accept a fabricated
    # URL candidate that cannot be traced to its exact original URL digest.
    raw_url_ids = {identity(row) for row in historical + newer
                   if validate_url(row.get("url"))}
    candidate_ids = [identity(row) for row in candidates]
    if (None in candidate_ids or len(candidate_ids) != len(set(candidate_ids))
            or not set(candidate_ids).issubset(raw_url_ids)):
        raise RuntimeError("Encrypted candidate view lacks raw URL provenance")
    return True

if __name__ == "__main__":
    check()
    print("PASS: authenticated V2 archive restore and complete 4955 identity baseline")
