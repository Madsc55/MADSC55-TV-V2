#!/usr/bin/env python3
"""Offline adapter for externally produced ASR/OCR language observations.

No speech recognition or image recognition runs here. Never treat a model's
unattributed guess, a channel name, or OCR text as verified spoken language.
"""
from v2.turkish_evidence_ingest import evaluate_record

SOURCES = {"asr", "ocr"}
MAX_TEXT = 4096

def evaluate_observation(name, observation):
    if not isinstance(observation, dict) or set(observation) != {"source", "language", "text"}:
        raise ValueError("Observation requires source, language and text")
    source, language, text = (observation[k] for k in ("source", "language", "text"))
    if source not in SOURCES or not isinstance(language, str) or not 2 <= len(language) <= 16:
        raise ValueError("Invalid observation source or language")
    import re
    if not re.fullmatch(r"[a-zA-Z]{2,3}(?:-[a-zA-Z]{2,8})?", language):
        raise ValueError("Invalid language tag")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise ValueError("Missing or oversized observation text")
    if any(ord(c) < 32 and c not in "\n\t" for c in text):
        raise ValueError("Invalid observation text")
    record = {"name": name, "evidence_sources": [source]}
    if source == "asr":
        record["spoken_language"] = language
    else:
        # OCR of visible text is NOT subtitle evidence: do not invent subtitles.
        # OCR remains separate and cannot set spoken_language or subtitle_language.
        record["evidence_sources"] = ["ocr"]
    result = evaluate_record(record)
    result["observation_source"] = source
    result["observed_language"] = language.lower()
    result["observed_language_is_verified"] = False
    result["observation_provenance"] = source
    result["observed_text_length"] = len(text)
    result["observation_text_retained"] = False
    result["ocr_text_is_not_subtitle_or_speech"] = source == "ocr"
    return result

def review_observation_batch(records):
    """Review already-produced ASR/OCR observations; no recognition or network."""
    if not isinstance(records, list) or len(records) > 20000:
        raise ValueError("Expected at most 20000 observations")
    results = []
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {"channel_id", "name", "observation"}:
            raise ValueError("Invalid observation record")
        channel_id = record["channel_id"]
        if not isinstance(channel_id, str) or not channel_id.strip() or len(channel_id) > 256:
            raise ValueError("Invalid channel ID")
        if channel_id in seen:
            raise ValueError("Duplicate channel ID")
        seen.add(channel_id)
        results.append({"channel_id": channel_id,
                        **evaluate_observation(record["name"], record["observation"])})
    return {"count": len(results),
            "turkish_spoken_candidates": sum(r["turkish_spoken_hint"] for r in results),
            "approved": 0, "playlist_modified": False, "results": results}
