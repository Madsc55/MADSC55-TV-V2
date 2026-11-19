#!/usr/bin/env python3
"""Bounded local-media ffprobe bridge for Turkish subtitle-track review.

Only an existing local regular media file is accepted. This does not perform
ASR, OCR, network requests, playlist writes or device verification.
"""
import json
from pathlib import Path
import shutil
import subprocess
from v2.turkish_subtitle_track_review import review_tracks

MAX_INPUT_BYTES = 12 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024

def validate_sample(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".mkv":
        raise ValueError("Expected existing regular MKV sample")
    if not 0 < path.stat().st_size <= MAX_INPUT_BYTES:
        raise ValueError("Sample size outside bounds")
    return path


def probe_local_sample(path, *, runner=subprocess.run, which=shutil.which):
    path = validate_sample(path)
    executable = which("ffprobe")
    if not executable:
        return {"status": "FFPROBE_UNAVAILABLE", "playlist_modified": False,
                "review_approved": False}
    command = [executable, "-v", "error", "-protocol_whitelist", "file",
               "-f", "matroska", "-show_entries",
               "stream=index,codec_type:stream_tags=language", "-of", "json",
               str(path.resolve())]
    try:
        result = runner(command, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "PROBE_FAILED", "playlist_modified": False,
                "review_approved": False}
    if result.returncode != 0 or not isinstance(result.stdout, bytes) or len(result.stdout) > MAX_JSON_BYTES:
        return {"status": "PROBE_FAILED", "playlist_modified": False,
                "review_approved": False}
    try:
        report = review_tracks(json.loads(result.stdout.decode("utf-8")))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "PROBE_FAILED", "playlist_modified": False,
                "review_approved": False}
    return {"status": "TRACK_METADATA_REVIEW_ONLY", **report}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True)
    args = parser.parse_args()
    print(json.dumps(probe_local_sample(args.sample), ensure_ascii=False, sort_keys=True))
