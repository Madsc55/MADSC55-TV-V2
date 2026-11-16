#!/usr/bin/env python3
"""Read-only, lossless IBO playlist snapshot/restore validation.

Never edits the protected live playlist. Archive includes all raw lines, not
only parsed channels. Restore writes to a new destination with exclusive create.
"""
import argparse
import hashlib
import json
from pathlib import Path

MAX_BYTES = 25_000_000

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inventory(data):
    text = data.decode("utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0] != "#EXTM3U":
        raise ValueError("Invalid M3U header")
    records = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF:"):
            url = None
            for candidate in lines[i + 1:]:
                candidate = candidate.strip()
                if candidate.startswith("#EXTINF:"):
                    break
                if not candidate or candidate.startswith("#"):
                    continue
                if candidate.startswith(("http://", "https://")):
                    url = candidate
                break
            if url is None:
                raise ValueError(f"Missing stream URL after EXTINF at line {i + 1}")
            records.append({"name": line.rsplit(",", 1)[-1], "metadata": line, "url": url, "line": i + 1})
    return records

def archive(source, target):
    data = Path(source).read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("Playlist too large")
    records = inventory(data)
    payload = {"schema": 1, "source_name": Path(source).name, "sha256": digest(data),
               "size": len(data), "channels": len(records), "playlist_hex": data.hex()}
    with Path(target).open("x", encoding="utf-8") as out:
        json.dump(payload, out, ensure_ascii=False)
        out.write("\n")
    return len(records)

def restore(source, target):
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or not isinstance(payload.get("playlist_hex"), str):
        raise ValueError("Invalid archive")
    data = bytes.fromhex(payload["playlist_hex"])
    if len(data) > MAX_BYTES or digest(data) != payload.get("sha256") or len(data) != payload.get("size"):
        raise ValueError("Archive integrity failure")
    if len(inventory(data)) != payload.get("channels"):
        raise ValueError("Channel count mismatch")
    with Path(target).open("xb") as out:
        out.write(data)
    return payload["channels"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["archive", "restore"])
    parser.add_argument("source")
    parser.add_argument("target")
    args = parser.parse_args()
    print(args.action, archive(args.source, args.target) if args.action == "archive" else restore(args.source, args.target))

if __name__ == "__main__":
    main()
