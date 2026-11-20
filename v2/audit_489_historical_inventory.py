#!/usr/bin/env python3
"""Read-only #489 recovery audit from Git history; never edits a playlist."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

CANONICAL = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
HISTORICAL = "4da4991625f95743e623e411b5cee0ff2925349d"
EXPECTED_HISTORICAL = 18912
EXPECTED_PRIMARY = 838


def records(data):
    result = []
    header = None
    for line in data.decode("utf-8-sig").splitlines():
        if line.startswith("#EXTINF:"):
            if header is not None:
                raise ValueError("Incomplete EXTINF record")
            header = line
        elif header is not None and line.strip() and not line.startswith("#"):
            result.append((header, line.strip()))
            header = None
    if header is not None:
        raise ValueError("Incomplete final record")
    return result


def group(header):
    import re
    match = re.search(r'group-title\s*=\s*"([^"]+)"', header, re.I)
    if not match:
        return "OTHER"
    value = match.group(1).upper()
    if "YEDEKLER" in value:
        return "YEDEKLER"
    if "ANA ARŞİV" in value or "ANA ARSIV" in value:
        return "ANA"
    if "TÜRK ARŞİV" in value or "TURK ARSIV" in value:
        return "TURK"
    if "YABANCI ARŞİV" in value or "YABANCI ARSIV" in value:
        return "YABANCI"
    return "OTHER"


def audit(current, historical):
    from collections import Counter
    old, now = records(historical), records(current)
    old_counts = Counter(group(h) for h, _ in old)
    now_counts = Counter(group(h) for h, _ in now)
    if len(old) != EXPECTED_HISTORICAL or old_counts["YEDEKLER"] != 18074 or old_counts["OTHER"] != EXPECTED_PRIMARY:
        raise ValueError("Historical inventory does not match verified 18074 + 838 baseline")
    # Compare URL multiplicity, not sets: repeated streams are separate playlist records.
    old_urls = Counter(url for _, url in old)
    now_urls = Counter(url for _, url in now)
    missing = old_urls - now_urls
    extra = now_urls - old_urls
    return {
        "historical_sha256": hashlib.sha256(historical).hexdigest(),
        "current_sha256": hashlib.sha256(current).hexdigest(),
        "historical_records": len(old),
        "current_records": len(now),
        "historical_groups": dict(old_counts),
        "current_groups": dict(now_counts),
        "historical_url_occurrences_missing": sum(missing.values()),
        "current_url_occurrences_not_in_history": sum(extra.values()),
        "historical_distinct_urls_missing": len(missing),
        "safe_to_auto_restore": False,
        "reason": "Historical records require reconciliation against 48 excluded channels and later archive moves before any write."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--historical-ref", default=HISTORICAL)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    current = (repo / CANONICAL).read_bytes()
    historical = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{args.historical_ref}:{CANONICAL}"]
    )
    report = audit(current, historical)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
