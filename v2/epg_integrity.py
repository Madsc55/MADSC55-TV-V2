#!/usr/bin/env python3
"""Read-only bounded XMLTV integrity inspection of EPG feeds."""
import concurrent.futures
import datetime
import gzip
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from discover import ROOT

OUT = ROOT / "v2" / "reports" / "epg-integrity.json"
MAX_BYTES = 20_000_000

def inspect(url):
    result = {"url_sha256": hashlib.sha256(url.encode()).hexdigest(), "status": "UNVERIFIED"}
    if not url.startswith("https://"):
        result["status"] = "NON_HTTPS"
        return result
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-V2-EPG-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=16) as res:
            data = res.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            result["status"] = "TOO_LARGE_FOR_AUDIT"
            return result
        if data.startswith(b"\x1f\x8b"):
            data = gzip.decompress(data)
        if len(data) > 120_000_000:
            result["status"] = "DECOMPRESSED_TOO_LARGE"
            return result
        root = ET.fromstring(data)
        if root.tag != "tv":
            result["status"] = "NOT_XMLTV"
            return result
        channels = {node.get("id") for node in root.iter("channel") if node.get("id")}
        programmes = sum(1 for node in root.iter("programme"))
        result.update(status="XMLTV_VALID", channels=len(channels), programmes=programmes)
    except (OSError, ValueError, ET.ParseError, EOFError, gzip.BadGzipFile, MemoryError) as exc:
        result.update(status="EPG_UNVERIFIED", error_type=type(exc).__name__)
    return result

def main():
    sources = json.loads((ROOT / "v2" / "epg_sources.json").read_text(encoding="utf-8"))["sources"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        checks = list(pool.map(inspect, sources))
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; XMLTV structure validated, channel mapping not guaranteed",
              "status_counts": dict(Counter(x["status"] for x in checks)), "sources": checks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("EPG XMLTV validation:", report["status_counts"])

if __name__ == "__main__":
    main()
