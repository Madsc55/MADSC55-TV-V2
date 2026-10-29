#!/usr/bin/env python3
"""Offline behavioral checks: metadata and audio never prove spoken Turkish."""
import importlib.util
import json
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("language_under_test", Path(__file__).with_name("turkish_language_evidence.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def run_case(candidate, playback, complete=True):
    with tempfile.TemporaryDirectory() as directory:
        reports = Path(directory)
        (reports / "candidates.json").write_text(json.dumps({"candidates": [candidate]}))
        (reports / "all-source-playback-aggregate.json").write_text(json.dumps({
            "channel_results": [playback], "coverage_complete": complete}))
        original = module.REPORTS
        module.REPORTS = reports
        try:
            module.main()
            return json.loads((reports / "turkish-language-evidence.json").read_text())
        finally:
            module.REPORTS = original

def main():
    candidate = {"url_sha256": "a" * 64, "name": "Türkçe Haber", "source": "fixture", "tvg_id": "test.tr", "group": "HABER"}
    playback = {"url_sha256": candidate["url_sha256"], "playback": "VIDEO_DECODED", "audio": True}
    report = run_case(candidate, playback)
    assert report["candidate_count"] == 1
    assert report["approved"] == report["spoken_turkish_verified"] == 0
    assert report["candidates"][0]["spoken_turkish_verified"] is False
    assert report["candidates"][0]["category"] == "LANGUAGE_REVIEW_WITH_METADATA_HINT"
    no_audio = run_case(candidate, {**playback, "audio": False})
    assert no_audio["candidates"][0]["category"] == "AUDIO_EVIDENCE_UNCONFIRMED_LANGUAGE_UNVERIFIED"
    no_video = run_case(candidate, {**playback, "playback": "REJECTED_PLAYBACK"})
    assert no_video["candidates"][0]["category"] == "PLAYBACK_UNAVAILABLE_LANGUAGE_UNVERIFIED"
    for broken, complete in [({**playback, "url_sha256": "b" * 64}, True), (playback, False)]:
        try:
            run_case(candidate, broken, complete)
        except SystemExit:
            pass
        else:
            raise AssertionError("Incomplete or mismatched evidence must fail closed")
    print("PASS: functional language-safety checks")

if __name__ == "__main__":
    main()
