#!/usr/bin/env python3
"""Sort only ANA ARŞİV entries in the one canonical IBO playlist, A-Z.

Default is read-only. --write requires exact expected category and total counts.
All EXTINF records (including URLs, logos, attributes) remain byte-identical.
"""
import argparse
from collections import Counter
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
GROUP = re.compile(rb'group-title\s*=\s*"([^"]*)"')


def parse(raw):
    lines = raw.splitlines(keepends=True)
    prefix, blocks, current = [], [], None
    for line in lines:
        if line.startswith(b"#EXTINF:"):
            if current is not None:
                raise ValueError("Incomplete EXTINF entry")
            current = [line]
        elif current is None:
            prefix.append(line)
        else:
            current.append(line)
            if line.strip() and not line.startswith(b"#"):
                blocks.append(b"".join(current))
                current = None
    if current is not None or not b"".join(prefix).startswith(b"#EXTM3U"):
        raise ValueError("Malformed playlist")
    return b"".join(prefix), blocks


def is_archive(block):
    match = GROUP.search(block.splitlines()[0])
    return bool(match and "ANA ARŞİV" in match.group(1).decode("utf-8").upper())


def sort_key(block):
    extinf = block.splitlines()[0].decode("utf-8")
    name = extinf.rsplit(",", 1)[-1].strip()
    # Natural Turkish-friendly, case-insensitive alphabetical comparison.
    normalized = unicodedata.normalize("NFKD", name.casefold())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = normalized.translate(str.maketrans({"ı": "i", "æ": "ae", "œ": "oe"}))
    return normalized, name.casefold()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write verified result to canonical playlist")
    args = ap.parse_args()
    original = PLAYLIST.read_bytes()
    prefix, blocks = parse(original)
    positions = [i for i, block in enumerate(blocks) if is_archive(block)]
    if len(blocks) != 18337 or len(positions) != 15703:
        raise SystemExit(f"Refusing unexpected counts: total={len(blocks)}, ANA ARŞİV={len(positions)}")
    position_set = set(positions)
    before = [blocks[i] for i in positions]
    after = sorted(before, key=sort_key)
    updated = blocks.copy()
    for i, block in zip(positions, after):
        updated[i] = block
    result = prefix + b"".join(updated)
    new_prefix, verified = parse(result)
    if (new_prefix != prefix or len(verified) != len(blocks)
            or Counter(verified) != Counter(blocks)
            or [verified[i] for i in range(len(blocks)) if i not in position_set]
               != [blocks[i] for i in range(len(blocks)) if i not in set(positions)]
            or [verified[i] for i in positions] != after):
        raise SystemExit("Invariant failure; refusing write")
    changed = sum(a != b for a, b in zip(before, after))
    print(f"ANA ARŞİV={len(positions)}; total={len(blocks)}; reordered positions={changed}")
    if args.write:
        PLAYLIST.write_bytes(result)
        print("Wrote canonical playlist (no new playlist created)")
    else:
        print("Dry run only; pass --write to apply")


if __name__ == "__main__":
    main()
