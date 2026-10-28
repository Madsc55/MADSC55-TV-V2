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
    newlisttr = load("newlisttr-check.json")
    all_sources = load("all-source-playback-aggregate.json") or load("all-source-playback.json")
    discovery = load("candidates.json")
    github = load("github-source-discovery.json")
    required = {
        "all_sources": all_sources, "discovery": discovery, "github_sources": github,
        "newlisttr": newlisttr,
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
        "configured_and_discovered_sources": discovery.get("configured_and_discovered_sources", 0) if discovery else 0,
        "sources_accessible": discovery.get("source_count", 0) if discovery else 0,
        "sources_failed": len(discovery.get("errors", [])) if discovery else 0,
        "m3u_candidates": len(discovery.get("candidates", [])) if discovery else 0,
        "all_source_playback_sampled": all_sources.get("unique_tested", all_sources.get("sampled", 0)) if all_sources else 0,
        "all_source_video_decoded": all_sources.get("video_decoded", 0) if all_sources else 0,
        "playback_batches_present": all_sources.get("batches_present", []) if all_sources else [],
        "playback_not_video_decoded": all_sources.get("not_video_decoded", 0) if all_sources else 0,
        "playback_coverage_complete": all_sources.get("coverage_complete", False) if all_sources else False,
        "playback_incomplete_sources": all_sources.get("incomplete_sources", []) if all_sources else [],
        "channel_review_counts": {"approved": 0, "rejected_playback": sum(x.get("classification") == "REJECTED_PLAYBACK" for x in all_sources.get("channel_results", [])) if all_sources else 0, "pending_review": sum(x.get("classification") == "PENDING_REVIEW" for x in all_sources.get("channel_results", [])) if all_sources else 0},
        "github_new_source_files": github.get("sources_found", 0) if github else 0,
        "newlisttr_source_entries": newlisttr.get("source_entries", 0) if newlisttr else 0,
        "newlisttr_tested": newlisttr.get("tested", 0) if newlisttr else 0,
        "newlisttr_short_video_decoded": newlisttr.get("short_video_decoded", 0) if newlisttr else 0,
        "newlisttr_remaining_untested": newlisttr.get("remaining_untested", 0) if newlisttr else 0,
        "baseline_selected": baseline.get("selected", 0) if baseline else 0,
        "baseline_measured": baseline.get("measured", 0) if baseline else 0,
        "stability_streams_sampled": stability.get("checked", 0) if stability else 0,
        "stability_rounds": stability.get("rounds", 0) if stability else 0,
        "candidate_asset_hints": assets.get("matched", 0) if assets else 0,
        "possible_video_duplicate_groups": len(frames.get("possible_duplicate_groups", [])) if frames else 0,
        "not_proven": ["24h uptime", "correct live channel identity for all URLs",
                       "EPG/logo correctness for new candidates", "every playlist entry decoded", "every discovered source candidate decoded", "permanent IBO-compatible YouTube live URL"],
    }
    out = REPORTS / "final-validation-summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print("Final evidence:", json.dumps({k:v for k,v in report.items() if k not in ("not_proven", "backup_names", "reports_present")}, ensure_ascii=False))
    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise SystemExit("Missing required reports: " + ", ".join(missing))
    if not report["playback_coverage_complete"]:
        raise SystemExit("Full source playback coverage NOT achieved; incomplete sources: " + ", ".join(report["playback_incomplete_sources"]))
    if report["channel_review_counts"]["pending_review"]:
        raise SystemExit("Channel identity/EPG/logo/category verification still pending; cannot mark complete")

if __name__ == "__main__":
    main()
