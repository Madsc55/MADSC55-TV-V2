#!/usr/bin/env python3
"""Fail-closed Stage 4 acceptance gate. No production playlist mutations."""
import argparse
import hashlib
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

def verify_local_artifacts(data, evidence_path):
    """Verify supplied bytes; never equate a checksum match with live acceptance."""
    errors = []
    root = evidence_path.resolve().parent
    for key in ("discovery", "recovery", "real_video_audio", "encrypted_archive", "s3_restore", "end_to_end"):
        proof = data.get(key, {})
        if not isinstance(proof, dict):
            continue
        name = proof.get("artifact_file")
        if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
            errors.append(f"{key}: missing or unsafe artifact_file")
            continue
        file_path = (root / name).resolve()
        if not file_path.is_relative_to(root) or not file_path.is_file():
            errors.append(f"{key}: artifact not found within evidence directory")
            continue
        # Hash in bounded chunks: an untrusted artifact must not exhaust runner RAM.
        hasher = hashlib.sha256()
        with file_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        if digest.lower() != str(proof.get("artifact_sha256", "")).lower():
            errors.append(f"{key}: artifact bytes do not match declared SHA-256")
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
    for error in verify_local_artifacts(data, args.evidence):
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 1
    print("BLOCKED: manifest format alone cannot establish real video/audio, S3 restoration, or authentic Actions artifacts; independent evidence verification is required.", file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
