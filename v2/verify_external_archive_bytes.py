#!/usr/bin/env python3
"""Read-only verifier for an externally retrieved V2 encrypted archive.

This tool checks bytes and authenticated decryption; it cannot independently
attest where an input file was stored or that a production restore occurred.
"""
import argparse
import json
import os
from pathlib import Path

from ibo_final_acceptance import audit_external_restore


def verify(original: bytes, encrypted: bytes, restored: bytes, passphrase: str):
    if not passphrase:
        raise ValueError("missing archive passphrase")
    report = audit_external_restore(original, encrypted, restored, passphrase)
    # A local verifier cannot attest independent storage provenance.
    report["independent_production_restore_accepted"] = False
    report["storage_provenance_verified"] = False
    report["status"] = "LOCAL_CRYPTOGRAPHIC_VERIFICATION_ONLY"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--external-encrypted", type=Path, required=True)
    parser.add_argument("--external-restored", type=Path, required=True)
    parser.add_argument("--passphrase-env", default="V2_ARCHIVE_PASSPHRASE")
    args = parser.parse_args()
    secret = os.environ.get(args.passphrase_env)
    if not secret:
        parser.error("passphrase environment variable is unset or empty")
    result = verify(args.original.read_bytes(), args.external_encrypted.read_bytes(),
                    args.external_restored.read_bytes(), secret)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
