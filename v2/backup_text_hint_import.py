"""Validate anonymized OCR/subtitle batch reports as review hints only."""
import re

SHA256 = re.compile(r"^[0-9a-f]{64}$")
POLICY = "READ_ONLY_HINTS_ONLY_NO_AUTO_APPROVAL"

def import_text_hints(report, expected_ids=None):
    if not isinstance(report, dict) or report.get("policy") != POLICY or not isinstance(report.get("results"), list):
        raise ValueError("Invalid OCR/subtitle batch report")
    if len(report["results"]) > 16:
        raise ValueError("OCR/subtitle batch exceeds 16 samples")
    allowed = set(expected_ids) if expected_ids is not None else None
    result = {}
    for row in report["results"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid text hint record")
        key = row.get("url_sha256")
        if not isinstance(key, str) or not SHA256.fullmatch(key) or key in result:
            raise ValueError("Invalid or duplicate text hint identity")
        if allowed is not None and key not in allowed:
            raise ValueError("Unknown text hint identity")
        result[key] = {
            "url_sha256": key,
            "ocr_turkish_hint": row.get("ocr_hint") is True,
            "subtitle_turkish_hint": row.get("subtitle_hint") is True,
            "language_evidence_verified": False,
            "review_approved": False,
        }
    return result
