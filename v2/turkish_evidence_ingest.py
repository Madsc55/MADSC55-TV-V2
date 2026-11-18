#!/usr/bin/env python3
"""Fail-closed, read-only ingestion of externally measured Turkish media evidence.

Evidence is untrusted input, not an approval or a playlist mutation. This module
does not probe streams, infer language from metadata, or claim device playback.
"""
import json
from pathlib import Path
from v2.turkish_channel_triage import classify_channel

ALLOWED = {"name", "origin_country", "spoken_language", "subtitle_language",
           "stream_checked", "video_decoded", "audio_decoded", "evidence_sources"}
SOURCES = {"ffmpeg", "ffprobe", "asr", "ocr", "webvtt", "broadcaster_metadata"}

def evaluate_record(record):
    if not isinstance(record, dict) or set(record) - ALLOWED:
        raise ValueError("Invalid evidence fields")
    if not isinstance(record.get("name"), str):
        raise ValueError("Missing channel name")
    sources = record.get("evidence_sources", [])
    if not isinstance(sources, list) or len(sources) != len(set(map(str, sources))) or any(
        not isinstance(s, str) or s not in SOURCES for s in sources
    ):
        raise ValueError("Invalid evidence sources")
    for key in ("stream_checked", "video_decoded", "audio_decoded"):
        if key in record and type(record[key]) is not bool:
            raise ValueError("Invalid media flag")
    if record.get("spoken_language") and "asr" not in sources:
        raise ValueError("Spoken language requires ASR provenance")
    if record.get("subtitle_language") and not ({"webvtt", "ocr"} & set(sources)):
        raise ValueError("Subtitle language requires WebVTT/OCR provenance")
    if any(record.get(k, False) for k in ("video_decoded", "audio_decoded", "stream_checked")) and not (
        {"ffmpeg", "ffprobe"} & set(sources)
    ):
        raise ValueError("AV flags require decoder provenance")
    result = classify_channel(**{k: record[k] for k in ALLOWED - {"evidence_sources"} if k in record})
    return {"name": record["name"], "evidence_sources": sorted(sources), **result}

def evaluate_file(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Input and output must differ")
    if source.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Input too large")
    records = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) > 20000:
        raise ValueError("Expected at most 20000 records")
    results = [evaluate_record(item) for item in records]
    output.write_text(json.dumps({"count": len(results), "approved": 0,
                                  "playlist_modified": False, "results": results},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(results)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print("reviewed", evaluate_file(args.input, args.output))
