#!/usr/bin/env python3
"""Read-only audit of logo-only candidates from an older IBO playlist revision.

No network requests, playlist edits, or automatic logo acceptance.
"""
import argparse
import json
import re
from pathlib import Path

LOGO = re.compile(r'(?<!\\w)tvg-logo="([^"]+)"')
ID = re.compile(r'(?<!\\w)tvg-id="([^"]+)"')


def records(text):
    """Index EXTINF records by stream URL, preserving duplicate URL ambiguity."""
    found = {}
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        if not line.startswith("#EXTINF:"):
            continue
        url = lines[index + 1].strip()
        if not url.startswith(("https://", "http://")):
            continue
        found.setdefault(url, []).append(line)
    return found


def audit(current_text, historical_text):
    current, historical = records(current_text), records(historical_text)
    candidates, ambiguous = [], 0
    for url, old_lines in historical.items():
        new_lines = current.get(url, [])
        if not new_lines:
            continue
        if len(old_lines) != 1 or len(new_lines) != 1:
            ambiguous += 1
            continue
        old, new = old_lines[0], new_lines[0]
        old_logo, new_logo = LOGO.search(old), LOGO.search(new)
        if not old_logo or (new_logo and new_logo.group(1)):
            continue
        old_id, new_id = ID.search(old), ID.search(new)
        # Never transfer a logo across changed or missing channel identity.
        if not old_id or not new_id or old_id.group(1) != new_id.group(1):
            ambiguous += 1
            continue
        if not old_logo.group(1).startswith("https://"):
            ambiguous += 1
            continue
        candidates.append({"tvg_id": new_id.group(1),
                           "name": new.rsplit(",", 1)[-1],
                           "logo_url": old_logo.group(1),
                           "status": "REVIEW_REQUIRED_NOT_VERIFIED"})
    return {"candidate_count": len(candidates),
            "ambiguous_records_skipped": ambiguous,
            "warning": "Historical logos are unverified; do not auto-apply.",
            "candidates": candidates}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--historical", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.current.read_text(encoding="utf-8-sig"),
                           args.historical.read_text(encoding="utf-8-sig")),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
