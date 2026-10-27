#!/usr/bin/env python3
"""Read-only EPG and logo reachability audit; no playlist mutation."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import urllib.request
from collections import Counter
from discover import ROOT, LIVE, entries

OUTPUT = ROOT / "v2" / "reports" / "assets-health.json"

def probe(url):
    if not url.startswith("https://"):
        return {"status": "SKIPPED_NON_HTTPS"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-V2-Audit/1.0", "Range": "bytes=0-4095"})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = res.read(4096)
            status = res.status
            mime = res.headers.get("Content-Type", "").lower()
        return {"status": "REACHABLE" if status in (200, 206) and data else "UNVERIFIED",
                "http_status": status, "content_type": mime}
    except Exception as exc:
        return {"status": "UNREACHABLE_OR_TIMEOUT", "error_type": type(exc).__name__}

def main():
    playlist = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    logos = sorted({e["logo"] for e in playlist if e["logo"]})
    epg_file = ROOT / "v2" / "epg_sources.json"
    epg_sources = json.loads(epg_file.read_text(encoding="utf-8"))["sources"]
    urls = [("logo", x) for x in logos] + [("epg", x) for x in epg_sources]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        checks = list(pool.map(lambda x: probe(x[1]), urls))
    results = []
    for (kind, url), check in zip(urls, checks):
        results.append({"kind": kind, "url_sha256": hashlib.sha256(url.encode()).hexdigest(), **check})
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; reachability is not ownership or correctness confirmation",
              "logo_total": len(logos), "epg_sources_total": len(epg_sources),
              "status_counts": dict(Counter(x["status"] for x in results)),
              "checks": results}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print("Logos:", len(logos), "EPG feeds:", len(epg_sources), "Results:", report["status_counts"])

if __name__ == "__main__":
    main()
