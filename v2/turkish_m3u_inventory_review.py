#!/usr/bin/env python3
"""Offline M3U inventory -> read-only Turkish channel review.

No stream URLs in output, no network, no mutation of the source playlist.
Each EXTINF record receives a stable 1-based ordinal, including non-Turkish
channels. Source title/group are *hints*, never verified country/language.
"""
import argparse
import json
import re
from pathlib import Path
try:
    from .turkish_channel_triage import classify_channel
except ImportError:
    from turkish_channel_triage import classify_channel

MAX_CHANNELS = 25000
MAX_BYTES = 32 * 1024 * 1024
EVIDENCE_FIELDS = {"origin_country", "spoken_language", "subtitle_language", "video_decoded", "audio_decoded", "stream_checked"}
SAMPLER_FIELDS = {"url_sha256", "status", "video_decoded", "audio_decoded", "asr_status", "spoken_turkish_hint", "ocr_turkish_hint", "subtitle_turkish_hint"}

def load_evidence(path):
    if path is None:
        return {}
    evidence = {}
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if len(line) > 8192 or len(evidence) >= MAX_CHANNELS:
                raise ValueError("Evidence limit exceeded")
            item = json.loads(line)
            if not isinstance(item, dict) or set(item) - (EVIDENCE_FIELDS | {"playlist_ordinal", "sample_report"}):
                raise ValueError("Unexpected evidence fields")
            ordinal = item.get("playlist_ordinal")
            if type(ordinal) is not int or ordinal < 1 or ordinal in evidence:
                raise ValueError("Invalid or duplicate playlist ordinal")
            sampler = item.get("sample_report")
            if sampler is not None:
                if not isinstance(sampler, dict) or not isinstance(sampler.get("url_sha256"), str) or len(sampler["url_sha256"]) != 64:
                    raise ValueError("Invalid sampler report")
                if any(type(sampler.get(k)) is not bool for k in ("video_decoded", "audio_decoded", "spoken_turkish_hint", "subtitle_turkish_hint")):
                    raise ValueError("Invalid sampler booleans")
                item["video_decoded"] = sampler["video_decoded"]
                item["audio_decoded"] = sampler["audio_decoded"]
                item["stream_checked"] = sampler.get("status") in ("AV_SAMPLED_REVIEW_REQUIRED", "AV_INCOMPLETE")
                # ASR/subtitle observations are hints, never verified languages.
            evidence[ordinal] = {k: v for k, v in item.items() if k in EVIDENCE_FIELDS}
            if sampler is not None:
                evidence[ordinal]["_sampler_hints"] = {"spoken_turkish_hint": sampler["spoken_turkish_hint"], "subtitle_turkish_hint": sampler["subtitle_turkish_hint"]}
    return evidence

GROUP_RE = re.compile(r'group-title="([^"]{0,256})"')

def inventory_review(playlist, output, evidence_path=None):
    playlist, output = Path(playlist), Path(output)
    if playlist.resolve() == output.resolve():
        raise ValueError("Output cannot replace input")
    if output.exists():
        raise FileExistsError("Review output already exists")
    if playlist.stat().st_size > MAX_BYTES:
        raise ValueError("Playlist too large")
    evidence = load_evidence(evidence_path)
    rows = []
    pending = None
    with playlist.open(encoding="utf-8-sig", errors="replace") as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                if pending is not None:
                    raise ValueError("Unpaired EXTINF entry")
                if "," not in line:
                    raise ValueError("Missing channel title")
                title = line.rsplit(",", 1)[1].strip()
                group_match = GROUP_RE.search(line)
                pending = (title, group_match.group(1) if group_match else "")
            elif line and not line.startswith("#") and pending is not None:
                title, group = pending
                pending = None
                if len(rows) >= MAX_CHANNELS:
                    raise ValueError("Channel limit exceeded")
                supplied = dict(evidence.get(len(rows) + 1, {}))
                sampler_hints = supplied.pop("_sampler_hints", None)
                triage = classify_channel(title, **supplied)
                if sampler_hints is not None:
                    triage["sampler_spoken_turkish_hint"] = sampler_hints["spoken_turkish_hint"]
                    triage["sampler_subtitle_turkish_hint"] = sampler_hints["subtitle_turkish_hint"]
                rows.append({"playlist_ordinal": len(rows) + 1,
                             "source_group": group,
                             "title": title,
                             **triage})
    if pending is not None:
        raise ValueError("Unpaired final EXTINF entry")
    if any(i > len(rows) for i in evidence):
        raise ValueError("Evidence refers to a missing channel")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"channels": len(rows), "approved": 0, "playlist_modified": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, help="Optional trusted per-ordinal JSONL evidence")
    args = parser.parse_args()
    print(json.dumps(inventory_review(args.playlist, args.output, args.evidence)))

if __name__ == "__main__":
    main()
