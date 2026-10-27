#!/usr/bin/env python3
"""Read-only detection of stream URL collisions across distinct TV channel identities."""
import collections
import datetime
import hashlib
import json
import urllib.parse
from discover import ROOT, LIVE, entries

OUT = ROOT / "v2/reports/stream-url-collisions.json"

def normalize(url):
    p = urllib.parse.urlsplit(url.strip())
    # Preserve query: tokenized variants may refer to distinct resources.
    return urllib.parse.urlunsplit((p.scheme.lower(), (p.netloc or "").lower(), p.path, p.query, ""))

def main():
    channels = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    by_url = collections.defaultdict(list)
    for item in channels:
        by_url[normalize(item["url"])].append(item)
    collisions = []
    repeated_category_entries = 0
    for url, items in by_url.items():
        identities = {(x["tvg_id"] or x["name"]).casefold().strip() for x in items}
        if len(identities) <= 1:
            repeated_category_entries += max(0, len(items) - 1)
            continue
        collisions.append({"url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                           "distinct_channel_identities": len(identities),
                           "channels": sorted({x["name"] for x in items}),
                           "tvg_ids": sorted({x["tvg_id"] for x in items if x["tvg_id"]}),
                           "groups": sorted({x["group"] for x in items})})
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; exact normalized URL collisions are strong evidence, but shared CDN hosts alone are not collisions",
              "playlist_entries": len(channels), "distinct_urls": len(by_url),
              "same_identity_repeated_category_entries": repeated_category_entries,
              "cross_channel_url_collision_count": len(collisions),
              "cross_channel_url_collisions": collisions}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("URL collision audit:", len(channels), "entries;",
          len(collisions), "cross-channel URL collisions;",
          repeated_category_entries, "same-channel category repetitions")
if __name__ == "__main__":
    main()
