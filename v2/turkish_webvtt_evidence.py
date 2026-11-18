#!/usr/bin/env python3
"""Offline WebVTT language-evidence extraction for Turkish review.

Only explicit WebVTT LANGUAGE metadata counts. Subtitle text is not
speech recognition, OCR, or proof of channel/device playback.
"""
import re
from v2.turkish_evidence_ingest import evaluate_record

LANGUAGE = re.compile(r"^Language:\s*([A-Za-z]{2,3}(?:-[A-Za-z]{2,8})?)\s*$", re.I)
MAX_BYTES = 256 * 1024

def extract_webvtt(name, content):
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Invalid or oversized subtitle data")
    lines = content.lstrip("\ufeff").splitlines()
    if not lines or not re.match(r"^WEBVTT(?:[ \t].*)?$", lines[0]):
        raise ValueError("Not WebVTT")
    # Header ends at first blank line; cue text is never parsed as metadata.
    header = []
    for line in lines[1:]:
        if not line.strip():
            break
        header.append(line)
    languages = [m.group(1).lower() for line in header if (m := LANGUAGE.fullmatch(line.strip()))]
    if len(languages) != 1:
        raise ValueError("WebVTT requires exactly one explicit header language")
    result = evaluate_record({"name": name, "subtitle_language": languages[0],
                              "evidence_sources": ["webvtt"]})
    result["subtitle_evidence_type"] = "webvtt_header_language"
    return result
