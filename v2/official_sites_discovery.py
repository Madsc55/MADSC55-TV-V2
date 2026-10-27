#!/usr/bin/env python3
"""Read-only official Turkish broadcaster directory; no scraping of protected streams."""
import datetime
import json
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "v2/reports/official-tv-sites.json"
URL = "https://iptv-org.github.io/api/channels.json"
MAX_BYTES = 30_000_000

def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "MADSC55-V2-Official-Sites/1.0"})
    with urllib.request.urlopen(req, timeout=35) as res:
        raw = res.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise SystemExit("Channel catalog too large")
    catalog = json.loads(raw)
    sites = []
    seen = set()
    for item in catalog:
        if item.get("country") != "TR" or item.get("is_nsfw") or item.get("closed"):
            continue
        url = item.get("website") or ""
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue
        if parsed.hostname.lower() in ("localhost",) or parsed.hostname.endswith(".local"):
            continue
        key = (item.get("id"), parsed.hostname.lower())
        if key in seen:
            continue
        seen.add(key)
        sites.append({"channel_id": str(item.get("id") or ""), "name": str(item.get("name") or ""),
                      "official_site": url, "domain": parsed.hostname.lower(),
                      "status": "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED"})
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "source": URL, "policy": "READ_ONLY_NO_PLAYLIST_CHANGES_NO_DRM_BYPASS",
              "count": len(sites), "channels": sites}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Official Turkish TV sites discovered:", len(sites))
if __name__ == "__main__":
    main()
