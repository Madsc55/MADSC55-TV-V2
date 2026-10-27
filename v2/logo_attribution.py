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
    assets_path = ROOT / "v2" / "reports" / "assets-health.json"
    if assets_path.exists():
        assets = json.loads(assets_path.read_text(encoding="utf-8"))
        by_hash = {x["url_sha256"]: x for x in assets.get("checks", []) if x.get("kind") == "logo"}
        for logo in logos:
            check = by_hash.get(logo["url_sha256"], {})
            logo["reachability"] = check.get("status", "NOT_CHECKED")
            logo["content_type"] = check.get("content_type")
            mime = (check.get("content_type") or "").split(";")[0].strip()
            logo["format_check"] = ("IMAGE_MIME" if mime.startswith("image/") else
                                    "NON_IMAGE_MIME" if mime else "MIME_UNKNOWN")
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; logo official status requires independent authoritative evidence",
              "unique_logos": len(logos),
              "reachability_counts": dict(Counter(x.get("reachability", "NOT_CHECKED") for x in logos)),
              "format_counts": dict(Counter(x.get("format_check", "NOT_CHECKED") for x in logos)),
              "host_counts": dict(Counter(x["host"] for x in logos)),
              "logos": logos}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Logo attribution inventory:", len(logos), "all ownership unverified")

if __name__ == "__main__":
    main()
