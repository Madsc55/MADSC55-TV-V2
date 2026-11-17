#!/usr/bin/env python3
"""Read-only, deterministic sharding plan for a separate M3U playlist.

No network access, media probing, or playlist modification.
"""
import argparse
import hashlib
import json
from pathlib import Path


def plan(path, shard_size=500):
    if shard_size < 1:
        raise ValueError("shard_size must be positive")
    entries = []
    pending = None
    with Path(path).open(encoding="utf-8-sig", errors="replace") as source:
        for line in source:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                pending = line
            elif line and not line.startswith("#") and pending is not None:
                entries.append((pending, line))
                pending = None
    seen = {}
    duplicates = 0
    for ordinal, (metadata, url) in enumerate(entries, 1):
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        if digest in seen:
            duplicates += 1
            seen[digest]["ordinals"].append(ordinal)
        else:
            seen[digest] = {"url_sha256": digest, "ordinals": [ordinal],
                            "name_sha256": hashlib.sha256(metadata.encode("utf-8")).hexdigest()}
    unique = list(seen.values())
    shards = []
    for offset in range(0, len(unique), shard_size):
        batch = unique[offset:offset + shard_size]
        shards.append({"shard": len(shards) + 1, "unique_count": len(batch),
                       "first_unique_index": offset + 1,
                       "last_unique_index": offset + len(batch),
                       "fingerprint": hashlib.sha256(
                           "\n".join(row["url_sha256"] for row in batch).encode()
                       ).hexdigest()})
    return {"schema": 1, "mode": "READ_ONLY_PLAN_NO_TESTS",
            "playlist_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "records": len(entries), "unique_urls": len(unique),
            "duplicate_records": duplicates, "shard_size": shard_size,
            "shards": shards, "playlist_modified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", default="YEDEKLER_PLAYLISTESI.m3u8")
    parser.add_argument("--shard-size", type=int, default=500)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    src, dst = Path(args.playlist), Path(args.output)
    if src.resolve() == dst.resolve() or dst.exists():
        parser.error("Output cannot overwrite an existing file or playlist")
    report = plan(src, args.shard_size)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: report[k] for k in ("records", "unique_urls", "duplicate_records", "shard_size") }))


if __name__ == "__main__":
    main()
