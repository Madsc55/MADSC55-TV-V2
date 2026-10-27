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
    verified_decodable = channels.get("decoder_status_counts", {}).get("DECODABLE_VIDEO", 0)
    total = channels.get("playlist_entries") or 0
    report = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": "READ_ONLY",
        "missing_reports": missing,
        "playlist_entries": channels.get("playlist_entries"),
        "category_counts": channels.get("category_counts"),
        "stream_status_counts": channels.get("live_status_counts"),
        "decoder_status_counts": channels.get("decoder_status_counts"),
        "decoder_sample_size": channels.get("decoder_sample_size", 0),
        "video_decodable_count": verified_decodable,
        "video_decodable_playlist_fraction": round(verified_decodable / total, 4) if total else None,
        "decoder_coverage_note": "Unsampled, inaccessible and YouTube entries are not confirmed playable",
        "candidate_count": len(channels.get("candidates", [])),
        "youtube_metadata_only": True,
        "epg_xmltv_status_counts": epg.get("status_counts", {}),
        "epg_playlist_id_matches_by_source": [x.get("playlist_id_matches") for x in epg.get("sources", [])],
        "epg_playlist_id_match_rates_by_source": [x.get("playlist_id_match_rate") for x in epg.get("sources", [])],
        "asset_reachability_status_counts": assets.get("status_counts", {}),
        "logo_reachability_counts": logos.get("reachability_counts", {}),
        "logo_format_counts": logos.get("format_counts", {}),
        "logos_with_official_ownership_verified": 0,
        "logos_requiring_authoritative_verification": logos.get("unique_logos"),
        "all_streams_playback_verified": False,
        "all_logos_officially_verified": False,
        "warnings": [
            "A successful workflow does not mean every stream plays.",
            "The decoder sample is configurable; even a full responsive-stream sample does not prove continuous playback.",
            "Reachable logo URLs do not establish official logo ownership.",
            "XMLTV channel ID overlap does not prove programme accuracy or freshness."
        ]
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "master-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("V2 summary:", "entries=", report["playlist_entries"], "reports_missing=", len(missing))
    if missing:
        raise SystemExit("Required reports missing: " + ", ".join(missing))

if __name__ == "__main__":
    main()
