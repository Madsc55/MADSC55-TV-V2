#!/usr/bin/env python3
"""Lossless, bounded-size category parts for the one canonical IBO playlist."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
PARTS = ROOT / "v2/playlists/parts"
MANIFEST = PARTS / "manifest.json"
GROUP = re.compile(rb'group-title="([^"]*)"')
MAX_BYTES = 500_000

def split_records(data):
    offsets = [m.start() for m in re.finditer(rb"(?m)^#EXTINF:", data)]
    if not offsets:
        raise ValueError("No EXTINF records")
    return data[:offsets[0]], [data[a:(offsets[i+1] if i+1 < len(offsets) else len(data))]
                                  for i, a in enumerate(offsets)]

def category(record):
    m = GROUP.search(record.splitlines()[0])
    if not m:
        raise ValueError("Missing group-title")
    return m.group(1).decode("utf-8")

def logical(name):
    upper = name.upper()
    if "YEDEKLER" in upper:
        return "YEDEKLER"
    if "ANA ARŞİV" in upper:
        return "ANA ARŞİV"
    return name

def checksum(data):
    return hashlib.sha256(data).hexdigest()

def inventory(records):
    return Counter(logical(category(r)) for r in records)

def write_parts():
    if MANIFEST.exists():
        raise ValueError("Parts already initialized; refusing to overwrite")
    original = PLAYLIST.read_bytes()
    header, records = split_records(original)
    counts = inventory(records)
    if len(records) != 18337 or counts["YEDEKLER"] != 1107 or counts["ANA ARŞİV"] != 15703:
        raise ValueError("Unexpected source inventory; refusing migration")
    # Reorder whole archive without altering any record bytes.
    archive = [r for r in records if logical(category(r)) == "ANA ARŞİV"]
    remaining = [r for r in records if logical(category(r)) != "ANA ARŞİV"]
    insert = max(i for i, r in enumerate(remaining) if logical(category(r)) == "YEDEKLER") + 1
    ordered = remaining[:insert] + archive + remaining[insert:]
    if Counter(ordered) != Counter(records):
        raise ValueError("Record preservation failure")
    PARTS.mkdir(parents=True, exist_ok=True)
    entries = []
    chunks = []
    current = []
    current_size = 0
    current_group = None
    for record in ordered:
        group = logical(category(record))
        if current and (group != current_group or current_size + len(record) > MAX_BYTES):
            chunks.append((current_group, b"".join(current), len(current)))
            current, current_size = [], 0
        if len(record) > MAX_BYTES:
            raise ValueError("Single record exceeds max part size")
        current_group = group
        current.append(record)
        current_size += len(record)
    if current:
        chunks.append((current_group, b"".join(current), len(current)))
    for index, (group, content, count) in enumerate(chunks):
        name = f"{index:04d}.m3u"
        (PARTS / name).write_bytes(content)
        entries.append({"file": name, "group": group, "records": count, "sha256": checksum(content)})
    manifest = {"version": 1, "header_hex": header.hex(), "source_sha256": checksum(original),
                "total_records": len(records), "entries": entries}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return build()

def build():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest["entries"]
    if not entries or len(set(e["file"] for e in entries)) != len(entries):
        raise ValueError("Invalid manifest")
    parts = []
    for entry in entries:
        filename = entry["file"]
        if not re.fullmatch(r"[0-9]{4}\.m3u", filename):
            raise ValueError("Unsafe part path")
        data = (PARTS / filename).read_bytes()
        _, records = split_records(data) if data.startswith(b"#EXTINF:") else (None, None)
        if records is None or len(records) != entry["records"]:
            raise ValueError("Part record count mismatch: " + filename)
        if any(logical(category(r)) != entry["group"] for r in records):
            raise ValueError("Part category mismatch: " + filename)
        parts.append(data)
    if set(p.name for p in PARTS.glob("*.m3u")) != set(e["file"] for e in entries):
        raise ValueError("Unexpected/missing part files")
    data = bytes.fromhex(manifest["header_hex"]) + b"".join(parts)
    _, records = split_records(data)
    counts = inventory(records)
    if len(records) != manifest["total_records"]:
        raise ValueError("Playlist record count changed")
    if counts["YEDEKLER"] != 1107 or counts["ANA ARŞİV"] != 15703 or len(records) != 18337:
        raise ValueError("Protected inventory changed")
    groups = [logical(category(r)) for r in records]
    y = max(i for i, g in enumerate(groups) if g == "YEDEKLER")
    if groups[y+1:y+1+15703] != ["ANA ARŞİV"] * 15703:
        raise ValueError("ANA ARŞİV must follow YEDEKLER")
    PLAYLIST.write_bytes(data)
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "build", "auto"])
    args = parser.parse_args()
    if args.command == "init" or (args.command == "auto" and not MANIFEST.exists()):
        write_parts()
    else:
        build()
