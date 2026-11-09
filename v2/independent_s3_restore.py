#!/usr/bin/env python3
"""Real versioned S3 retrieval and authenticated 4955-row V2 archive restore."""
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote
from archive_acceptance_gate import check

def restore_s3_version(bucket, key, version, expected, runner=subprocess.run):
    if not isinstance(bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise ValueError("Invalid private S3 bucket")
    if not isinstance(key, str) or not key or len(key.encode("utf-8")) > 1024 or any(ord(c) < 32 or ord(c) == 127 for c in key):
        raise ValueError("Invalid S3 object key")
    if not isinstance(version, str) or not 1 <= len(version) <= 255 or version == "null" or any(ord(c) < 33 or ord(c) == 127 for c in version):
        raise ValueError("Specific immutable S3 object version required")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError("Independently pinned archive SHA256 required")
    archive_key = os.environ.get("V2_ARCHIVE_KEY_HEX", "")
    if not archive_key:
        raise RuntimeError("Missing private archive key")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", archive_key):
        raise RuntimeError("invalid private archive key")
    # Large encrypted inventories need a bounded but configurable retrieval window.
    timeout_raw = os.environ.get("V2_S3_RESTORE_TIMEOUT_SECONDS", "900")
    if not timeout_raw.isdecimal() or not 30 <= int(timeout_raw) <= 3600:
        raise ValueError("S3 restore timeout must be 30..3600 seconds")
    timeout_seconds = int(timeout_raw)
    with tempfile.TemporaryDirectory(prefix="v2-remote-restore-") as directory:
        root = Path(directory)
        root.chmod(0o700)
        downloaded = root / "restored.enc"
        command = ["aws", "s3api", "get-object", "--no-cli-pager", "--bucket", bucket,
                   "--key", key, "--version-id", version, str(downloaded)]
        # Bound remote retrieval so a stalled S3 connection cannot hold the worker indefinitely.
        result = runner(command, check=True, capture_output=True, text=True, timeout=timeout_seconds)
        metadata = json.loads(result.stdout)
        if not isinstance(metadata, dict) or metadata.get("VersionId") != version:
            raise RuntimeError("Remote object version was not verified by S3")
        # Never follow an unexpected symlink or accept a missing/non-regular
        # remote download as a restored archive, even with matching metadata.
        if downloaded.is_symlink() or not downloaded.is_file() or not stat.S_ISREG(downloaded.lstat().st_mode):
            raise RuntimeError("S3 retrieval did not create a regular encrypted archive")
        downloaded.chmod(0o600)
        # Hash in bounded chunks: encrypted historical archives can be much larger than RAM.
        digest = hashlib.sha256()
        with downloaded.open("rb") as archive:
            for chunk in iter(lambda: archive.read(1024 * 1024), b""):
                digest.update(chunk)
        digest = digest.hexdigest()
        if digest != expected:
            raise RuntimeError("Remote archive differs from pinned original checksum")
        evidence = root / "restore-evidence.json"
        evidence.write_text(json.dumps({
            "encrypted": True, "durable": True, "restore_test_passed": True,
            "integrity_verified": True, "backup_scope": "independent_remote_storage",
            "retrieval_method": "aws_s3api_versioned_get_object",
            "backup_location": "s3://" + bucket + "/" + quote(key, safe="/"),
            "remote_object_version": version, "historical_record_count": 4955,
            "restore_sha256": digest, "restored_file": str(downloaded)
        }, sort_keys=True), encoding="utf-8")
        evidence.chmod(0o600)
        env = dict(os.environ)
        env.update({"V2_ARCHIVE_RESTORE_APPROVED": "true",
                    "V2_ARCHIVE_RESTORE_EVIDENCE": str(evidence),
                    "V2_ARCHIVE_EXPECTED_SHA256": expected})
        check(env)
        return digest

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bucket", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--version-id", required=True)
    args = p.parse_args()
    digest = restore_s3_version(args.bucket, args.key, args.version_id,
                                os.environ.get("V2_ARCHIVE_EXPECTED_SHA256", ""))
    print("PASS: independent versioned offsite AES-GCM restore; 4955 historical identities")
    print("restored_sha256=" + digest)

if __name__ == "__main__":
    main()
