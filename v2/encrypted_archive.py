#!/usr/bin/env python3
"""Encrypted, append-only discovery archive. Never prints or logs stream URLs.

Requires cryptography (AES-256-GCM) and V2_ARCHIVE_KEY_HEX (64 hex characters).
Each record is independently authenticated with a fresh nonce and a fixed AAD.
Writes are durable via fsync; plaintext is never persisted by this module.
"""
import base64
import hashlib
import json
import os
from pathlib import Path

AAD = b"MADSC55-TV-V2-ARCHIVE-v1"
MAX_RECORD_BYTES = 2_000_000

def _cipher(key_hex=None):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = key_hex if key_hex is not None else os.environ.get("V2_ARCHIVE_KEY_HEX", "")
    if not isinstance(raw, str) or len(raw) != 64:
        raise ValueError("V2_ARCHIVE_KEY_HEX must be 64 hex characters")
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError("Invalid V2_ARCHIVE_KEY_HEX") from exc
    return AESGCM(key)

def append(path, record, key_hex=None):
    cipher = _cipher(key_hex)
    if not isinstance(record, dict):
        raise TypeError("Archive record must be an object")
    plaintext = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(plaintext) > MAX_RECORD_BYTES:
        raise ValueError("Archive record too large")
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, plaintext, AAD)
    item = {"schema": 1, "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii")}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        if os.fstat(fd).st_mode & 0o077:
            raise PermissionError("Archive permissions must be owner-only")
        with os.fdopen(fd, "ab", closefd=False) as stream:
            stream.write((json.dumps(item, separators=(",", ":")) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)

def restore(path, key_hex=None):
    cipher = _cipher(key_hex)
    records = []
    with Path(path).open("rb") as stream:
        for line in stream:
            if len(line) > 3_000_000:
                raise ValueError("Archive line too large")
            item = json.loads(line)
            if item.get("schema") != 1:
                raise ValueError("Unsupported archive record")
            nonce = base64.b64decode(item["nonce"], validate=True)
            data = base64.b64decode(item["ciphertext"], validate=True)
            if len(nonce) != 12:
                raise ValueError("Invalid archive nonce")
            records.append(json.loads(cipher.decrypt(nonce, data, AAD)))
    return records

def archive_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
