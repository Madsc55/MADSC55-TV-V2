#!/usr/bin/env python3
"""Offline, read-only evidence join entrypoint for the smart backup archive.

No stream probing, playlist writes, or automatic promotion.
"""
import argparse
import json
from pathlib import Path
try:
    from .backup_evidence_adapter import join_evidence
except ImportError:
    from backup_evidence_adapter import join_evidence

def load(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data

def run(inventory_path, playback_path, language_path, output_path, expected_count):
    inputs = [p.resolve() for p in (inventory_path, playback_path, language_path)]
    if output_path.resolve() in inputs:
        raise ValueError("Refusing to overwrite evidence inputs")
    inventory = load(inventory_path).get("channels")
    playback = load(playback_path).get("by_url_sha256")
    language = load(language_path).get("by_url_sha256")
    if not isinstance(inventory, list) or not isinstance(playback, dict) or not isinstance(language, dict):
        raise ValueError("Expected channels and by_url_sha256 maps")
    report = join_evidence(inventory, playback, language, expected_count)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"total": report["total"], "counts": report["counts"]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--playback", required=True, type=Path)
    parser.add_argument("--language", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-count", type=int, default=18074)
    args = parser.parse_args()
    if args.expected_count < 1:
        parser.error("expected-count must be positive")
    print(json.dumps(run(args.inventory, args.playback, args.language, args.output, args.expected_count)))

if __name__ == "__main__":
    main()
