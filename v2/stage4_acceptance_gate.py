#!/usr/bin/env python3
"""Fail-closed Stage 4 acceptance gate. No production playlist mutations."""
import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED = ("9", "13", "23")
SHA = re.compile(r"^[a-fA-F0-9]{64}$")
RUN = re.compile(r"^https://github\.com/Madsc55/MADSC55-TV-V2/actions/runs/[0-9]+(?:/.*)?$")

def check(data):
    errors = []
    if not isinstance(data, dict):
        return ["evidence must be a JSON object"]
    if data.get("repository") != "Madsc55/MADSC55-TV-V2":
        errors.append("repository identity mismatch")
    prerequisites = data.get("prerequisites")
    if not isinstance(prerequisites, dict):
        prerequisites = {}
    for task in REQUIRED:
        proof = prerequisites.get(task)
        if not isinstance(proof, dict) or proof.get("status") != "verified":
            errors.append(f"#{task} has no verified prerequisite")
            continue
        if not RUN.fullmatch(str(proof.get("actions_run", ""))):
            errors.append(f"#{task} missing Actions run URL")
    for key in ("discovery", "recovery", "real_video_audio", "encrypted_archive", "s3_restore", "end_to_end"):
        proof = data.get(key)
        if not isinstance(proof, dict) or proof.get("status") != "verified":
            errors.append(f"{key}: no verified real-run proof")
            continue
        if not RUN.fullmatch(str(proof.get("actions_run", ""))):
            errors.append(f"{key}: missing Actions run URL")
        if not SHA.fullmatch(str(proof.get("artifact_sha256", ""))):
            errors.append(f"{key}: missing artifact SHA-256")
    if data.get("main_ibo_unchanged") is not True:
        errors.append("main IBO immutability not confirmed")
    return errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"BLOCKED: cannot read evidence: {exc}", file=sys.stderr)
        return 1
    errors = check(data)
    if errors:
        for error in errors:
            print(f"BLOCKED: {error}", file=sys.stderr)
        return 1
    print("Evidence manifest structure verified; external run and artifact authenticity must also be independently checked.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
