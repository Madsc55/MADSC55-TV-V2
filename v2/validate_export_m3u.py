#!/usr/bin/env python3
"""Fail-closed, read-only validation of proposed V2 M3U export files.

This does not create exports or claim that streams have passed AV checks.
"""
import argparse
import pathlib
import re
import sys

HEADER = "#EXTM3U"
GROUP = re.compile(r'group-title="([^"]+)"')
ATTRIBUTE = re.compile(r'([\w-]+)="([^"]*)"')


def validate_m3u(text: str) -> list[str]:
    lines = [line.strip() for line in text.lstrip("\ufeff").splitlines() if line.strip()]
    errors = []
    if not lines or lines[0] != HEADER:
        return ["missing exact #EXTM3U header"]
    seen = set()
    pending = None
    for number, line in enumerate(lines[1:], 2):
        if line.startswith("#EXTINF:"):
            if pending is not None:
                errors.append(f"line {number}: previous EXTINF has no URL")
            pending = number
            match = GROUP.search(line)
            if not match or not match.group(1).strip():
                errors.append(f"line {number}: missing or empty group-title")
            if "," not in line or not line.rsplit(",", 1)[-1].strip():
                errors.append(f"line {number}: missing channel name")
        elif line.startswith("#"):
            if pending is not None and line.startswith("#EXT-X-"):
                errors.append(f"line {number}: HLS manifest directive in M3U channel list")
            continue
        else:
            if pending is None:
                errors.append(f"line {number}: URL without EXTINF")
            if not line.startswith(("http://", "https://")):
                errors.append(f"line {number}: unsupported URL scheme")
            if line in seen:
                errors.append(f"line {number}: duplicate stream URL")
            seen.add(line)
            pending = None
    if pending is not None:
        errors.append(f"line {pending}: EXTINF has no URL")
    if not seen:
        errors.append("no stream entries")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("playlists", nargs="+", type=pathlib.Path)
    args = parser.parse_args()
    failed = False
    for path in args.playlists:
        if not path.is_file():
            print(f"FAIL {path}: file missing", file=sys.stderr)
            failed = True
            continue
        errors = validate_m3u(path.read_text(encoding="utf-8-sig"))
        for error in errors:
            print(f"FAIL {path}: {error}", file=sys.stderr)
        if not errors:
            print(f"PASS {path}: structural validation only; AV evidence not assessed")
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
