#!/usr/bin/env python3
"""Fail closed before network discovery until durable private archive is approved."""
import json
import os
from pathlib import Path

def check(env=None):
    env = os.environ if env is None else env
    if env.get("V2_ARCHIVE_RESTORE_APPROVED") != "true":
        raise RuntimeError("Durable encrypted archive restore has not been approved")
    path = env.get("V2_ARCHIVE_RESTORE_EVIDENCE", "")
    if not path:
        raise RuntimeError("Missing independent archive restore evidence path")
    evidence = json.loads(Path(path).read_text(encoding="utf-8"))
    required = ("encrypted", "durable", "restore_test_passed", "integrity_verified")
    if not all(evidence.get(k) is True for k in required):
        raise RuntimeError("Archive evidence missing required passed checks")
    if not evidence.get("backup_location") or not evidence.get("restore_sha256"):
        raise RuntimeError("Archive evidence lacks backup location or restore checksum")
    return True

if __name__ == "__main__":
    check()
    print("Encrypted durable archive acceptance: PASS")
