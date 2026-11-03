#!/usr/bin/env python3
"""Read-only integration gate for channel discovery inputs.

Run once after discovery adapters and before AV acceptance. This gate does not
fetch media, change playlists, or claim device playback.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "v2/config/sources.json"
REPORTS = {
    "github_gist": ROOT / "v2/reports/github-source-discovery.json",
    "gitlab_codeberg": ROOT / "v2/reports/forge-source-discovery.json",
    "official_live_pages": ROOT / "v2/reports/live-page-references.json",
    "webpage_indexes": ROOT / "v2/reports/webpage-playlist-references.json",
    "youtube": ROOT / "v2/reports/youtube-live-candidates.json",
    "document_platforms": ROOT / "v2/reports/document-platform-references.json",
    "document_handoff": ROOT / "v2/reports/document-platform-sources.json",
}
REQUIRED = {
    "iptv-org", "iptv-org-tr", "iptv-org-az", "iptv-org-tur-language",
    "iptv-org-aze-language", "free-tv-independent", "dearbulut-tr",
    "turktv-itasli-archive", "onureroz-turk-index",
}
def audit():
    sources = json.loads(CONFIG.read_text(encoding="utf-8"))["sources"]
    ids = [s["id"] for s in sources]
    missing = sorted(REQUIRED - set(ids))
    duplicates = sorted({x for x in ids if ids.count(x) > 1})
    reports = {}
    for name, path in REPORTS.items():
        if not path.is_file():
            reports[name] = "MISSING"
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            reports[name] = "PRESENT" if isinstance(data, dict) else "INVALID"
        except (OSError, ValueError):
            reports[name] = "INVALID"
    errors = []
    if missing: errors.append("MISSING_STATIC_SOURCES")
    if duplicates: errors.append("DUPLICATE_SOURCE_IDS")
    if any(v != "PRESENT" for v in reports.values()):
        errors.append("INCOMPLETE_ADAPTER_HANDOFF")
    return {
        "schema": 1,
        "status": "INTEGRATED_REFERENCES_NOT_AV_VERIFIED" if not errors else "INCOMPLETE",
        "static_source_count": len(sources),
        "missing_static_sources": missing,
        "duplicate_source_ids": duplicates,
        "adapter_reports": reports,
        "errors": errors,
        "av_verified": False,
        "ibo_device_verified": False,
    }
if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not result["errors"] else 1)
