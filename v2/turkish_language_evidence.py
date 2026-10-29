#!/usr/bin/env python3
"""Read-only Turkish-language evidence queue; metadata is NOT speech recognition."""
import json
import re
from collections import Counter
from pathlib import Path

REPORTS = Path(__file__).resolve().parent / "reports"
def load(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))

def main():
    discovery = load("candidates.json")
    playback = load("all-source-playback-aggregate.json")
    candidates = discovery["candidates"]
    tested = {r["url_sha256"]: r for r in playback["channel_results"]}
    if len(tested) != len(playback["channel_results"]):
        raise SystemExit("Duplicate playback hashes in Turkish language evidence")
    hashes = {r["url_sha256"] for r in candidates}
    if len(hashes) != len(candidates):
        raise SystemExit("Duplicate candidate hashes in Turkish language evidence")
    if not playback.get("coverage_complete") or len(tested) != len(candidates) or hashes != set(tested):
        raise SystemExit("Turkish language audit refuses incomplete or mismatched playback evidence")
    rows = []
    for candidate in candidates:
        name = candidate.get("name", "")
        tvg = candidate.get("tvg_id", "")
        group = candidate.get("group", "")
        combined = " ".join((name, tvg, group))
        turkish_marker = bool(re.search(r"(?i)(türkçe|turkish|türkiye|turkiye|\.tr(?:\b|$)|\bTR\b)", combined))
        playback_row = tested[candidate["url_sha256"]]
        video = playback_row.get("playback") == "VIDEO_DECODED"
        audio = playback_row.get("audio")
        # Metadata only supports prioritizing review; never auto-approve a language.
        category = "LANGUAGE_REVIEW_WITH_METADATA_HINT" if turkish_marker else "LANGUAGE_REVIEW_SOURCE_ONLY"
        if not video:
            category = "PLAYBACK_UNAVAILABLE_LANGUAGE_UNVERIFIED"
        rows.append({"url_sha256": candidate["url_sha256"], "name": name, "source": candidate.get("source"),
                     "category": category, "video_decoded": video, "audio_evidence": audio,
                     "spoken_turkish_verified": False, "approved": False,
                     "action": "VERIFY_SPOKEN_LANGUAGE_AND_BROADCASTER_IDENTITY"})
    counts = dict(Counter(x["category"] for x in rows))
    report = {"policy": "READ_ONLY_NO_AUTO_LANGUAGE_APPROVAL", "candidate_count": len(rows),
              "spoken_turkish_verified": 0, "approved": 0,
              "counts": counts,
              "limitations": "M3U names, country, tvg-id and decoded video/audio cannot prove spoken Turkish. No ASR/audio-language classifier is run.",
              "candidates": rows}
    (REPORTS / "turkish-language-evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k,v in report.items() if k != "candidates"}, ensure_ascii=False))
if __name__ == "__main__":
    main()
