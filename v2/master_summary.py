#!/usr/bin/env python3
"""Summarize V2 read-only audits; never claim untested media or official logos."""
import datetime
import json
from collections import Counter
from discover import ROOT

REPORTS = ROOT / "v2" / "reports"
FILES = {"channels": "turkish-tv-health.json", "assets": "assets-health.json",
         "logos": "logo-attribution.json", "epg": "epg-integrity.json"}

def main():
    data = {}
    missing = []
    for key, name in FILES.items():
        path = REPORTS / name
        if not path.exists():
            missing.append(name)
            continue
        data[key] = json.loads(path.read_text(encoding="utf-8"))
    channels = data.get("channels", {})
    epg = data.get("epg", {})
    assets = data.get("assets", {})
    logos = data.get("logos", {})
    report = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": "READ_ONLY",
        "missing_reports": missing,
        "playlist_entries": channels.get("playlist_entries"),
        "category_counts": channels.get("category_counts"),
        "stream_status_counts": channels.get("live_status_counts"),
        "decoder_status_counts": channels.get("decoder_status_counts"),
        "decoder_sample_size": channels.get("decoder_sample_size", 0),
        "candidate_count": len(channels.get("candidates", [])),
        "youtube_metadata_only": True,
        "epg_xmltv_status_counts": epg.get("status_counts", {}),
        "asset_reachability_status_counts": assets.get("status_counts", {}),
        "logos_with_official_ownership_verified": 0,
        "logos_requiring_authoritative_verification": logos.get("unique_logos"),
        "all_streams_playback_verified": False,
        "all_logos_officially_verified": False,
        "warnings": [
            "A successful workflow does not mean every stream plays.",
            "ffprobe tests a rotating subset; audio/video continuity remains unverified.",
            "Reachable logo URLs do not establish official logo ownership.",
            "XMLTV-valid feeds do not guarantee channel-to-programme matching."
        ]
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "master-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("V2 summary:", "entries=", report["playlist_entries"], "reports_missing=", len(missing))
    if missing:
        raise SystemExit("Required reports missing: " + ", ".join(missing))

if __name__ == "__main__":
    main()
