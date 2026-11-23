#!/usr/bin/env python3
"""Read-only reporting of shared stream URLs and different channel identity labels."""
import datetime
import json
from discover import ROOT, LIVE, entries
from shared_url_identity import normalized_url, summarize_shared_urls

# Backward-compatible helper for callers of the old collision auditor.
normalize = normalized_url

OUT = ROOT / "v2/reports/stream-url-collisions.json"


def main():
    channels = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    report = summarize_shared_urls({**item, "source": "MAIN_PLAYLIST"} for item in channels)
    report["created_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report["playlist_entries"] = report["playlist_entries_examined"]
    report["same_identity_repeated_category_entries"] = report["same_identity_repeated_entries"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Shared URL review:", report["playlist_entries_examined"], "entries;",
          report["cross_channel_url_collision_count"], "different-name collisions;",
          report["multiple_program_selector_hint_count"], "program-selector hints")


if __name__ == "__main__":
    main()
