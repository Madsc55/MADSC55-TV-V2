#!/usr/bin/env python3
"""Stage 5 evidence gate: validates post-discovery acceptance without scanning channels."""
import argparse
import ipaddress
import json
import re
from urllib.parse import urlsplit
from pathlib import Path

REQUIRED = {
    "31": ("grouped_actions_run_url", "discovery_batch_id", "real_av_evidence_url",
           "encrypted_archive_url", "independent_restore_evidence_url", "playlist_immutability_evidence_url"),
    "32": ("device_model", "device_test_date", "device_video_evidence_url",
           "device_audio_evidence_url", "user_approval"),
    "33": ("final_archive_url", "final_archive_sha256", "final_restore_evidence_url",
           "final_report_url"),
}

def _valid_evidence_url(value):
    if (not isinstance(value, str) or not value.strip()
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        _ = parsed.port
        if (parsed.scheme != "https" or not host or parsed.username is not None
                or parsed.password is not None):
            return False
        host = host.lower().rstrip(".")
        if (host in {"example.org", "example.com", "localhost"}
                or host.endswith((".invalid", ".test", ".example", ".localhost",
                                  ".local", ".internal"))):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return True
        return address.is_global
    except ValueError:
        return False


def evaluate(record):
    if not isinstance(record, dict):
        raise ValueError("Invalid acceptance report")
    tasks = record.get("tasks", {})
    if not isinstance(tasks, dict):
        raise ValueError("Invalid acceptance tasks mapping")
    result = {}
    for number, fields in REQUIRED.items():
        data = tasks.get(number, {})
        if not isinstance(data, dict):
            raise ValueError("Invalid acceptance task entry " + number)
        missing = [key for key in fields if not data.get(key)]
        for key in fields:
            if key.endswith("_url") and key not in missing and not _valid_evidence_url(data[key]):
                missing.append(key + "_invalid_https")
        if number == "33" and not re.fullmatch(r"[a-fA-F0-9]{64}", str(data.get("final_archive_sha256", ""))):
            missing.append("final_archive_sha256_invalid")
        if number == "31" and data.get("real_world_checks_passed") is not True:
            missing.append("real_world_checks_passed_required")
        if number == "32" and data.get("device_test_confirmed_by_user") is not True:
            missing.append("device_test_confirmed_by_user_required")
        if number == "33" and data.get("archive_restore_verified") is not True:
            missing.append("archive_restore_verified_required")
        if number == "31" and data.get("discovery_batch_id") == "legacy":
            missing.append("new_discovery_batch_required")
        if number == "32" and data.get("user_approval") is not True:
            missing.append("explicit_user_approval_required")
        if number == "32" and result.get("31", {}).get("accepted") is not True:
            missing.append("task_31_acceptance_required")
        if number == "33" and not all(result.get(n, {}).get("accepted") for n in ("31", "32")):
            missing.append("tasks_31_and_32_acceptance_required")
        result[number] = {"accepted": not missing, "missing": sorted(set(missing))}
    return {"all_accepted": all(x["accepted"] for x in result.values()), "tasks": result}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.evidence.read_text(encoding="utf-8")))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(rendered + "\n")
    print(rendered)
    raise SystemExit(0 if result["all_accepted"] else 2)

if __name__ == "__main__":
    main()
