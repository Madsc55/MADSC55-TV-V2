#!/usr/bin/env python3
"""Fail-closed Stage C acceptance gate. Does not modify production or task state."""
import argparse
import hashlib
import json
import pathlib
import sys

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def evidence_file(root, record, field):
    item = record.get(field)
    require(isinstance(item, dict), f"{field}: missing file record")
    name, digest = item.get("path"), item.get("sha256")
    require(isinstance(name, str) and name and not pathlib.PurePath(name).is_absolute(), f"{field}: unsafe path")
    require(isinstance(digest, str) and len(digest) == 64, f"{field}: missing SHA-256")
    target = (root / name).resolve()
    require(target.is_relative_to(root.resolve()) and target.is_file(), f"{field}: missing or escaping file")
    require(sha256(target) == digest.lower(), f"{field}: SHA-256 mismatch")

def load(path):
    require(path.is_file(), f"missing evidence: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), f"invalid evidence: {path}")
    return data

def validate_device(root, record):
    require(record.get("passed") is True, "device: not passed")
    require(record.get("environment") == "physical_android", "device: not physical Android")
    require(record.get("mock") is False, "device: mock status missing or true")
    require(record.get("device_id") and record.get("player_version"), "device: identity/version missing")
    require(record.get("started_at") and record.get("finished_at"), "device: timestamps missing")
    sessions = record.get("sessions")
    require(isinstance(sessions, list) and sessions, "device: no playback sessions")
    for i, session in enumerate(sessions):
        require(session.get("channel_id") and session.get("video_ok") is True and session.get("audio_ok") is True,
                f"device: session {i} lacks simultaneous video/audio proof")
        require(session.get("same_session") is True, f"device: session {i} not same playback")
        evidence_file(root, session, "capture")

def validate_restore(root, record):
    require(record.get("passed") is True, "restore: not passed")
    require(record.get("environment") == "independent_isolated", "restore: not independent")
    require(record.get("mock") is False, "restore: mock status missing or true")
    require(record.get("source_archive_sha256") and len(record["source_archive_sha256"]) == 64, "restore: archive SHA missing")
    require(record.get("archive_integrity_passed") is True, "restore: archive integrity failed")
    require(record.get("decryption_passed") is True, "restore: decryption failed")
    require(record.get("source_count") == record.get("restored_count"), "restore: count mismatch")
    require(isinstance(record.get("restored_count"), int) and record["restored_count"] > 0, "restore: empty restore")
    require(record.get("missing_count") == 0 and record.get("corrupt_count") == 0 and record.get("duplicate_count") == 0,
            "restore: missing/corrupt/duplicate records")
    require(record.get("started_at") and record.get("finished_at"), "restore: timestamps missing")
    evidence_file(root, record, "restore_log")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--evidence-dir", type=pathlib.Path, required=True)
    p.add_argument("--output", type=pathlib.Path, help="optional report JSON (not a state update)")
    args = p.parse_args()
    root = args.evidence_dir.resolve()
    checks = {}
    for name, validator in (("device", validate_device), ("restore", validate_restore)):
        try:
            validator(root, load(root / (name + ".json")))
            checks[name] = {"passed": True}
        except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            checks[name] = {"passed": False, "error": str(exc)}
    report = {"passed": all(x["passed"] for x in checks.values()), "checks": checks,
              "note": "This gate does not update task state; independent review and package checks remain required."}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
