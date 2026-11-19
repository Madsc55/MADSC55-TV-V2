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

def review_batch(payload):
    """Review already-collected channel probe metadata; never fetch streams."""
    if not isinstance(payload, list) or len(payload) > 20000:
        raise ValueError("Expected at most 20000 channel observations")
    reviewed = []
    seen = set()
    for record in payload:
        if not isinstance(record, dict) or set(record) != {"channel_id", "ffprobe"}:
            raise ValueError("Invalid channel observation")
        channel_id = record["channel_id"]
        if not isinstance(channel_id, str) or not channel_id.strip() or len(channel_id) > 256:
            raise ValueError("Invalid channel ID")
        if channel_id in seen:
            raise ValueError("Duplicate channel ID")
        seen.add(channel_id)
        tracks = review_tracks(record["ffprobe"])
        reviewed.append({"channel_id": channel_id, **tracks})
    return {"count": len(reviewed),
            "candidate_channels": sum(row["turkish_subtitle_track_candidates"] > 0 for row in reviewed),
            "approved": 0, "playlist_modified": False, "results": reviewed}


def review_batch_file(path):
    path = Path(path)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Oversized batch")
    return review_batch(json.loads(path.read_text(encoding="utf-8")))


def review_file(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Oversized ffprobe data")
    return review_tracks(json.loads(path.read_text(encoding="utf-8")))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ffprobe-json")
    group.add_argument("--batch-json")
    args = parser.parse_args()
    result = review_batch_file(args.batch_json) if args.batch_json else review_file(args.ffprobe_json)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
