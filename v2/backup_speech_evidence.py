#!/usr/bin/env python3
"""Conservative bridge from bounded ASR samples to archive review evidence.

ASR predictions are hints, never reviewed language proof. No URLs or transcript
text is retained. Explicit review must happen in a separate acceptance process.
"""
import re

SHA256 = re.compile(r"^[0-9a-f]{64}$")

def import_speech_hints(report, expected_ids=None):
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ValueError("Invalid speech report")
    if report.get("policy") != "READ_ONLY_SAMPLED_ASR_HINTS_REQUIRE_REVIEW":
        raise ValueError("Unrecognized speech evidence policy")
    if len(report["results"]) > 16:
        raise ValueError("Speech sample batch exceeds 16 samples")
    allowed = set(expected_ids) if expected_ids is not None else None
    output = {}
    for item in report["results"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid speech sample")
        digest = item.get("url_sha256")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest) or digest in output:
            raise ValueError("Invalid or duplicate speech identity")
        if allowed is not None and digest not in allowed:
            raise ValueError("Unknown speech identity")
        probability = item.get("language_probability")
        valid_probability = isinstance(probability, (float, int)) and not isinstance(probability, bool) and 0 <= probability <= 1
        turkish_hint = (item.get("status") == "LANGUAGE_MODEL_HINT_ONLY"
                        and item.get("detected_language") == "tr"
                        and item.get("speech_detected") is True and valid_probability)
        output[digest] = {"language": "UNKNOWN", "spoken_turkish_hint": turkish_hint,
                          "language_evidence_verified": False, "review_approved": False}
    return output
