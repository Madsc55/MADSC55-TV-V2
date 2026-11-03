#!/usr/bin/env python3
"""Encrypt exact recovered stream URLs to a session's public RSA key.

Only the private key holder can open the result. Public GitHub artifacts are
NEVER allowed to include raw IPTV URL strings or access-token-bearing records.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import zlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AAD = b"MADSC55-TV-V2-STAGE3-RECOVERED-URL-TRANSIT-v1"


def seal_rows(rows, public_key_path, output_path):
    rows = list(rows)
    if len(rows) > 4955:
        raise ValueError("Too many recovered streams for 4955 historical identity baseline")
    hashes_seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Expected stream metadata objects")
        url = row.get("url")
        sha = row.get("url_sha256")
        if (not isinstance(url, str) or
                not isinstance(sha, str) or
                hashlib.sha256(url.encode("utf-8")).hexdigest() != sha or
                sha in hashes_seen):
            raise ValueError("Recovered stream URL does not match its immutable SHA256")
        hashes_seen.add(sha)
    out = Path(output_path)
    if out.exists() or out.is_symlink() or out.suffix != ".sealed":
        raise ValueError("Refusing unsafe sealed evidence destination")
    public = serialization.load_pem_public_key(Path(public_key_path).read_bytes())
    if not isinstance(public, rsa.RSAPublicKey) or public.key_size < 3072:
        raise ValueError("Recovery transport requires RSA-3072 or stronger")
    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    packed = zlib.compress(json.dumps(
        {"schema": 1, "records": rows}, ensure_ascii=False,
        separators=(",", ":")).encode("utf-8"), level=9)
    ciphertext = AESGCM(key).encrypt(nonce, packed, AAD)
    wrapped = public.encrypt(
        key, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                          algorithm=hashes.SHA256(), label=None))
    item = {"schema": 1, "kind": "RSA_OAEP_SHA256_AES256_GCM_ZLIB",
            "records_encrypted": len(rows),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "wrapped_key": base64.b64encode(wrapped).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii")}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(item, stream, separators=(",", ":"))
        stream.write("\n")
    os.chmod(out, 0o600)
    return len(rows)


def open_rows(sealed_path, private_key_path):
    private = serialization.load_pem_private_key(
        Path(private_key_path).read_bytes(), password=None)
    item = json.loads(Path(sealed_path).read_text(encoding="utf-8"))
    if item.get("schema") != 1 or item.get("kind") != "RSA_OAEP_SHA256_AES256_GCM_ZLIB":
        raise ValueError("Unsupported encrypted recovery transit envelope")
    key = private.decrypt(
        base64.b64decode(item["wrapped_key"], validate=True),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None))
    packed = AESGCM(key).decrypt(
        base64.b64decode(item["nonce"], validate=True),
        base64.b64decode(item["ciphertext"], validate=True), AAD)
    data = json.loads(zlib.decompress(packed))
    rows = data["records"]
    if len(rows) != item["records_encrypted"]:
        raise ValueError("Recovered row count mismatch")
    return rows
