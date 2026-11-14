#!/usr/bin/env python3
"""Independent Stage B package acceptance gate; read-only, fails closed.

Usage: V2_ARCHIVE_PASSPHRASE=... python v2/verify_ibo_package_evidence.py evidence.zip
Never prints URLs, decrypted inventory, or the secret.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from export_ibo_batches import render, valid_stream_url
from secure_archive import decrypt

PATTERN = re.compile(r"IBO_AV_VERIFIED_(1000|2000)_PART([1-9][0-9]*)\.m3u8$")


def verify(path, secret):
    errors = []
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC failure")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entry names")
        if "ibo-candidate-inventory.jsonl.enc" not in names:
            raise ValueError("Missing encrypted inventory")
        if "ibo-real-scan-report.json" not in names:
            raise ValueError("Missing scan report")
        records = []
        seen = set()
        raw = decrypt(archive.read("ibo-candidate-inventory.jsonl.enc"), secret)
        for line in raw.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                continue
            url = record.get("url")
            if not valid_stream_url(url) or url in seen:
                continue
            if (record.get("http_hls_status") != "AV_VERIFIED"
                or record.get("decoded_av_verified") is not True
                or record.get("decode_status") != "DECODED_AV"):
                continue
            seen.add(url)
            records.append(record)
        report = json.loads(archive.read("ibo-real-scan-report.json"))
        if len(records) != report.get("av_verified"):
            errors.append("Decrypted AV-qualified count disagrees with report")
        package_counts = {}
        for size in (1000, 2000):
            parts = sorted(
                (int(m.group(2)), name)
                for name in names if (m := PATTERN.fullmatch(name)) and int(m.group(1)) == size
            )
            expected_count = (len(records) + size - 1) // size
            if [n for n, _ in parts] != list(range(1, expected_count + 1)):
                errors.append(f"{size}: missing, extra or out-of-sequence parts")
                continue
            for part, name in parts:
                expected = render(records[(part - 1) * size:part * size])
                actual = archive.read(name)
                if actual != expected:
                    errors.append(f"{size} part {part}: playlist does not match decrypted AV-qualified inventory")
            package_counts[str(size)] = len(parts)
        unexpected = [n for n in names if n.startswith("IBO_AV_VERIFIED_") and not PATTERN.fullmatch(n)]
        if unexpected:
            errors.append("Unexpected verified playlist filenames")
    return {
        "result": "PASS" if not errors else "FAIL",
        "zip_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "decrypted_av_qualified_records": len(records),
        "package_parts": package_counts,
        "errors": errors,
        "limitations": [
            "Validates inventory flags and exact playlist bytes, not independent live ffprobe AV",
            "Does not establish playback on a physical IBO device",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.zip, os.environ.get("V2_ARCHIVE_PASSPHRASE", ""))
    except Exception as exc:
        result = {"result": "FAIL", "errors": [type(exc).__name__ + ": evidence unavailable or invalid"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
