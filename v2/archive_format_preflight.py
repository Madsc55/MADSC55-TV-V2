#!/usr/bin/env python3
"""Read-only archive format preflight. Never decrypts, writes or logs ciphertext."""
import argparse
import json
from pathlib import Path

MAGIC = b"MADSC55-V2-ARCHIVE\x01"
MAX_LINE = 16 * 1024 * 1024


def inspect(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Archive must be a regular file")
    with path.open("rb") as source:
        if source.read(len(MAGIC)) == MAGIC:
            return {"format": "v2-binary-aesgcm", "compatible_with_secure_archive": True}
        source.seek(0)
        count = 0
        for line in source:
            if not line.strip() or len(line) > MAX_LINE:
                raise ValueError("Unknown archive format")
            try:
                record = json.loads(line)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("Unknown archive format") from exc
            if (not isinstance(record, dict) or record.get("schema") != 1
                    or set(record) != {"schema", "nonce", "ciphertext"}
                    or not isinstance(record["nonce"], str)
                    or not isinstance(record["ciphertext"], str)):
                raise ValueError("Unknown archive format")
            count += 1
        if not count:
            raise ValueError("Empty archive")
        return {"format": "legacy-jsonl-encrypted", "records": count,
                "compatible_with_secure_archive": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.archive), sort_keys=True))
    # A legacy archive must not be passed to the incompatible binary restore path.
    if not inspect(args.archive)["compatible_with_secure_archive"]:
        parser.exit(2, "Legacy encrypted archive requires its original verified decryptor; no restore attempted.\n")


if __name__ == "__main__":
    main()
