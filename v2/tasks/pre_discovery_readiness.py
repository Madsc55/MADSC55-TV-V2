#!/usr/bin/env python3
"""Read-only system readiness check; never starts channel discovery or changes playlists."""
import argparse
import json
from pathlib import Path

# Post-discovery acceptance depends on newly discovered streams and device evidence.
POST_DISCOVERY = frozenset({15, 17, 18, 19, 20, 21, 28, 29, 30, 31, 32, 33, 34})

def check(state, tasks):
    statuses = {int(x["id"]): x["status"] for x in state["statuses"]}
    specs = {int(x["id"]): x for x in tasks["tasks"]}
    unknown = sorted(set(statuses) ^ set(specs))
    system_ids = sorted(set(specs) - POST_DISCOVERY)
    unfinished = [i for i in system_ids if statuses.get(i) != "completed"]
    blocked = {}
    for i in unfinished:
        unmet = [d for d in specs[i].get("depends_on", [])
                 if d in system_ids and statuses.get(d) != "completed"]
        if unmet:
            blocked[str(i)] = unmet
    return {
        "recorded_system_tasks_complete": not unfinished and not unknown,
        "system_ready": False,
        "system_tasks": len(system_ids),
        "system_unfinished": unfinished,
        "blocked_by_system_dependencies": blocked,
        "post_discovery_or_discovery_tasks": sorted(POST_DISCOVERY & set(specs)),
        "task_id_mismatch": unknown,
        "note": "Recorded statuses alone cannot establish system readiness: latest grouped Actions and deployment evidence must be checked separately. No discovery, real AV, device or archive acceptance is claimed."
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=Path("v2/tasks/state.json"))
    parser.add_argument("--tasks", type=Path, default=Path("v2/tasks/master_tasks.json"))
    args = parser.parse_args()
    result = check(json.loads(args.state.read_text(encoding="utf-8")),
                   json.loads(args.tasks.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["recorded_system_tasks_complete"] else 2)

if __name__ == "__main__":
    main()
