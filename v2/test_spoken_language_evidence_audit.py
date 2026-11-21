#!/usr/bin/env python3
"""Offline regression checks for spoken-language evidence auditing."""
import importlib.util
import json
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("spoken_language_evidence_audit.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "sample.json"
        entries = [
            {"url_sha256": "a" * 64, "status": "LANGUAGE_MODEL_HINT_ONLY", "detected_language": "tr", "language_probability": 0.9, "speech_detected": True, "approved": False, "spoken_turkish_verified": False},
            {"url_sha256": "b" * 64, "status": "LANGUAGE_MODEL_HINT_ONLY", "detected_language": "en", "language_probability": 0.8, "speech_detected": True, "approved": False, "spoken_turkish_verified": False},
            {"url_sha256": "c" * 64, "status": "LANGUAGE_MODEL_HINT_ONLY", "detected_language": "tr", "language_probability": 0.7, "speech_detected": False, "approved": False, "spoken_turkish_verified": False},
            {"url_sha256": "d" * 64, "status": "AUDIO_SAMPLE_UNAVAILABLE", "approved": False},
        ]
        def write(rows):
            file.write_text(json.dumps({"policy": "READ_ONLY_SAMPLED_ASR_HINTS_REQUIRE_REVIEW", "sampled": len(rows), "results": rows}), encoding="utf-8")
        write(entries)
        result = audit.audit([file])
        assert result["unique_streams_reviewed"] == 4
        assert result["spoken_turkish_verified"] == 0
        assert all(v == 1 for v in result["categories"].values())
        for invalid in [entries + [entries[0]], [{**entries[0], "approved": True}], [{**entries[0], "language_probability": 1.5}], [{**entries[0], "status": "APPROVED"}]]:
            write(invalid)
            try:
                audit.audit([file])
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid language evidence accepted")
    print("PASS: spoken-language evidence audit fails closed")


if __name__ == "__main__":
    main()
