#!/usr/bin/env python3
"""Consolidate read-only evidence; distinguish workflow success from channel verification."""
import datetime
import json
from pathlib import Path
from discover import ROOT, LIVE, entries

REPORTS = ROOT / "v2/reports"
def load(name):
    path = REPORTS / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None

def main():
    channels = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    groups = sorted({x["group"] for x in channels})
    backups = [x for x in channels if "YEDEKLER" in x["group"]]
    baseline = load("current-stream-resolution.json")
    stability = load("stream-stability.json")
    quality = load("quality-upgrades.json")
    frames = load("frame-collisions.json")
    assets = load("candidate-assets.json")
    probe = load("turkish-stream-probe.json")
    decoder = load("turkish-stream-decode.json")
    required = {
        "baseline": baseline, "stability": stability, "quality": quality,
        "frames": frames, "candidate_assets": assets, "http_probe": probe,
        "decoder": decoder, "epg": load("epg-integrity.json"),
        "playlist_assets": load("assets-health.json")
    }
    report = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "policy": "READ_ONLY_EVIDENCE_SUMMARY_NOT_ALL_CHANNELS_VERIFIED",
        "playlist_entries": len(channels), "category_count": len(groups),
        "backup_names": sorted(x["name"] for x in backups),
        "reports_present": {k: v is not None for k, v in required.items()},
        "baseline_selected": baseline.get("selected", 0) if baseline else 0,
        "baseline_measured": baseline.get("measured", 0) if baseline else 0,
        "stability_streams_sampled": stability.get("checked", 0) if stability else 0,
        "stability_rounds": stability.get("rounds", 0) if stability else 0,
        "candidate_asset_hints": assets.get("matched", 0) if assets else 0,
        "possible_video_duplicate_groups": len(frames.get("possible_duplicate_groups", [])) if frames else 0,
        "not_proven": ["24h uptime", "correct live channel identity for all URLs",
                       "EPG/logo correctness for new candidates", "every playlist entry decoded"],
    }
    out = REPORTS / "final-validation-summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print("Final evidence:", json.dumps({k:v for k,v in report.items() if k not in ("not_proven", "backup_names", "reports_present")}, ensure_ascii=False))
    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise SystemExit("Missing required reports: " + ", ".join(missing))

if __name__ == "__main__":
    main()
