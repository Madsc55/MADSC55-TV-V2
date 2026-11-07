#!/usr/bin/env python3
"""Derive a stable, domain-separated AES-256 key for *new* V2 live archives.

Does not decrypt or re-key historical Stage 5 production archives.
Never print secret material.
"""
import hashlib
import re

SALT = b"MADSC55-TV-V2-LIVE-MASTER-ARCHIVE-KEY-v1"

def resolve_key(hex_secret, passphrase):
    if re.fullmatch(r"[0-9a-fA-F]{64}", hex_secret or ""):
        return hex_secret.lower(), "hex"
    if not isinstance(passphrase, str) or len(passphrase.encode("utf-8")) < 16 or not passphrase.strip():
        raise ValueError("Missing usable archive secret: provide 64 hex chars or a passphrase of at least 16 UTF-8 bytes")
    # Fixed domain separation makes the same passphrase yield a stable key across
    # ephemeral Actions runners. scrypt raises the cost of offline guessing.
    derived = hashlib.scrypt(passphrase.encode("utf-8"), salt=SALT, n=2**14, r=8, p=1, dklen=32)
    return derived.hex(), "passphrase-scrypt-v1"
