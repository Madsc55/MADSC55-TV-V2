#!/usr/bin/env python3
"""Convert existing AV probe results into review-only Turkish evidence.

No network, ASR inference, OCR inference, device approval, or playlist writes.
"""
from v2.turkish_evidence_ingest import evaluate_record

def from_probe(name, probe_result, *, origin_country=None):
    if not isinstance(probe_result, dict):
        raise ValueError("Probe result must be an object")
    status = probe_result.get("status")
    decoded = probe_result.get("decoded_av_verified")
    if type(decoded) is not bool:
        raise ValueError("Missing explicit decoded AV flag")
    if status == "AV_VERIFIED" and decoded is not True:
        raise ValueError("Contradictory AV status")
    if decoded is True and status != "AV_VERIFIED":
        raise ValueError("Unverified AV status")
    record = {"name": name, "evidence_sources": ["ffprobe", "ffmpeg"],
              "stream_checked": decoded is True,
              "video_decoded": decoded is True,
              "audio_decoded": decoded is True}
    if origin_country is not None:
        record["origin_country"] = origin_country
        record["evidence_sources"].append("broadcaster_metadata")
    result = evaluate_record(record)
    result["probe_status"] = status
    return result
