#!/usr/bin/env python3
"""Offline cryptographic acceptance for an externally retrieved Turkish vault copy.

The caller MUST authenticate the provider download separately. This program
verifies exact encrypted-byte identity and isolated decrypted-content parity;
it never connects to Drive or exposes stream URLs, channel IDs, or the key.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from v2.turk_authorized_vault import Vault, _private_bytes

_HASH = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def verify_retrieved_vault(source, downloaded_copy, expected_sha256, key):
    """Verify two distinct private files and independently restore the copy.

    Expected SHA must be pinned outside this function (e.g., authenticated
    provider metadata or independent source receipt), never derived from the
    untrusted downloaded file alone.
    """
    if not isinstance(expected_sha256, str) or not _HASH.fullmatch(expected_sha256):
        raise ValueError("Expected encrypted SHA-256 must be a 64-character hex digest")
    if not key:
        raise ValueError("Authorized vault decryption key is unavailable")
    source, downloaded_copy = Path(source), Path(downloaded_copy)
    if source.samefile(downloaded_copy):
        raise ValueError("Source and downloaded copy must be different files")
    raw = _private_bytes(source)
    backup = _private_bytes(downloaded_copy)
    if raw is None or backup is None:
        raise ValueError("Source and downloaded copy must both exist")
    source_sha = hashlib.sha256(raw).hexdigest()
    backup_sha = hashlib.sha256(backup).hexdigest()
    if source_sha != expected_sha256 or backup_sha != expected_sha256 or raw != backup:
        raise ValueError("Encrypted source/external copy identity mismatch")

    reader = Vault(source, key)
    original_doc = reader._decode(raw)
    with tempfile.TemporaryDirectory(prefix="madsc55-vault-acceptance-") as directory:
        isolated_path = Path(directory) / "restored-private.enc"
        recovered = Vault(isolated_path, key)
        recovered.restore(downloaded_copy, expected_sha256)
        restored_doc = recovered.read()
        if restored_doc != original_doc:
            raise ValueError("Decrypted vault contents or decision history changed")
        if isolated_path.stat().st_mode & 0o777 != 0o600:
            raise ValueError("Isolated restored vault does not have private permissions")

    # No URLs, channel IDs, tokens, credentials or decrypted records in output.
    return {
        "schema_version": 1,
        "vault_type": "AUTHORIZED_TURKISH_FERNET",
        "encrypted_bytes_sha256": expected_sha256,
        "encrypted_source_and_copy_byte_identical": True,
        "isolated_restore_contents_identical": True,
        "isolated_restore_private_permissions": True,
        "restored_entry_count": len(original_doc["entries"]),
        "network_requests": 0,
        "raw_urls_in_report": False,
        "decryption_key_in_report": False,
        # A local file path is NOT an authenticated provider receipt.
        "external_provider_identity_verified_by_this_tool": False,
        "full_external_acceptance": False,
        "status": "CRYPTOGRAPHIC_LOCAL_RESTORE_ONLY",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--retrieved-copy", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify_retrieved_vault(
            args.source, args.retrieved_copy, args.expected_sha256,
            os.environ.get("V2_AUTHORIZED_VAULT_FERNET_KEY"))
    except Exception:
        raise SystemExit(
            "Private vault acceptance failed; no encrypted data, URLs or secrets disclosed"
        ) from None
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
