#!/usr/bin/env python3
"""Read-only, no-secret structural audit for existing Drive legacy encrypted backups.

Never decrypts, prints ciphertext, or modifies the input. A structural PASS is
NOT evidence of authenticated decryption or successful restoration.
"""
import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path

STAGE4_FIELDS = {"schema", "nonce", "ciphertext"}
PRODUCTION_MAGIC = b"MADSC55-TV-V2-REAL-4955-PLUS-107-ARCHIVE-v1\n"
MAX_BYTES = 512 * 1024 * 1024


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def audit(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("source must be a regular non-symlink file")
    size = path.stat().st_size
    if not 0 < size <= MAX_BYTES:
        raise ValueError("invalid archive size")
    data = path.read_bytes()
    result = {"bytes": size, "sha256": hashlib.sha256(data).hexdigest(),
              "structural_pass": False, "restore_verified": False}
    if data.startswith(PRODUCTION_MAGIC):
        # Only the format marker is known; do not guess encryption parameters.
        if len(data) <= len(PRODUCTION_MAGIC) + 16:
            raise ValueError("truncated production archive")
        result.update(format="production-v1", structural_pass=True,
                      note="header and nonempty payload only; authentication unverified")
        return result
    if not data.startswith(b'{"schema":'):
        raise ValueError("unrecognized legacy encrypted archive format")
    nonces = set()
    count = 0
    for line in data.splitlines():
        if not line:
            raise ValueError("empty record")
        try:
            obj = json.loads(line, object_pairs_hook=_unique_pairs)
            if type(obj) is not dict or set(obj) != STAGE4_FIELDS or type(obj["schema"]) is not int or obj["schema"] != 1:
                raise ValueError("invalid record schema")
            if type(obj["nonce"]) is not str or type(obj["ciphertext"]) is not str:
                raise ValueError("invalid record types")
            nonce = base64.b64decode(obj["nonce"], validate=True)
            cipher = base64.b64decode(obj["ciphertext"], validate=True)
        except (UnicodeError, json.JSONDecodeError, binascii.Error) as exc:
            raise ValueError("invalid encrypted record encoding") from exc
        if len(nonce) != 12 or len(cipher) < 16:
            raise ValueError("invalid nonce or ciphertext size")
        if nonce in nonces:
            raise ValueError("reused nonce")
        nonces.add(nonce)
        count += 1
    result.update(format="stage4-jsonl-v1", records=count,
                  unique_nonces=len(nonces), structural_pass=True,
                  note="ciphertext authentication and restore unverified")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.archive), sort_keys=True))


if __name__ == "__main__":
    main()
