#!/usr/bin/env python3
"""Audit speech-language sample artifacts without promoting probabilistic hints.

Offline only: reads JSON, never opens stream URLs or modifies playlists.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

VALID = {"LANGUAGE_MODEL_HINT_ONLY", "AUDIO_SAMPLE_UNAVAILABLE", "SAMPLE_ERROR"}


def audit(paths):
    seen = set()
    counts = Counter()
    total = 0
    for path in paths:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        if report.get("policy") != "READ_ONLY_SAMPLED_ASR_HINTS_REQUIRE_REVIEW":
            raise ValueError(f"Unexpected report policy: {path}")
        results = report.get("results")
        if not isinstance(results, list) or report.get("sampled") != len(results):
            raise ValueError(f"Invalid sample count: {path}")
        for entry in results:
            digest = entry.get("url_sha256")
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Invalid stream identity hash")
            if digest in seen:
                raise ValueError("Duplicate stream across artifacts")
            seen.add(digest)
            if entry.get("approved") is not False or entry.get("spoken_turkish_verified", False) is not False:
                raise ValueError("Unreviewed language hint cannot be approved")
            status = entry.get("status")
            if status not in VALID:
                raise ValueError("Unexpected language evidence status")
            if status == "LANGUAGE_MODEL_HINT_ONLY":
                language = entry.get("detected_language")
                probability = entry.get("language_probability")
                if not isinstance(language, str) or not language.isalpha() or not isinstance(probability, (int, float)) or isinstance(probability, bool) or not 0 <= probability <= 1:
                    raise ValueError("Invalid language model evidence")
                if entry.get("speech_detected") is not True:
                    category = "NO_SPEECH_CONFIRMED"
                elif language == "tr":
                    category = "TURKISH_MODEL_HINT_REVIEW_REQUIRED"
                else:
                    category = "OTHER_LANGUAGE_MODEL_HINT_REVIEW_REQUIRED"
            else:
                category = "AUDIO_UNAVAILABLE_OR_ERROR"
            counts[category] += 1
            total += 1
    return {
        "policy": "READ_ONLY_LANGUAGE_EVIDENCE_AUDIT_NO_AUTOMATIC_APPROVAL",
        "unique_streams_reviewed": total,
        "categories": dict(sorted(counts.items())),
        "spoken_turkish_verified": 0,
        "requires_human_or_independent_speech_validation": total,
        "limitations": "Model predictions do not establish spoken language; no stream is automatically promoted.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
