#!/usr/bin/env python3
"""Read-only recurring AV audit of the EXISTING main playlist YEDEKLER category."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import pathlib
import sys
from stream_probe import probe, verify_decoded_av

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"

def channels(text):
    pending = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            pending = line
        elif line and not line.startswith("#"):
            if pending and 'group-title="' in pending:
                group = pending.split('group-title="', 1)[1].split('"', 1)[0]
                if "YEDEKLER" in group:
                    yield {"name": pending.rsplit(",", 1)[-1].strip(), "url": line}
            pending = None

def check(item, timeout):
    # Network errors are NOT evidence of a permanently dead channel.
    try:
        result = probe(item["url"], timeout=timeout)
        if result["status"] == "AV_STREAMS_PRESENT":
            result.update(verify_decoded_av(item["url"], timeout=timeout))
            if result.get("decoded_av_verified"):
                result["status"] = "AV_VERIFIED"
        status = result["status"]
    except Exception:
        status = "PROBE_ERROR"
        result = {}
    return {"position": item["position"], "name": item["name"],
            "url_sha256": hashlib.sha256(item["url"].encode()).hexdigest(),
            "status": status, "video": bool(result.get("video")),
            "audio": bool(result.get("audio")),
            "decoded_av_verified": bool(result.get("decoded_av_verified")),
            "classification": "WORKING" if status == "AV_VERIFIED" else "RECHECK_REQUIRED"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=int, default=15)
    p.add_argument("--output", default="v2/reports/yedekler_av_audit.json")
    args = p.parse_args()
    if not 1 <= args.workers <= 16 or not 5 <= args.timeout <= 60:
        p.error("workers must be 1..16 and timeout 5..60")
    raw = PLAYLIST.read_bytes()
    entries = list(channels(raw.decode("utf-8-sig")))
    if not entries:
        raise SystemExit("REFUSED: YEDEKLER empty or missing")
    for pos, item in enumerate(entries, 1):
        item["position"] = pos
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda item: check(item, args.timeout), entries))
    counts = {}
    for result in results:
        counts[result["classification"]] = counts.get(result["classification"], 0) + 1
    report = {"schema_version": 1, "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "playlist_sha256": hashlib.sha256(raw).hexdigest(),
              "category": "YEDEKLER", "total": len(entries),
              "counts": counts, "results": results,
              "policy": "Read-only; failures need repeat verification. Never auto-delete, mark or reorder."}
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(entries), "counts": counts, "report": str(output)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
