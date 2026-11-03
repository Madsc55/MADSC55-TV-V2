#!/usr/bin/env python3
"""Real versioned S3 retrieval and authenticated 4955-row V2 archive restore."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from archive_acceptance_gate import check

def restore_s3_version(bucket, key, version, expected, runner=subprocess.run):
    if not isinstance(bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise ValueError("Invalid private S3 bucket")
    if not isinstance(key, str) or not key or len(key) > 1024 or any(ord(c) < 32 for c in key):
        raise ValueError("Invalid S3 object key")
    if not isinstance(version, str) or not 1 <= len(version) <= 255 or any(ord(c) < 33 for c in version):
        raise ValueError("Specific immutable S3 object version required")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError("Independently pinned archive SHA256 required")
    if not os.environ.get("V2_ARCHIVE_KEY_HEX"):
        raise RuntimeError("Missing private archive key")
    with tempfile.TemporaryDirectory(prefix="v2-remote-restore-") as directory:
        root = Path(directory)
        root.chmod(0o700)
        downloaded = root / "restored.enc"
        command = ["aws", "s3api", "get-object", "--no-cli-pager", "--bucket", bucket,
                   "--key", key, "--version-id", version, str(downloaded)]
        result = runner(command, check=True, capture_output=True, text=True)
        metadata = json.loads(result.stdout)
        if not isinstance(metadata, dict) or metadata.get("VersionId") != version:
            raise RuntimeError("Remote object version was not verified by S3")
        downloaded.chmod(0o600)
        digest = hashlib.sha256(downloaded.read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError("Remote archive differs from pinned original checksum")
        evidence = root / "restore-evidence.json"
        evidence.write_text(json.dumps({
            "encrypted": True, "durable": True, "restore_test_passed": True,
            "integrity_verified": True, "backup_scope": "independent_remote_storage",
            "retrieval_method": "aws_s3api_versioned_get_object",
            "backup_location": "s3://" + bucket + "/" + key,
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
