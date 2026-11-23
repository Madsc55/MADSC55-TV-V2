#!/usr/bin/env python3
"""Place ANA ARŞİV immediately after YEDEKLER in the single main playlist."""
import argparse
import collections
import hashlib
import re
from pathlib import Path

PAT = re.compile(r'group-title\s*=\s*"([^"]*)"', re.I)
def group(block):
    m = PAT.search(block[0])
    return m.group(1).strip().upper() if m else ""

def reorder(data):
    lines = data.splitlines(keepends=True)
    if not lines or not lines[0].startswith(b"#EXTM3U"):
        raise ValueError("Invalid M3U header")
    prefix, blocks, current = [], [], None
    for line in lines:
        if line.startswith(b"#EXTINF:"):
            if current is not None:
                raise ValueError("Incomplete block")
            current = [line]
        elif current is None:
            prefix.append(line)
        else:
            current.append(line)
            if line.strip() and not line.startswith(b"#"):
                blocks.append(current)
                current = None
    if current is not None:
        raise ValueError("Incomplete last block")
    def label(block):
        return group([block[0].decode("utf-8-sig")])
    counts = collections.Counter(label(b) for b in blocks)
    backups = [k for k in counts if k.startswith("YEDEKLER")]
    archive = [k for k in counts if k.startswith("ANA ARŞİV")]
    if len(backups) != 1 or len(archive) != 1:
        raise ValueError(f"Ambiguous groups: backups={backups}, archive={archive}")
    if counts[backups[0]] != 1107 or counts[archive[0]] != 15703:
        raise ValueError(f"Unexpected counts: {counts[backups[0]]} / {counts[archive[0]]}")
    saved = [b for b in blocks if label(b) == archive[0]]
    others = [b for b in blocks if label(b) != archive[0]]
    last_backup = max(i for i,b in enumerate(others) if label(b) == backups[0])
    result = others[:last_backup+1] + saved + others[last_backup+1:]
    before = collections.Counter(hashlib.sha256(b"".join(b)).digest() for b in blocks)
    after = collections.Counter(hashlib.sha256(b"".join(b)).digest() for b in result)
    if before != after:
        raise ValueError("Channel content changed")
    return b"".join(prefix) + b"".join(b"".join(b) for b in result)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("playlist", type=Path)
    args = p.parse_args()
    raw = args.playlist.read_bytes()
    output = reorder(raw)
    args.playlist.write_bytes(output) if output != raw else None
    print("ANA ARŞİV placed after YEDEKLER; 1107/15703 channels preserved")
