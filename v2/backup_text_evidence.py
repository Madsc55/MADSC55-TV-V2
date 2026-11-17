#!/usr/bin/env python3
"""Conservative OCR/subtitle evidence intake, without fetching or modifying streams.

Input is a bounded, externally produced observation. A detected Turkish token
is a review hint, never automatic approval or proof of a Turkish broadcaster.
"""
import re

MAX_TEXT = 4096
MAX_ITEMS = 100
TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")

def inspect_text_observations(observations):
    if not isinstance(observations, list) or len(observations) > MAX_ITEMS:
        raise ValueError("Invalid observation collection")
    evidence = []
    for obs in observations:
        if not isinstance(obs, dict) or obs.get("kind") not in ("OCR", "SUBTITLE"):
            raise ValueError("Invalid observation")
        value = obs.get("text")
        if not isinstance(value, str) or len(value) > MAX_TEXT:
            raise ValueError("Invalid observation text")
        language_tag = obs.get("language_tag", "")
        if not isinstance(language_tag, str) or len(language_tag) > 32:
            raise ValueError("Invalid language tag")
        # Neither a locale tag nor Turkish-looking letters alone prove language.
        marker = any(ch in TURKISH_CHARS for ch in value) or language_tag.lower().split("-")[0] == "tr"
        evidence.append({"kind": obs["kind"], "turkish_review_hint": marker,
                         "language_verified": False, "review_approved": False})
    return {"policy": "HINTS_ONLY_REVIEW_REQUIRED_NO_RAW_TEXT_OUTPUT",
            "observations": evidence, "language_evidence_verified": False,
            "review_approved": False}
