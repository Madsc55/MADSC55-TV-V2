#!/usr/bin/env python3
"""Join existing playback and language evidence without altering channel inventories.

Only verified language evidence is promoted; metadata and model hints remain
review signals. No raw stream URLs are emitted.
"""
from .backup_smart_archive import build_report

AUDIO_OK = {"AUDIO_DECODED", "AUDIO_PRESENT", "PRESENT", "YES", "TRUE"}
def join_evidence(inventory, playback, language_evidence, expected_count=None):
    if not isinstance(inventory, list) or not isinstance(playback, dict) or not isinstance(language_evidence, dict):
        raise ValueError("Invalid evidence inputs")
    if any(not isinstance(x, dict) for x in inventory):
        raise ValueError("Invalid inventory record")
    if len(inventory) != len({x.get("url_sha256") for x in inventory}):
        raise ValueError("Duplicate inventory IDs")
    ids = {x["url_sha256"] for x in inventory}
    if expected_count is not None and len(ids) != expected_count:
        raise ValueError("Incomplete inventory")
    if set(playback) - ids or set(language_evidence) - ids:
        raise ValueError("Evidence references unknown channels")
    rows = []
    for item in inventory:
        key = item["url_sha256"]
        av = playback.get(key, {})
        lang = language_evidence.get(key, {})
        if not isinstance(av, dict) or not isinstance(lang, dict):
            raise ValueError("Invalid evidence record")
        video = av.get("playback") == "VIDEO_DECODED"
        audio = str(av.get("audio", "")).upper() in AUDIO_OK
        decoded = av.get("decoded_av_verified") is True and video and audio
        # A single failure, timeout, or geo-block never proves a dead channel.
        exhausted = av.get("retries_exhausted") is True and av.get("terminal_failure_verified") is True
        health = "WORKING" if decoded else ("NOT_WORKING" if exhausted else "UNKNOWN")
        # Speech model hints, OCR and subtitles alone do not establish broadcaster nationality.
        language = lang.get("language", "UNKNOWN")
        verified = lang.get("language_evidence_verified") is True and lang.get("review_approved") is True
        rows.append({"url_sha256": key, "health": health, "decoded_av_verified": decoded,
                     "retries_exhausted": exhausted, "language": language,
                     "language_evidence_verified": verified})
    return build_report(rows, expected_count)
