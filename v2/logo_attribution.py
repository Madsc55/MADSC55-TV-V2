#!/usr/bin/env python3
"""Read-only logo attribution evidence, without claiming official ownership."""
import datetime
import hashlib
import json
import pathlib
import urllib.parse
from collections import Counter
from discover import ROOT, LIVE, entries

OUT = ROOT / "v2" / "reports" / "logo-attribution.json"

def main():
    live = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    seen = set()
    logos = []
    for e in live:
        url = e["logo"]
        if not url or url in seen:
            continue
        seen.add(url)
        host = urllib.parse.urlsplit(url).hostname or ""
        logos.append({"url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                      "host": host.lower(), "status": "OWNERSHIP_UNVERIFIED",
                      "reason": "Domain alone does not prove channel logo ownership"})
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; logo official status requires independent authoritative evidence",
              "unique_logos": len(logos), "host_counts": dict(Counter(x["host"] for x in logos)),
              "logos": logos}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Logo attribution inventory:", len(logos), "all ownership unverified")

if __name__ == "__main__":
    main()
