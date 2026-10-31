#!/usr/bin/env python3
"""Fail closed before network discovery until durable private archive is approved."""
import json
import hashlib
import re
import os
import stat
from pathlib import Path

def check(env=None):
    env = os.environ if env is None else env
    if env.get("V2_ARCHIVE_RESTORE_APPROVED") != "true":
        raise RuntimeError("Durable encrypted archive restore has not been approved")
    path = env.get("V2_ARCHIVE_RESTORE_EVIDENCE", "")
    if not path:
        raise RuntimeError("Missing independent archive restore evidence path")
    evidence_path = Path(path)
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise RuntimeError("Restore evidence must be a regular non-symlink file")
    if evidence_path.stat().st_mode & 0o077:
        raise RuntimeError("Restore evidence must be owner-only")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    required = ("encrypted", "durable", "restore_test_passed", "integrity_verified")
    if not all(evidence.get(k) is True for k in required):
        raise RuntimeError("Archive evidence missing required passed checks")
    if not evidence.get("backup_location") or not evidence.get("restore_sha256"):
        raise RuntimeError("Archive evidence lacks backup location or restore checksum")
    if not isinstance(evidence["backup_location"], str):
        raise RuntimeError("Backup location must be a string")
    if evidence.get("backup_scope") == "local_separate_directory_not_independent_storage":
        raise RuntimeError("Local backup drill does not establish independent durable backup")
    digest = evidence["restore_sha256"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise RuntimeError("Invalid restore SHA256 digest")
    restored = evidence.get("restored_file")
    if not isinstance(restored, str) or not restored:
        raise RuntimeError("No restored archive file provided for independent integrity check")
    restored_path = Path(restored)
    if restored_path.is_symlink() or not restored_path.is_file():
        raise RuntimeError("Restored archive must be a regular non-symlink file")
    if restored_path.stat().st_mode & 0o077:
        raise RuntimeError("Restored archive must be owner-only")
    actual = hashlib.sha256(restored_path.read_bytes()).hexdigest()
    if actual != digest:
        raise RuntimeError("Restored archive integrity mismatch")
    return True

if __name__ == "__main__":
    check()
    print("Encrypted durable archive acceptance: PASS")
