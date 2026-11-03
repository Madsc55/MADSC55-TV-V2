#!/usr/bin/env python3
"""Build a conservative review queue for short-decoded Turkish stream candidates."""
import datetime
import json
from discover import ROOT

CANDIDATES = ROOT / "v2/reports/turkish-stream-candidates.json"
DECODE = ROOT / "v2/reports/turkish-stream-decode.json"
OUT = ROOT / "v2/reports/turkish-stream-review-queue.json"

def main():
    catalog = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    decoded = json.loads(DECODE.read_text(encoding="utf-8"))
    by_id = {}
    for item in catalog["candidates"]:
        by_id.setdefault(item["channel_id"], []).append(item)
    queue = []
    for result in decoded["results"]:
        if result["status"] != "SHORT_DECODE_VERIFIED":
            continue
        matches = [x for x in by_id.get(result["channel_id"], []) if x["url"] == result.get("url")]
        for item in matches:
            queue.append({"channel_id": item["channel_id"], "url": item["url"],
                          "review_priority": item["review_priority"],
                          "media_types": result.get("media_types", []),
                          "video_streams": result.get("video_streams", []),
                          "measured_max_height": max((s.get("height") or 0 for s in result.get("video_streams", [])), default=0),
                          "status": "SHORT_DECODED_MANUAL_REVIEW_REQUIRED",
                          "note": "Not confirmed as a new distinct channel or long-term playable."})
    # Results match exact URL and channel ID; never treat sibling URLs as decoded.
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY_REVIEW_QUEUE_NO_AUTO_PROMOTION",
              "verified_channel_ids": len({x["channel_id"] for x in decoded["results"]
                                           if x["status"] == "SHORT_DECODE_VERIFIED"}),
              "review_url_entries": len(queue), "items": queue}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Short-decoded channel IDs:", report["verified_channel_ids"],
          "review URL entries:", len(queue))
if __name__ == "__main__":
    main()
