#!/usr/bin/env python3
"""Repeated read-only checks for bounded candidate streams, with per-URL stability evidence."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import time
from discover import ROOT
from turkish_stream_probe import probe

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--interval", type=int, default=90)
    p.add_argument("--limit", type=int, default=32)
    args = p.parse_args()
    rounds = max(1, min(args.rounds, 6))
    interval = max(0, min(args.interval, 600))
    catalog = json.loads((ROOT / "v2/reports/turkish-stream-candidates.json").read_text(encoding="utf-8"))
    selected = catalog["candidates"][:max(0, min(args.limit, 100))]
    history = {}
    timestamps = []
    for number in range(rounds):
        timestamps.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            checks = list(pool.map(probe, selected))
        for item, check in zip(selected, checks):
            key = hashlib.sha256(item["url"].encode()).hexdigest()
            record = history.setdefault(key, {"channel_id": item["channel_id"], "statuses": []})
            record["statuses"].append(check["status"])
        if number + 1 < rounds:
            time.sleep(interval)
    items = [{"url_sha256": key, **value, "responsive_rounds": sum(s == "HTTP_RESPONSIVE_MEDIA_HINT" for s in value["statuses"])}
             for key, value in history.items()]
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY_REPEATED_HTTP_HINTS_NOT_24H_UPTIME_OR_IDENTITY_PROOF",
              "rounds": rounds, "interval_seconds": interval, "timestamps": timestamps,
              "checked": len(items), "items": items}
    out = ROOT / "v2/reports/stream-stability.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print("Stability rounds:", rounds, "streams:", len(items))

if __name__ == "__main__":
    main()
