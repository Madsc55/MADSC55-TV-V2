#!/usr/bin/env python3
"""Retired protected-playlist writer. Preserve an advisory-only review manifest.

No historical backup category, frozen TRT/DHA entries, favorites or LIVE M3U
may be rewritten by this script. Only the strict FFmpeg AV gated separate
test export is eligible for IBO device review.
"""
import json
from discover import ROOT, LIVE, entries

SOURCE = ROOT / "v2/reports/newlisttr-decoded-only.m3u8"
DEST = ROOT / "v2/reports/legacy-newlisttr-review-only.m3u8"
SUMMARY = ROOT / "v2/reports/legacy-newlisttr-not-promoted.json"

def main():
    original = LIVE.read_bytes()
    rows = list(entries(SOURCE.read_text(encoding="utf-8-sig")))
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text("#EXTM3U\n", encoding="utf-8")
    SUMMARY.write_text(json.dumps({
        "policy":"LEGACY_IMPORT_RETIRED_NO_AUTO_IBO_PROMOTION",
        "source_rows_metadata_only":len(rows),
        "exported_ibo_channels":0,"protected_playlist_modified":False,
        "next_step":"Require genuine FFmpeg video and audio evidence via build_verified_test_playlist.py"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if LIVE.read_bytes()!=original:
        raise RuntimeError("Protected playlist changed during legacy review")
    print("Legacy NewlistTR import disabled; advisory rows:",len(rows))

if __name__=="__main__":
    main()
