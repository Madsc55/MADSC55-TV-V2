#!/usr/bin/env python3
"""Offline-only stage 6 search plan. Never performs network requests or edits playlists."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "v2/reports/stage6-search-plan.json"
PLATFORMS = {
    "github": "https://github.com/search",
    "gist": "https://gist.github.com/search",
    "gitlab": "https://gitlab.com/search",
    "codeberg": "https://codeberg.org/explore/repos",
}
TERMS = (
    "turkiye.m3u", "tr.m3u8", "turkish-iptv", "canli-tv",
    "yerel-tv", "iptv-turkiye", "azerbaijan iptv m3u",
    "azerbaycan canlı tv", "world iptv m3u8", "live tv m3u",
)
REGIONS = ("TR", "AZ", "world")
CHANNELS = ("repository", "gist", "official_broadcaster", "youtube_live", "m3u_m3u8")

def make_plan():
    return {
        "kind": "STAGE6_OFFLINE_SEARCH_PLAN_NO_LIVE_SCAN",
        "regions": list(REGIONS),
        "platforms": PLATFORMS,
        "queries": list(TERMS),
        "discovery_channels": list(CHANNELS),
        "rules": {
            "main_ibo_read_only": True,
            "existing_channels_not_revalidated": True,
            "no_network_or_playlist_changes": True,
            "no_automatic_channel_import": True,
            "future_acceptance_requires_real_video_and_audio": True,
            "do_not_close_task_34_from_this_report": True,
        },
        "search_jobs_planned": len(PLATFORMS) * len(TERMS),
        "search_jobs_executed": 0,
    }

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(make_plan(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "search_jobs_executed": 0}))

if __name__ == "__main__":
    main()
