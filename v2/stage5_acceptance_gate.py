#!/usr/bin/env python3
"""Stage 5 evidence gate: validates post-discovery acceptance without scanning channels."""
import argparse
import json
from pathlib import Path

REQUIRED = {
    "31": ("grouped_actions_run_url", "discovery_batch_id", "real_av_evidence_url",
           "encrypted_archive_url", "independent_restore_evidence_url", "playlist_immutability_evidence_url"),
    "32": ("device_model", "device_test_date", "device_video_evidence_url",
           "device_audio_evidence_url", "user_approval"),
    "33": ("final_archive_url", "final_archive_sha256", "final_restore_evidence_url",
           "final_report_url"),
}

def evaluate(record):
    tasks = record.get("tasks", {})
    result = {}
    for number, fields in REQUIRED.items():
        data = tasks.get(number, {})
        missing = [key for key in fields if not data.get(key)]
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
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["all_accepted"] else 2)

if __name__ == "__main__":
    main()
