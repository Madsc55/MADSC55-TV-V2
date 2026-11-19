#!/usr/bin/env python3
"""Read-only review of subtitle track language tags from existing ffprobe JSON.

Track metadata is a hint, not evidence that Turkish subtitles appeared on screen.
No network, subprocess, playlist or archive writes.
"""
import json
from pathlib import Path

MAX_BYTES = 1024 * 1024
TURKISH = {"tr", "tur", "tr-tr"}

def review_tracks(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("streams"), list):
        raise ValueError("Expected ffprobe streams array")
    if len(payload["streams"]) > 512:
        raise ValueError("Too many streams")
    result = []
    for stream in payload["streams"]:
        if not isinstance(stream, dict):
            raise ValueError("Invalid stream")
        if stream.get("codec_type") != "subtitle":
            continue
        tags = stream.get("tags", {})
        if not isinstance(tags, dict):
            raise ValueError("Invalid subtitle tags")
        language = tags.get("language", "und")
        if not isinstance(language, str) or len(language) > 32:
            raise ValueError("Invalid subtitle language")
        language = language.strip().lower()
        index = stream.get("index")
        if type(index) is not int or index < 0:
            raise ValueError("Invalid subtitle index")
        result.append({"stream_index": index, "language_tag": language,
                       "turkish_subtitle_track_hint": language in TURKISH,
                       "subtitle_content_verified": False,
                       "language_evidence_verified": False,
                       "review_approved": False})
    if len({row["stream_index"] for row in result}) != len(result):
        raise ValueError("Duplicate subtitle index")
    return {"subtitle_tracks": result,
            "turkish_subtitle_track_candidates": sum(row["turkish_subtitle_track_hint"] for row in result),
            "playlist_modified": False, "review_approved": False}

def review_file(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Oversized ffprobe data")
    return review_tracks(json.loads(path.read_text(encoding="utf-8")))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffprobe-json", required=True)
    args = parser.parse_args()
    print(json.dumps(review_file(args.ffprobe_json), ensure_ascii=False, sort_keys=True))
