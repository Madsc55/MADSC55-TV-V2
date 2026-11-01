#!/usr/bin/env python3
"""Authenticated, atomic private inventory backup and verified restore.

Requires cryptography (AES-256-GCM). Key: 32 random bytes, base64 in
V2_ARCHIVE_KEY_B64. Never commit key, plaintext inventory or encrypted
archive to a public repository.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets

MAGIC = b"V2ARCHIVE1\n"
AAD = b"MADSC55-TV-V2/private-inventory/v1"

def key_from_env():
    raw = os.environ.get("V2_ARCHIVE_KEY_B64", "")
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 archive key") from exc
    if len(key) != 32:
        raise ValueError("Archive key must be exactly 32 bytes")
    return key

def atomic_private_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_dir():
        raise ValueError("Output must be a file")
    if path.is_symlink():
        raise ValueError("Refusing symlink output")
    tmp = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

def encrypt(data, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, data, AAD)

def decrypt(data, key):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not data.startswith(MAGIC) or len(data) < len(MAGIC) + 12 + 16:
        raise ValueError("Invalid archive format")
    offset = len(MAGIC)
    return AESGCM(key).decrypt(data[offset:offset+12], data[offset+12:], AAD)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("backup", "restore", "verify"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    key = key_from_env()
    if args.operation != "verify" and args.destination is None:
        parser.error("--destination is required")
    if args.operation == "backup":
        if args.evidence and args.evidence.resolve() == args.source.resolve():
            raise ValueError("Evidence must not overwrite source")
        if args.evidence and args.evidence.resolve() == args.destination.resolve():
            raise ValueError("Evidence must not overwrite archive")
        if args.destination.resolve() == args.source.resolve():
            raise ValueError("Backup output must differ from source")
        plaintext = args.source.read_bytes()
        atomic_private_write(args.destination, encrypt(plaintext, key))
        restored = decrypt(args.destination.read_bytes(), key)
        if restored != plaintext:
            raise RuntimeError("Backup round-trip failed")
        if args.evidence:
            record = {"encrypted": True, "restore_test_passed": True,
                      "integrity_verified": True,
                      "restore_sha256": hashlib.sha256(restored).hexdigest(),
                      "backup_location": str(args.destination),
                      "durable": False}
            atomic_private_write(args.evidence, (json.dumps(record, indent=2)+"\n").encode())
    elif args.operation == "restore":
        if args.destination.resolve() == args.source.resolve():
            raise ValueError("Restore output must differ from source")
        atomic_private_write(args.destination, decrypt(args.source.read_bytes(), key))
    else:
        data = decrypt(args.source.read_bytes(), key)
        print(json.dumps({"integrity_verified": True,
                          "sha256": hashlib.sha256(data).hexdigest(),
                          "bytes": len(data)}))
if __name__ == "__main__":
    main()
