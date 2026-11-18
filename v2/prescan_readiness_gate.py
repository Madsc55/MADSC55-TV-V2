#!/usr/bin/env python3
"""Fail-closed pre-scan readiness gate; never launches discovery or edits playlists."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "v2/tasks/state.json"
REQUIRED = {15, 17, 18, 19, 20, 21, 28, 29, 30, 31, 32, 33, 34}

def inspect(state):
    statuses = state.get("statuses", [])
    by_id = {item["id"]: item for item in statuses}
    missing = sorted(REQUIRED - by_id.keys())
    pending = sorted(i for i in REQUIRED if i in by_id and by_id[i].get("status") != "completed")
    return {"ready": not missing and not pending, "missing": missing, "pending": pending,
            "state_generated_at": state.get("generated_at")}

def main():
    report = inspect(json.loads(STATE.read_text(encoding="utf-8")))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ready"]:
        raise SystemExit("BLOCKED: complete and independently verify open tasks before any new worldwide scan")

if __name__ == "__main__":
    main()
