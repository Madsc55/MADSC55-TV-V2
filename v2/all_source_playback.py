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
LIMIT = int(os.getenv("PLAYBACK_LIMIT", "100"))
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
    sources = json.loads(SOURCES.read_text())["sources"]
    if DISCOVERED.exists():
        try:
            sources += [{"id": "github-auto-" + str(i), "url": s["url"]}
                        for i, s in enumerate(json.loads(DISCOVERED.read_text()).get("sources", [])[:80])]
        except (ValueError, KeyError, OSError):
            pass
    existing = {e["url"] for e in entries(LIVE.read_text(encoding="utf-8-sig"))}
    seen, selected, audit, pools = set(), [], [], []
    for source in sources:
        try:
            last_error = None
            for fetch_attempt in range(1, RETRIES + 2):
                try:
                    parsed = list(entries(fetch(source["url"])))
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
            if last_error is not None:
                raise last_error
            unique = []
            for e in parsed:
                if e["url"] not in existing and e["url"] not in seen:
                    seen.add(e["url"])
                    unique.append(e)
            # Stable per-source ordering, then round-robin across sources.
            # Shards are disjoint and deterministic for the same source snapshot.
            shard_items = [e for e in unique if int(hashlib.sha256(e["url"].encode()).hexdigest(), 16) % SHARD_COUNT == SHARD_INDEX]
            pools.append((source["id"], shard_items))
            audit.append({"source": source["id"], "entries": len(parsed), "new_unique": len(unique),
                          "shard_candidates": len(shard_items), "sampled": 0, "status": "PARSED"})
        except Exception as exc:
            audit.append({"source": source["id"], "status": "FETCH_FAILED", "error": type(exc).__name__})
    # Each page skips already selected positions so later runs expand coverage.
    for round_index in range(PAGE * PER_SOURCE, (PAGE + 1) * PER_SOURCE):
        for source_id, items in pools:
            if len(selected) >= LIMIT:
                break
            if round_index < len(items):
                selected.append((source_id, items[round_index]))
                next(a for a in audit if a["source"] == source_id)["sampled"] += 1
        if len(selected) >= LIMIT:
            break
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(probe, selected))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"policy": "READ_ONLY_SAMPLED_NOT_EXHAUSTIVE",
       "total_sources": len(sources), "shard_index": SHARD_INDEX, "shard_count": SHARD_COUNT, "page": PAGE, "sampled": len(results),
       "video_decoded": sum(x["status"] == "VIDEO_DECODED" for x in results),
       "sources": audit, "results": results}, ensure_ascii=False, indent=2)+"\n")
    print("Sources", len(sources), "sampled", len(results), "decoded", sum(x["status"] == "VIDEO_DECODED" for x in results))

if __name__ == "__main__":
    main()
