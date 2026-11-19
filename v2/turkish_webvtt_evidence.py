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

# FFmpeg emits plain, timestamped WebVTT cues when it decodes a text track.
_CUE_TIME = r"(?:(?:[0-9]{2,}):)?[0-5][0-9]:[0-5][0-9]\.[0-9]{3}"
_TIMING = re.compile(rf"^({_CUE_TIME})[ \t]+-->[ \t]+({_CUE_TIME})(?:[ \t].*)?$")


def _milliseconds(timestamp):
    hours, minutes, seconds = ("0:" + timestamp).split(":")[-3:]
    whole, fraction = seconds.split(".")
    return ((int(hours) * 60 + int(minutes)) * 60 + int(whole)) * 1000 + int(fraction)


def review_decoded_cues(content, language, duration_ms):
    """Review timed text belonging to a decoded track in this sample."""
    from v2.backup_text_evidence import inspect_text_observations
    from v2.turkish_channel_triage import TR_LANGUAGE

    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Invalid or oversized WebVTT")
    blocks = re.split(r"\n[ \t]*\n", content.replace("\r\n", "\n").lstrip("\ufeff"))
    if not blocks or not re.fullmatch(r"WEBVTT(?:[ \t].*)?", blocks[0].split("\n")[0]):
        raise ValueError("Missing WebVTT header")
    count = 0
    text_hint = False
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if not lines or lines[0].split(maxsplit=1)[0] in {"NOTE", "STYLE", "REGION"}:
            continue
        if "-->" not in lines[0]:
            lines = lines[1:]  # Optional cue identifier.
        match = _TIMING.fullmatch(lines[0]) if lines else None
        if not match:
            continue
        start, stop = map(_milliseconds, match.groups())
        text = re.sub(r"<[^>]*>", "", " ".join(lines[1:])).strip()
        if start >= min(stop, duration_ms) or not any(c.isalpha() for c in text):
            continue
        count += 1
        review = inspect_text_observations([{"kind": "SUBTITLE", "text": text[:4096]}])
        text_hint |= review["observations"][0]["turkish_review_hint"]
    return {"cue_count": count, "turkish_text_hint": text_hint,
            "tag_and_text_turkish_hint": language in TR_LANGUAGE and text_hint}
