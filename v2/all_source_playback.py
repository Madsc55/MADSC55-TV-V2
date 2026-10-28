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
WORKERS = 6

def probe(item):
    source, e = item
    url = e["url"]
    digest = hashlib.sha256(url.encode()).hexdigest()
    result = {"source": source, "name": e["name"], "url_sha256": digest, "status": "UNVERIFIED"}
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
    seen, selected, audit = set(), [], []
    for source in sources:
        if len(selected) >= LIMIT:
            break
        try:
            parsed = list(entries(fetch(source["url"])))
            unique = []
            for e in parsed:
                if e["url"] not in existing and e["url"] not in seen:
                    seen.add(e["url"])
                    unique.append(e)
            batch = unique[:min(PER_SOURCE, LIMIT-len(selected))]
            selected.extend((source["id"], e) for e in batch)
            audit.append({"source": source["id"], "entries": len(parsed), "new_unique": len(unique),
                          "sampled": len(batch), "status": "PARSED"})
        except Exception as exc:
            audit.append({"source": source["id"], "status": "FETCH_FAILED", "error": type(exc).__name__})
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(probe, selected))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"policy": "READ_ONLY_SAMPLED_NOT_EXHAUSTIVE",
       "total_sources": len(sources), "sampled": len(results),
       "video_decoded": sum(x["status"] == "VIDEO_DECODED" for x in results),
       "sources": audit, "results": results}, ensure_ascii=False, indent=2)+"\n")
    print("Sources", len(sources), "sampled", len(results), "decoded", sum(x["status"] == "VIDEO_DECODED" for x in results))

if __name__ == "__main__":
    main()
