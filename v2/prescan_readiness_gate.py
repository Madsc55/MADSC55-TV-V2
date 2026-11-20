#!/usr/bin/env python3
"""Fail-closed pre-scan readiness gate; never launches discovery or edits playlists."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "v2/tasks/state.json"
# Task 34 contains the final live scan itself; requiring it here would deadlock.
# Keep all independent infrastructure prerequisites fail-closed.
REQUIRED = {15, 17, 18, 19, 20, 21, 28, 29, 30, 31, 32, 33}

def inspect(state):
    if not isinstance(state, dict) or state.get("schema") != 1 or state.get("canonical_state") != "state.json":
        return {"ready": False, "error": "INVALID_STATE_SCHEMA", "missing": sorted(REQUIRED), "pending": []}
    statuses = state.get("statuses", [])
    if not isinstance(statuses, list):
        return {"ready": False, "error": "INVALID_STATUSES", "missing": sorted(REQUIRED), "pending": []}
    if any(not isinstance(item, dict) or type(item.get("id")) is not int for item in statuses):
        return {"ready": False, "error": "INVALID_ENTRY", "missing": sorted(REQUIRED), "pending": []}
    ids = [item["id"] for item in statuses]
    if len(ids) != len(set(ids)):
        return {"ready": False, "error": "DUPLICATE_TASK_ID", "missing": [], "pending": []}
    by_id = {item["id"]: item for item in statuses}
    missing = sorted(REQUIRED - by_id.keys())
    pending = sorted(i for i in REQUIRED if i in by_id and by_id[i].get("status") != "completed")
    blockers = [{"id": i, "status": by_id[i].get("status"),
                 "blocker": by_id[i].get("blocker") or "No blocker recorded"}
                for i in pending]
    return {"ready": not missing and not pending, "missing": missing, "pending": pending,
            "blockers": blockers, "state_generated_at": state.get("generated_at")}

def require_readiness():
    report = inspect(json.loads(STATE.read_text(encoding="utf-8")))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ready"]:
        raise SystemExit("BLOCKED: complete and independently verify open tasks before any new worldwide scan")


if __name__ == "__main__":
    require_readiness()
