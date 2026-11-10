#!/usr/bin/env python3
"""Read-only, fail-closed MADSC55 V2 task selection and evidence checks."""
import argparse
import json
import re
from pathlib import Path, PurePosixPath

STATUSES = {"pending", "in_progress", "blocked", "completed"}
REPO = "Madsc55/MADSC55-TV-V2"
BRANCH = "madsc/v2-discovery-bulk-20261031"
PROTECTED = {"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"}
PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
# User-directed scheduling only; does not change dependencies or completion criteria.
DEFERRED_LAST = frozenset()
OPTIONAL_SCOPE = "deferred_optional"


def validate(master, ledger, root):
    if root.get("repository") != REPO or root.get("branch") != BRANCH:
        raise ValueError("Wrong repository or branch")
    if root.get("task_tracking", {}).get("task_ledger") != "v2/tasks/state.json":
        raise ValueError("Canonical state link missing")
    tasks = master["tasks"]
    if len(tasks) != 34 or [t["id"] for t in tasks] != list(range(1, 35)):
        raise ValueError("Must register exactly 34 ordered tasks")
    if master.get("repository") != REPO or master.get("branch") != BRANCH:
        raise ValueError("Wrong task manifest target")
    by_id = {t["id"]: t for t in tasks}
    for t in tasks:
        if t.get("scope") == OPTIONAL_SCOPE:
            raise ValueError("All 34 tasks are mandatory; deferred scope is forbidden")
        if t["priority"] not in PRIORITY or not t["acceptance"] or not isinstance(t["evidence_urls"], list):
            raise ValueError("Incomplete task acceptance or priority")
        if any(d not in by_id or d == t["id"] for d in t["depends_on"]):
            raise ValueError("Invalid dependency")
    visiting, visited = set(), set()
    def visit(i):
        if i in visiting:
            raise ValueError("Cyclic dependency")
        if i not in visited:
            visiting.add(i)
            for d in by_id[i]["depends_on"]:
                visit(d)
            visiting.remove(i)
            visited.add(i)
    for i in by_id:
        visit(i)
    tracking = root.get("task_tracking", {})
    if (tracking.get("manifest") != "v2/tasks/master_tasks.json" or
            tracking.get("canonical_root") != "state.json" or
            tracking.get("total_tasks") != 34 or
            tracking.get("status_authority") !=
            "v2/tasks/state.json for per-task statuses; root state.json for project-wide state"):
        raise ValueError("Canonical root state metadata mismatch")
    if master.get("canonical_state") != "state.json":
        raise ValueError("Manifest canonical root mismatch")
    if (ledger.get("canonical_state") != "state.json" or
            ledger.get("schema") != 1 or
            set(ledger.get("allowed_statuses", [])) != STATUSES or
            len(ledger.get("allowed_statuses", [])) != len(STATUSES)):
        raise ValueError("Task ledger canonical state metadata mismatch")
    rows = ledger["statuses"]
    if len(rows) != 34 or sorted(row["id"] for row in rows) != list(range(1, 35)):
        raise ValueError("Incomplete task status ledger")
    # A completed task cannot be accepted while any mandatory prerequisite
    # remains incomplete. Validate the entire ledger, not just the next task.
    status_by_id = {row["id"]: row["status"] for row in rows}
    for task in tasks:
        if status_by_id[task["id"]] == "completed":
            missing = [dep for dep in task["depends_on"]
                       if status_by_id[dep] != "completed"]
            if missing:
                raise ValueError(
                    "Completed task has unfinished dependencies: "
                    + str(task["id"]) + " -> " + ",".join(map(str, missing)))
    for row in rows:
        if row["status"] not in STATUSES:
            raise ValueError("Invalid task status")
        if row["status"] == "completed" and (not row["evidence_urls"] or not row["last_checked_at"]):
            raise ValueError("Completed task without verified evidence")
        if row["id"] == 32 and row["status"] == "completed" and not row.get("user_device_confirmation"):
            raise ValueError("Device test requires user confirmation")
    return by_id, {row["id"]: row for row in rows}


def select(master, ledger, root, defer_heavy=False):
    tasks, rows = validate(master, ledger, root)
    # Resume ongoing work first; blocked work is not silently marked successful.
    ready = [t for t in tasks.values() if t.get("scope") != OPTIONAL_SCOPE and rows[t["id"]]["status"] in ("pending", "in_progress")
             and all(rows[d]["status"] == "completed" for d in t["depends_on"])]
    # #34 is always last: every other task must have evidence-backed completion.
    if any(rows[i]["status"] != "completed" for i in range(1, 34)):
        ready = [t for t in ready if t["id"] != 34]
    if defer_heavy and any(t["id"] not in DEFERRED_LAST for t in ready):
        ready = [t for t in ready if t["id"] not in DEFERRED_LAST]
    ready.sort(key=lambda t: (PRIORITY[t["priority"]], 0 if rows[t["id"]]["status"] == "in_progress" else 1, t["id"]))
    return ready[0]["id"] if ready else None


def safe_transition(row, new_status, evidence_urls=(), checked_at=None, user_confirmed=False):
    if new_status not in STATUSES:
        raise ValueError("Unknown status")
    if user_confirmed and row.get("id") != 32:
        raise ValueError("User device confirmation only applies to task 32")
    if row.get("status") == "completed" and new_status != "completed":
        raise ValueError("Completed task cannot be silently reopened or downgraded")
    if new_status == "completed" and row.get("status") != "completed" and (not evidence_urls or not checked_at):
        raise ValueError("No completion without evidence and verification timestamp")
    if new_status == "completed" and row.get("status") == "completed":
        if evidence_urls and list(evidence_urls) != row.get("evidence_urls"):
            raise ValueError("Completed task evidence cannot be silently replaced")
        if checked_at and checked_at != row.get("last_checked_at"):
            raise ValueError("Completed task verification timestamp cannot be silently replaced")
    if row["id"] == 32 and new_status == "completed" and not user_confirmed:
        raise ValueError("Only user can confirm device test")
    return dict(row, status=new_status, evidence_urls=list(evidence_urls) if evidence_urls else row["evidence_urls"],
                last_checked_at=checked_at or row["last_checked_at"],
                **({"user_device_confirmation": True} if user_confirmed else {}))


def require_matching_sha(observed_sha, expected_sha):
    """Caller must use GitHub's conditional blob-SHA update after this check."""
    if not observed_sha or not expected_sha or observed_sha != expected_sha:
        raise ValueError("Concurrent state update; refetch and reconcile")
    return True


def require_fresh_github(fetch_result):
    if not isinstance(fetch_result, dict) or fetch_result.get("status") != "completed":
        raise ValueError("GitHub unavailable or run incomplete")
    if fetch_result.get("conclusion") != "success":
        raise ValueError("GitHub run not successful")
    return True


def verify_grouped_actions(runs, expected_sha, required_names):
    """Require fresh, same-commit, successful workflow runs; no partial green."""
    if (not isinstance(runs, list) or not isinstance(expected_sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", expected_sha) is None
            or not isinstance(required_names, (list, tuple)) or not required_names
            or any(not isinstance(name, str) or not name for name in required_names)
            or len(set(required_names)) != len(required_names)):
        raise ValueError("Missing or duplicate required GitHub Actions evidence")
    accepted = {}
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError("Invalid GitHub run")
        if run.get("head_sha") != expected_sha:
            continue
        # A same-SHA run from a fork or unrelated ref is not development acceptance.
        if run.get("head_branch") != BRANCH or run.get("event") not in ("push", "workflow_dispatch"):
            continue
        name = run.get("name")
        if name not in required_names:
            continue
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise ValueError("Required grouped Actions run incomplete or failed: " + str(name))
        if (type(run.get("id")) is not int or run["id"] <= 0 or
                run.get("html_url") != (
                    "https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/" + str(run["id"]))):
            raise ValueError("Missing trusted Actions run identity")
        jobs = run.get("jobs")
        if (run.get("jobs_checked") is not True or not isinstance(jobs, list)
                or not jobs or type(run.get("jobs_total_count")) is not int
                or run["jobs_total_count"] != len(jobs)):
            raise ValueError("Missing complete grouped Actions job evidence")
        if any(not isinstance(job, dict) or job.get("status") != "completed"
               or job.get("conclusion") != "success"
               or not isinstance(job.get("steps"), list) or not job["steps"]
               or any(not isinstance(step, dict)
                      or step.get("conclusion") != "success"
                      for step in job["steps"]) for job in jobs):
            raise ValueError("Skipped, failed or incomplete grouped Actions job evidence")
        if name in accepted:
            raise ValueError("Ambiguous duplicate Actions workflow evidence")
        accepted[name] = run["html_url"]
    if set(accepted) != set(required_names):
        raise ValueError("Missing required same-commit Actions checks")
    return accepted



def reconcile_root_actions(root, ledger, runs, expected_sha, required_names):
    """Read-only reconciliation: root observations never imply fresh acceptance."""
    if not isinstance(root, dict) or not isinstance(ledger, dict):
        raise ValueError("Missing canonical state")
    if root.get("repository") != REPO or root.get("branch") != BRANCH:
        raise ValueError("Wrong canonical root")
    if ledger.get("canonical_state") != "state.json":
        raise ValueError("Wrong task ledger")
    observed = root.get("last_verified_run_observation")
    if not isinstance(observed, dict):
        raise ValueError("Missing root GitHub observation")
    # Root observations are historical. Fresh acceptance comes only from
    # same-commit successful Actions runs; requiring root SHA equality would
    # create an impossible commit/update cycle for state.json.
    accepted = verify_grouped_actions(runs, expected_sha, required_names)
    # Return evidence only; never mutate the root or mark any task completed.
    return {"repository": REPO, "branch": BRANCH,
            "expected_sha": expected_sha, "accepted_runs": accepted,
            "root_observation_present": True, "task_statuses_unchanged": True}


def independent_ready(master, ledger, root, excluded=(), defer_heavy=False):
    """List independent eligible tasks without treating a running AV gate as success."""
    tasks, rows = validate(master, ledger, root)
    excluded = set(excluded)
    ready = [t for t in tasks.values()
             if t["id"] not in excluded and t.get("scope") != OPTIONAL_SCOPE
             and rows[t["id"]]["status"] in ("pending", "in_progress")
             and all(rows[d]["status"] == "completed" for d in t["depends_on"])]
    # #34 is always last: every other task must have evidence-backed completion.
    if any(rows[i]["status"] != "completed" for i in range(1, 34)):
        ready = [t for t in ready if t["id"] != 34]
    if defer_heavy and any(t["id"] not in DEFERRED_LAST for t in ready):
        ready = [t for t in ready if t["id"] not in DEFERRED_LAST]
    return [t["id"] for t in sorted(ready, key=lambda t: (PRIORITY[t["priority"]], t["id"]))]



def issue34_ready(master, ledger, root, user_approved=False):
    """Fail-closed, read-only gate for post-33 discovery issue #10.

    A caller must separately establish explicit user approval; this function
    never starts an issue, edits GitHub, or impersonates IBO device evidence.
    """
    tasks, rows = validate(master, ledger, root)
    if set(tasks) != set(range(1, 35)):
        raise ValueError("Canonical 34 tasks required")
    if user_approved is not True:
        return False
    if any(row["status"] != "completed" for i, row in rows.items() if i not in DEFERRED_LAST and i != 34):
        return False
    if any(not row.get("evidence_urls") or not row.get("last_checked_at")
           for i, row in rows.items() if i not in DEFERRED_LAST):
        return False
    return rows[32].get("user_device_confirmation") is True


def assert_safe_write(path, branch):
    """Reject noncanonical, absolute and protected paths before GitHub writes."""
    if branch != BRANCH or not isinstance(path, str) or not path:
        raise ValueError("Protected path or branch")
    if (chr(92) in path or chr(0) in path or
            any(part in ("", ".", "..") for part in path.split("/"))):
        raise ValueError("Protected path or branch")
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or candidate.name in PROTECTED:
        raise ValueError("Protected path or branch")
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("state.json"))
    p.add_argument("--manifest", type=Path, default=Path("v2/tasks/master_tasks.json"))
    p.add_argument("--ledger", type=Path, default=Path("v2/tasks/state.json"))
    p.add_argument("--include-heavy", action="store_true", help="Compatibility flag; all 34 tasks are mandatory")
    args = p.parse_args()
    master, ledger, root = [json.loads(p.read_text(encoding="utf-8")) for p in (args.manifest, args.ledger, args.root)]
    print(json.dumps({"next_task_id": select(master, ledger, root, defer_heavy=not args.include_heavy), "policy": "READ_ONLY_NO_GITHUB_WRITES"}))


if __name__ == "__main__":
    main()
