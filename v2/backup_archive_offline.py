#!/usr/bin/env python3
"""Offline, read-only evidence join entrypoint for the smart backup archive.

No stream probing, playlist writes, or automatic promotion.
"""
import argparse
import json
from pathlib import Path
try:
    from .backup_evidence_adapter import join_evidence
    from .backup_speech_evidence import import_speech_hints
    from .backup_text_hint_import import import_text_hints
except ImportError:
    from backup_evidence_adapter import join_evidence
    from backup_speech_evidence import import_speech_hints
    from backup_text_hint_import import import_text_hints

def load(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data

def run(inventory_path, playback_path, language_path, output_path, expected_count, speech_path=None, text_path=None):
    inputs = [p.resolve() for p in (inventory_path, playback_path, language_path)]
    if speech_path is not None:
        inputs.append(speech_path.resolve())
    if text_path is not None:
        inputs.append(text_path.resolve())
    if output_path.resolve() in inputs or output_path.exists():
        raise ValueError("Refusing to overwrite evidence inputs or existing report")
    inventory = load(inventory_path).get("channels")
    playback = load(playback_path).get("by_url_sha256")
    language = load(language_path).get("by_url_sha256")
    if not isinstance(inventory, list) or not isinstance(playback, dict) or not isinstance(language, dict):
        raise ValueError("Expected channels and by_url_sha256 maps")
    if speech_path is not None:
        speech = import_speech_hints(load(speech_path), {x["url_sha256"] for x in inventory})
        # ASR predictions are review hints only; they cannot overwrite approvals.
        language = {key: dict(value) for key, value in language.items()}
        for key, hint in speech.items():
            current = language.setdefault(key, {})
            if not isinstance(current, dict):
                raise ValueError("Invalid language record")
            current["spoken_turkish_hint"] = hint["spoken_turkish_hint"]
    report = join_evidence(inventory, playback, language, expected_count)
    if speech_path is not None:
        # Expose only review queue hints, never a verified-language verdict.
        report["speech_review_hints"] = [
            {"url_sha256": key, "spoken_turkish_hint": hint["spoken_turkish_hint"],
             "language_evidence_verified": False}
            for key, hint in sorted(speech.items())
        ]
        report["speech_review_hint_count"] = sum(
            item["spoken_turkish_hint"] for item in report["speech_review_hints"]
        )
    if text_path is not None:
        text_hints = import_text_hints(load(text_path), {x["url_sha256"] for x in inventory})
        report["text_review_hints"] = [text_hints[key] for key in sorted(text_hints)]
        report["ocr_review_hint_count"] = sum(x["ocr_turkish_hint"] for x in text_hints.values())
        report["subtitle_review_hint_count"] = sum(x["subtitle_turkish_hint"] for x in text_hints.values())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as destination:
        destination.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {"total": report["total"], "counts": report["counts"]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--playback", required=True, type=Path)
    parser.add_argument("--language", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--speech", type=Path, help="Optional bounded ASR hint report")
    parser.add_argument("--text-hints", type=Path, help="Optional OCR/subtitle batch hint report")
    parser.add_argument("--expected-count", type=int, default=18074)
    args = parser.parse_args()
    if args.expected_count < 1:
        parser.error("expected-count must be positive")
    print(json.dumps(run(args.inventory, args.playback, args.language, args.output, args.expected_count, args.speech, args.text_hints)))

if __name__ == "__main__":
    main()
