#!/usr/bin/env python3
"""One-command, fail-closed move of YEDEKLER positions into the existing foreign archive.

Run from repository root: python v2/archive_backup_range.py 84 101
Commit the three changed files in a reviewed PR. Never writes to GitHub directly.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
ARCHIVE = ROOT / "v2/arsiv/yabanci_yedekler_2026-11-16_positions_84-1006_923.m3u8"
MANIFEST = ROOT / "v2/ibo_authorized_change.json"
INVARIANTS = ROOT / "v2/test_playlist_invariants.py"

def split_records(data):
    lines = data.splitlines(keepends=True)
    header, records = [], []
    for line in lines:
        if line.startswith(b"#EXTINF:"):
            records.append([line])
        elif records:
            records[-1].append(line)
        else:
            header.append(line)
    return b"".join(header), [b"".join(x) for x in records]

def is_backup(record):
    return b"YEDEKLER (" in record.splitlines()[0]

def channel_name(record):
    return record.splitlines()[0].decode("utf-8").split(",", 1)[-1]

def prepare(start, end):
    if start < 3 or end < start:
        raise ValueError("Invalid range; protected YEDEKLER positions 1 and 2 cannot move")
    original = PLAYLIST.read_bytes()
    header, records = split_records(original)
    backups = [r for r in records if is_backup(r)]
    if end > len(backups):
        raise ValueError("Range exceeds current YEDEKLER count")
    chosen = backups[start-1:end]
    if len(chosen) != end-start+1 or any(not is_backup(r) for r in chosen):
        raise ValueError("Unexpected backup selection")
    old_archive = ARCHIVE.read_bytes()
    _, archived = split_records(old_archive)
    archive_records = set(archived)
    # Refuse double-archiving exact records; removing an already-archived
    # entry is allowed without adding a duplicate.
    to_append = [r for r in chosen if r not in archive_records]
    count = len(backups)-len(chosen)
    old_label = ("🗂️ YEDEKLER (%d)" % len(backups)).encode("utf-8")
    new_label = ("🗂️ YEDEKLER (%d)" % count).encode("utf-8")
    if any(old_label not in r.splitlines()[0] for r in backups):
        raise ValueError("Backup group counter is inconsistent")
    chosen_set = set(id(r) for r in chosen)
    new_records = [r.replace(old_label, new_label, 1) if is_backup(r) else r
                   for r in records if id(r) not in chosen_set]
    updated = header + b"".join(new_records)
    _, verify = split_records(updated)
    if len(verify) != len(records)-len(chosen):
        raise ValueError("Playlist record count mismatch")
    if [r for r in records if not is_backup(r)] != [r for r in verify if not is_backup(r)]:
        raise ValueError("Non-backup categories changed")
    # Keep original EXTINF/URL bytes in the archive; no new archive file.
    appendix = b"".join((b"\n" if old_archive and not old_archive.endswith(b"\n") else b"") + r
                       for r in to_append)
    archive_new = old_archive + appendix
    spec = {
        "base_sha256": hashlib.sha256(original).hexdigest(),
        "result_sha256": hashlib.sha256(updated).hexdigest(),
        "operation": "remove",
        "request": f"User authorized moving YEDEKLER positions {start}-{end} inclusive to the existing foreign archive, without touching other categories.",
        "channels": [channel_name(r) for r in chosen],
    }
    tests = INVARIANTS.read_text(encoding="utf-8")
    previous_total = len(records)
    tests = tests.replace(f"len(channels_pre) == {previous_total}", f"len(channels_pre) == {len(verify)}")
    tests = tests.replace(f"backup_count == {len(backups)}", f"backup_count == {count}")
    tests = tests.replace(f"len(backups) == {len(backups)}", f"len(backups) == {count}")
    tests = tests.replace(f"YEDEKLER ({len(backups)})", f"YEDEKLER ({count})")
    # Update stale explanatory count strings as well.
    tests = tests.replace(f"{len(backups)-1000} retained", f"{count-1000} retained")
    if tests == INVARIANTS.read_text(encoding="utf-8"):
        raise ValueError("Invariant test counters were not updated")
    return updated, archive_new, spec, tests, len(chosen), len(to_append)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", type=int)
    parser.add_argument("end", type=int)
    parser.add_argument("--apply", action="store_true", help="Write files after validation (default: preview)")
    args = parser.parse_args()
    updated, archive, spec, tests, moved, appended = prepare(args.start, args.end)
    print(json.dumps({"removed_from_backups": moved, "new_archive_entries": appended,
                      "playlist_sha256": spec["result_sha256"], "apply": args.apply}, ensure_ascii=False))
    if args.apply:
        PLAYLIST.write_bytes(updated)
        ARCHIVE.write_bytes(archive)
        MANIFEST.write_text(json.dumps(spec, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        INVARIANTS.write_text(tests, encoding="utf-8")

if __name__ == "__main__":
    main()
