#!/usr/bin/env python3
"""Offline, read-only batch triage of previously collected channel evidence.

Input JSONL fields: name, origin_country, spoken_language, subtitle_language,
video_decoded, audio_decoded, stream_checked. Output JSONL never contains URLs.
Does not fetch streams, edit M3U files, or approve channels.
"""
import argparse
import json
from pathlib import Path
try:
    from .turkish_channel_triage import classify_channel
except ImportError:
    from turkish_channel_triage import classify_channel

ALLOWED = {"name", "origin_country", "spoken_language", "subtitle_language",
           "video_decoded", "audio_decoded", "stream_checked"}
MAX_RECORDS = 20000
MAX_LINE = 8192

def prepare_review(input_path, output_path):
    source, target = Path(input_path), Path(output_path)
    if source.resolve() == target.resolve():
        raise ValueError("Input and output must differ")
    if target.exists():
        raise FileExistsError("Never overwrite an existing review")
    results = []
    with source.open("r", encoding="utf-8") as stream:
        for index, line in enumerate(stream, 1):
            if index > MAX_RECORDS or len(line) > MAX_LINE:
                raise ValueError("Evidence batch limit exceeded")
            data = json.loads(line)
            if not isinstance(data, dict) or "name" not in data or not set(data) <= ALLOWED:
                raise ValueError("Unexpected evidence record")
            result = classify_channel(**data)
            results.append({"source_row": index, **result})
    # Atomic create-exclusive output: no playlist files or input records touched.
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        for result in results:
            stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return {"reviewed": len(results), "approved": 0, "playlist_modified": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_review(args.input, args.output)))

if __name__ == "__main__":
    main()
