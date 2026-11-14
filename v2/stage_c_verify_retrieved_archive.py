#!/usr/bin/env python3
"""Stage C: verify a separately retrieved encrypted archive, never mutate production lists.

The caller must retrieve the archive from independent private storage first.
A local copy alone is not proof of external durability.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from secure_archive import restore


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify(archive, expected_archive_sha256, expected_restored_sha256, passphrase):
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("Archive must be a regular, independently retrieved file")
    if not isinstance(expected_archive_sha256, str) or len(expected_archive_sha256) != 64:
        raise ValueError("Missing archive SHA256")
    if not isinstance(expected_restored_sha256, str) or len(expected_restored_sha256) != 64:
        raise ValueError("Missing restored SHA256")
    archive_hash = sha256(archive)
    if archive_hash != expected_archive_sha256.lower():
        raise ValueError("Independent archive SHA256 mismatch")
    with tempfile.TemporaryDirectory(prefix="v2-stage-c-restore-") as directory:
        target = Path(directory) / "restored-inventory"
        restore(archive, target, passphrase)
        restored_hash = sha256(target)
        if restored_hash != expected_restored_sha256.lower():
            raise ValueError("Independent restored SHA256 mismatch")
    return {"encrypted": True, "restore_test_passed": True,
            "integrity_verified": True, "archive_sha256": archive_hash,
            "restore_sha256": restored_hash,
            "independent_storage_verified": False,
            "device_playback_verified": False,
            "acceptance": "LOCAL_RETRIEVED_ARCHIVE_CRYPTO_CHECK_ONLY"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieved-archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--restored-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("Evidence output already exists")
    result = verify(args.retrieved_archive, args.archive_sha256, args.restored_sha256,
                    os.environ.get("V2_ARCHIVE_PASSPHRASE", ""))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print("Stage C encrypted archive cryptographic restore: PASS (not external storage/device acceptance)")


if __name__ == "__main__":
    main()
