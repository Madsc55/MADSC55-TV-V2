#!/usr/bin/env python3
"""Offline, fail-closed check of bounded broadcast/language evidence. No network or playlist writes."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "v2" / "reports"


def read(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def verify():
    source = read("task17-18-20-bounded-retry-20261118.json")
    derived = read("bounded-http-language-row-review-20261121.json")
    fixture = read("turkish-sample-verification-20261119.json")
    assert source["unique_urls_attempted"] == derived["row_count"] == 15
    assert source["attempts_this_batch"] == sum(len(o["attempts"]) for o in source["observations"]) == 17
    source_by_hash = {o["url_sha256"]: o for o in source["observations"]}
    rows = derived["rows"]
    assert len(source_by_hash) == len(rows) == len({r["url_sha256"] for r in rows})
    actions = Counter()
    for row in rows:
        observation = source_by_hash[row["url_sha256"]]
        last = observation["attempts"][-1]
        assert row["source_label"] == observation["playlist_label"]
        assert row["source_domain"] == observation["publisher_domain"]
        assert row["attempt_count"] == len(observation["attempts"])
        for field in ("manifest_http_status", "variant_http_status", "segment_http_status"):
            assert row[field] == last.get(field)
        assert row["video_decoded"] is bool(last["video_frame_decoded"])
        assert row["audio_decoded"] is bool(last["audio_frame_decoded"])
        status = last.get("variant_http_status") or last.get("manifest_http_status")
        if row["video_decoded"] and row["audio_decoded"]:
            expected = "KEEP_AV_EVIDENCE_LANGUAGE_PENDING"
        elif status == 404:
            expected = "REVIEW_SOURCE_HTTP_404"
        elif status == 503:
            expected = "RETRY_LATER_HTTP_503"
        else:
            expected = "MANUAL_REVIEW"
        assert row["recommended_action"] == expected
        assert row["spoken_turkish_verified"] is False
        assert row["turkish_subtitles_verified"] is False
        assert row["tr_az_broadcaster_identity_verified"] is False
        actions[expected] += 1
    assert dict(actions) == derived["action_counts"]
    assert actions == {"REVIEW_SOURCE_HTTP_404": 8, "RETRY_LATER_HTTP_503": 6,
                       "KEEP_AV_EVIDENCE_LANGUAGE_PENDING": 1}
    assert len(fixture["samples"]) == 2
    assert all(s["sample"]["speech"]["spoken_turkish_verified"] is False for s in fixture["samples"])
    assert derived["playlist_mutated"] is False
    assert derived["security_hold_685_lifted"] is False
    return {"rows_verified": len(rows), "attempts_verified": 17, "action_counts": dict(actions)}


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
