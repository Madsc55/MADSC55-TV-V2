#!/usr/bin/env python3
"""One-time owner-authorized move of the historical 685 entries into ANA ARŞİV.

No live probing, deletions, additions, language guessing, or unrelated group edits.
The caller supplies the historical Actions manifest downloaded from run 44842556117.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

EXPECTED_MANIFEST_SHA256 = "b001bf48f07437e9ae67ed9f73b12ea9cfcab653523973435cf3b1cee3c31fcc"
GROUP = re.compile(r'(group-title\s*=\s*")([^"]*)(")', re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse(raw):
    lines = raw.decode("utf-8-sig").splitlines(keepends=True)
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("Invalid playlist header")
    prefix, blocks, current = [], [], None
    for line in lines:
        if line.startswith("#EXTINF:"):
            if current is not None:
                raise ValueError("Incomplete channel block")
            current = [line]
        elif current is None:
            prefix.append(line)
        else:
            current.append(line)
            if line.strip() and not line.startswith("#"):
                blocks.append("".join(current))
                current = None
    if current is not None:
        raise ValueError("Incomplete final block")
    return "".join(prefix), blocks


def move(raw, manifest_raw):
    if sha(manifest_raw) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Historical manifest checksum mismatch")
    queue = json.loads(manifest_raw)["retry_queue"]
    if len(queue) != 685:
        raise ValueError("Expected exactly 685 manifest records")
    expected = {}
    for item in queue:
        h = item["channel_sha256"]
        if h in expected or item.get("status") != "uncertain":
            raise ValueError("Duplicate or invalid historical record")
        expected[h] = item["url_sha256"]
    prefix, blocks = parse(raw)
    matches, rest, origins = [], [], collections.Counter()
    for block in blocks:
        identity = sha(block.encode("utf-8"))
        if identity not in expected:
            rest.append(block)
            continue
        if sha(block.splitlines()[-1].strip().encode("utf-8")) != expected[identity]:
            raise ValueError("URL mismatch for historical identity")
        first, sep, tail = block.partition("\n")
        group = GROUP.search(first)
        if not group:
            raise ValueError("Missing group-title")
        origins[group.group(2)] += 1
        updated = first[:group.start(2)] + "ANA ARŞİV" + first[group.end(2):] + sep + tail
        matches.append(updated)
        del expected[identity]
    if expected or len(matches) != 685:
        raise ValueError(f"Only {len(matches)}/685 matched; no changes written")
    # Insert immediately before the first existing ANA ARŞİV record, if present;
    # otherwise insert at the beginning of the channel records.
    insertion = next((i for i, b in enumerate(rest)
                      if (m := GROUP.search(b.splitlines()[0]))
                      and "ANA ARŞİV" in m.group(2).upper()), 0)
    output = (prefix + "".join(rest[:insertion] + matches + rest[insertion:])).encode("utf-8")
    _, after = parse(output)
    if len(after) != len(blocks):
        raise ValueError("Channel count changed")
    return output, {"moved": len(matches), "from_groups": dict(sorted(origins.items())),
                    "target": "ANA ARŞİV", "total_before": len(blocks),
                    "total_after": len(after), "source_sha256": sha(raw),
                    "result_sha256": sha(output)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--playlist", type=Path, default=Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"))
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--report", type=Path, default=Path("move-685-report.json"))
    args = p.parse_args()
    raw = args.playlist.read_bytes()
    output, report = move(raw, args.manifest.read_bytes())
    if args.playlist.read_bytes() != raw:
        raise ValueError("Playlist changed during move")
    args.playlist.write_bytes(output)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
