#!/usr/bin/env python3
"""Read-only, resumable verification of staged legacy stream URLs."""
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "v2" / "arsiv"
PARTS = [ARCHIVE / f"eski_sistem_aktarim_adaylari_2026-11-16_parca_{i}.m3u8" for i in range(1, 5)]

def candidates():
    items = []
    for part in PARTS:
        lines = part.read_text(encoding="utf-8-sig").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("#EXTINF:") and i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url.startswith(("http://", "https://")):
                    items.append({"name": line.rsplit(",", 1)[-1], "url": url, "source": part.name})
    if len(items) != 7650 or len({x["url"] for x in items}) != 7650:
        raise RuntimeError("Legacy candidate archive count or uniqueness changed; fail closed")
    return items

def probe(url, timeout):
    env = dict(os.environ)
    env["AV_LOG_FORCE_NOCOLOR"] = "1"
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type", "-of", "json", "-rw_timeout", str(timeout * 1000000),
            url], capture_output=True, text=True, timeout=timeout + 5, env=env)
        if p.returncode:
            return "unavailable", p.stderr[-200:]
        kinds = {s.get("codec_type") for s in json.loads(p.stdout).get("streams", [])}
        if not {"video", "audio"}.issubset(kinds):
            return "missing_audio_or_video", ",".join(sorted(kinds))
        q = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-rw_timeout", str(timeout * 1000000), "-i", url, "-t", "5",
            "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
            capture_output=True, text=True, timeout=timeout + 12, env=env)
        return ("av_verified", "") if q.returncode == 0 else ("decode_failed", q.stderr[-200:])
    except (subprocess.TimeoutExpired, OSError, ValueError, json.JSONDecodeError) as e:
        return "error_or_timeout", str(e)[:200]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--batch-size", type=int, default=500)
    ap.add_argument("--timeout", type=int, default=10)
    ap.add_argument("--start-index", type=int, default=None)
    args = ap.parse_args()
    if args.batch_size != 500:
        raise SystemExit("Only approved 500-channel batches permitted")
    all_items = candidates()
    state_file = Path(args.state)
    state = json.loads(state_file.read_text()) if state_file.is_file() else {"next_index": 0, "results": []}
    start = state["next_index"]
    if args.start_index is not None:
        if state_file.exists():
            raise RuntimeError("Explicit start index must not reuse an existing checkpoint")
        if args.start_index not in range(0, 7650, 500):
            raise RuntimeError("Invalid batch start")
        start = args.start_index
        state["next_index"] = start
    if (args.start_index is None and start != len(state["results"])) or not 0 <= start <= len(all_items):
        raise RuntimeError("Checkpoint inconsistent; refusing to skip channels")
    end = min(start + args.batch_size, len(all_items))
    for idx in range(start, end):
        item = all_items[idx]
        status, reason = probe(item["url"], args.timeout)
        state["results"].append({"index": idx, "name": item["name"], "url": item["url"],
                                 "status": status, "detail": reason})
        state["next_index"] = idx + 1
        if (idx + 1) % 25 == 0 or idx + 1 == end:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            tmp.replace(state_file)
    counts = {k: sum(x["status"] == k for x in state["results"]) for k in
              ("av_verified", "unavailable", "missing_audio_or_video", "decode_failed", "error_or_timeout")}
    out = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
           "total_candidates": len(all_items), "tested": state["next_index"],
           "remaining": len(all_items) - state["next_index"], "counts": counts,
           "last_batch": [start, end], "auto_promoted": False}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
