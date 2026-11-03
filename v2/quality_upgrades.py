#!/usr/bin/env python3
"""Read-only quality upgrade candidates, including channels already in the playlist."""
import datetime
import json
import re
from discover import ROOT, LIVE, entries

SOURCE = ROOT / "v2/reports/turkish-stream-candidates.json"
OUT = ROOT / "v2/reports/quality-upgrades.json"

def height(text):
    text = str(text or "").casefold()
    m = re.search(r"(?<!\d)(2160|1440|1080|720|576|540|480|360)[pi]?(?!\d)", text)
    if m:
        return int(m.group(1))
    if "4k" in text or "uhd" in text:
        return 2160
    if "fhd" in text:
        return 1080
    if re.search(r"\bhd\b", text):
        return 720
    return None

def main():
    current = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    by_id = {}
    for e in current:
        if e["tvg_id"]:
            by_id.setdefault(e["tvg_id"].split("@")[0].casefold(), []).append(e)
    catalog = json.loads(SOURCE.read_text(encoding="utf-8"))
    decoded_path = ROOT / "v2/reports/turkish-stream-decode.json"
    decoded = json.loads(decoded_path.read_text(encoding="utf-8")) if decoded_path.exists() else {"results": []}
    measurements = {(x.get("channel_id"), x.get("url")): max((v.get("height") or 0 for v in x.get("video_streams", [])), default=0) for x in decoded.get("results", []) if x.get("status") == "SHORT_DECODE_VERIFIED"}
    baseline_path = ROOT / "v2/reports/current-stream-resolution.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {"results": []}
    measured_current = {}
    for sample in baseline.get("results", []):
        if sample.get("status") == "MEASURED" and sample.get("tvg_id"):
            k = sample["tvg_id"].split("@")[0].casefold()
            measured_current[k] = max(measured_current.get(k, 0), sample["height"])
    items = []
    for c in catalog["candidates"]:
        channel = c["channel_id"]
        present = by_id.get(channel.split("@")[0].casefold(), [])
        claimed = height(c.get("declared_quality"))
        known = [height(e["name"]) for e in present]
        known = [x for x in known if x is not None]
        best_known = max(known) if known else None
        if present:
            status = ("POTENTIAL_QUALITY_UPGRADE" if claimed and best_known and claimed > best_known
                      else "QUALITY_COMPARISON_NEEDED")
        else:
            status = "NEW_CHANNEL_CANDIDATE"
        measured = measurements.get((channel, c["url"]))
        current_measured = measured_current.get(channel.split("@")[0].casefold())
        measured_comparison = ("MEASURED_CANDIDATE_HIGHER" if measured and current_measured and measured > current_measured else "MEASURED_NO_UPGRADE" if measured and current_measured else "INSUFFICIENT_MEASUREMENTS")
        items.append({"channel_id": channel, "url": c["url"],
                      "candidate_measured_height": measured,
                      "current_measured_height": current_measured,
                      "measured_comparison": measured_comparison,
                      "existing_playlist_entries": len(present),
                      "existing_label_height": best_known,
                      "candidate_declared_height": claimed,
                      "status": status,
                      "warning": "Name and catalog quality labels are unverified; ffprobe width/height and stability required."})
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; never replace a stream based on name or declared quality",
              "candidates": items,
              "potential_label_upgrades": sum(x["status"] == "POTENTIAL_QUALITY_UPGRADE" for x in items),
              "measured_candidate_count": sum(x["candidate_measured_height"] is not None for x in items),
              "existing_channel_alternatives": sum(x["existing_playlist_entries"] > 0 for x in items)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Existing-channel alternatives:", report["existing_channel_alternatives"],
          "potential label upgrades:", report["potential_label_upgrades"])
if __name__ == "__main__":
    main()
