#!/usr/bin/env python3
"""Bounded, read-only playback verification across ALL discovered M3U sources."""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import subprocess
import urllib.request
from discover import ROOT, SOURCES, LIVE, entries, fetch

OUT = ROOT / "v2/reports/all-source-playback.json"
DISCOVERED = ROOT / "v2/reports/github-source-discovery.json"
SNAPSHOT = ROOT / "v2/reports/private-playback-snapshot.json"
PER_SOURCE = int(os.getenv("PLAYBACK_PER_SOURCE", "4"))
SHARD_COUNT = max(1, int(os.getenv("PLAYBACK_SHARD_COUNT", "1")))
SHARD_INDEX = int(os.getenv("PLAYBACK_SHARD_INDEX", "0"))
if not 0 <= SHARD_INDEX < SHARD_COUNT:
    raise ValueError("PLAYBACK_SHARD_INDEX must be within shard count")
PAGE = max(0, int(os.getenv("PLAYBACK_PAGE", "0")))
WORKERS = 6
RETRIES = 3

def probe(item):
    source, e = item
    url = e["url"]
    digest = hashlib.sha256(url.encode()).hexdigest()
    result = {"source": source, "name": e["name"], "url_sha256": digest, "status": "UNVERIFIED"}
    for attempt in range(1, RETRIES + 2):
      result["attempts"] = attempt
      try:
        proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,codec_name,width,height", "-of", "json",
            "-analyzeduration", "1500000", "-probesize", "1000000", url],
            capture_output=True, text=True, timeout=14)
        streams = json.loads(proc.stdout or "{}").get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = any(s.get("codec_type") == "audio" for s in streams)
        if proc.returncode == 0 and video:
            result.update(status="VIDEO_DECODED", width=video.get("width"), height=video.get("height"), audio=audio)
        else:
            result["status"] = "NO_VIDEO_DECODED"
      except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["status"] = type(exc).__name__
      if result["status"] == "VIDEO_DECODED":
        break
    return result

def main():
    if not SNAPSHOT.exists():
        raise SystemExit("Shared private candidate snapshot missing; refusing inconsistent per-shard fetch")
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    grouped = {}
    for item in snap["candidates"]:
        grouped.setdefault(item["source"], []).append(item)
    selected, audit, pools = [], [], []
    for source in snap["sources"]:
        source_id = source["source"]
        items = grouped.get(source_id, [])
        shard_items = [e for e in items if int(hashlib.sha256(e["url"].encode()).hexdigest(), 16) % SHARD_COUNT == SHARD_INDEX]
        pools.append((source_id, shard_items))
        fingerprint = hashlib.sha256("\n".join(sorted(hashlib.sha256(e["url"].encode()).hexdigest() for e in shard_items)).encode()).hexdigest()
        audit.append({"source": source_id, "entries": source.get("entries", 0),
                      "shard_candidates": len(shard_items), "shard_fingerprint": fingerprint,
                      "sampled": 0, "status": "FETCH_FAILED" if source["status"] == "FETCH_FAILED" else "PARSED"})
    sources = snap["sources"]
    # Partition every source into disjoint pages; do not silently truncate candidate coverage.
    max_items = max((len(items) for _, items in pools), default=0)
    for round_index in (i for block in range(PAGE * PER_SOURCE, max_items, PER_SOURCE * 2) for i in range(block, min(block + PER_SOURCE, max_items))):
        for source_id, items in pools:
            if round_index < len(items):
                selected.append((source_id, items[round_index]))
                next(a for a in audit if a["source"] == source_id)["sampled"] += 1
    # No fixed candidate cap: each disjoint shard/page processes all assigned entries.
    # Bound concurrent work without truncating the source coverage.
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for result in pool.map(probe, selected):
            results.append(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"policy": "READ_ONLY_SAMPLED_NOT_EXHAUSTIVE",
       "total_sources": len(sources), "shard_index": SHARD_INDEX, "shard_count": SHARD_COUNT, "page": PAGE, "sampled": len(results),
       "video_decoded": sum(x["status"] == "VIDEO_DECODED" for x in results),
       "sources": audit, "results": results}, ensure_ascii=False, indent=2)+"\n")
    print("Sources", len(sources), "sampled", len(results), "decoded", sum(x["status"] == "VIDEO_DECODED" for x in results))

if __name__ == "__main__":
    main()
