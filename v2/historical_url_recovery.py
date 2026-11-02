#!/usr/bin/env python3
"""Offline historical URL recovery; never performs network scans or changes playlists."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

def read_records(path):
    with Path(path).open(encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{number}: expected JSON object")
            yield record

def validate_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

def recover(old_records, current_records):
    current = {row["url"] for row in current_records if validate_url(row.get("url"))}
    recovered, seen = [], set()
    missing_url = 0
    for row in old_records:
        url = row.get("url")
        if not validate_url(url):
            missing_url += 1
            continue
        if url in current or url in seen:
            continue
        seen.add(url)
        recovered.append(dict(row, recovery_status="HISTORICAL_NOT_REVERIFIED",
                              source_status="HISTORICAL_ARTIFACT"))
    return recovered, {"historical_missing_real_url": missing_url,
                       "recoverable_real_urls": len(recovered),
                       "current_urls_excluded": len(current),
                       "device_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.report.exists():
        parser.error("Refusing to overwrite an existing recovery artifact")
    rows, report = recover(read_records(args.historical), read_records(args.current))
    if not rows:
        raise SystemExit("No real historical URLs recovered; refusing empty candidate export")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()
