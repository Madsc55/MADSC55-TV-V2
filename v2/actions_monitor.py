#!/usr/bin/env python3
"""Read V2 Eight-Stage verification Actions runs, jobs and failed steps."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "Madsc55/MADSC55-TV-V2")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
WORKFLOWS = ("v2-eight-stage-verification.yml", "v2-master-engine.yml",
             "v2-source-integration-batch.yml", "v2-ordered-preflight.yml")
BRANCH = "madsc/v2-discovery-bulk-20261031"

def api(path):
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing; actions:read required")
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "MADSC55-V2-Actions-Monitor",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GitHub Actions API HTTP %d; check actions:read and repository access" % exc.code) from exc

def collect():
    base = "/repos/" + REPO + "/actions"
    q = urllib.parse.urlencode({"branch": BRANCH, "per_page": 10})
    # Query each required workflow independently: repo-wide pages may be dominated by monitor runs.
    runs = []
    for workflow in WORKFLOWS:
        batch = api(base + "/workflows/" + workflow + "/runs?" + q)["workflow_runs"]
        if not isinstance(batch, list):
            raise RuntimeError("Invalid GitHub workflow runs response: " + workflow)
        for run in batch:
            run = dict(run)
            run["_workflow_file"] = workflow
            runs.append(run)
    if not runs:
        raise RuntimeError("GitHub API returned no V2 verification runs for the configured branch")
    if any(not run.get("id") or not run.get("head_sha") or not run.get("html_url") for run in runs):
        raise RuntimeError("GitHub API returned incomplete workflow run identity")
    records = []
    for run in runs:
        record = {key: run.get(key) for key in (
            "id", "run_number", "run_attempt", "event", "head_sha",
            "status", "conclusion", "html_url", "created_at", "updated_at"
        )}
        record["workflow_file"] = run["_workflow_file"]
        record["jobs"] = []
        if run.get("status") == "completed" and run.get("conclusion") != "success":
            jobs = api(base + "/runs/%s/jobs?per_page=100" % run["id"]).get("jobs", [])
            record["jobs"] = [{
                "id": job.get("id"), "name": job.get("name"),
                "status": job.get("status"), "conclusion": job.get("conclusion"),
                "failed_steps": [{
                    "number": step.get("number"), "name": step.get("name"),
                    "conclusion": step.get("conclusion")
                } for step in job.get("steps", []) if step.get("conclusion") in (
                    "failure", "cancelled", "timed_out"
                )]
            } for job in jobs if job.get("conclusion") != "success"]
        records.append(record)
    return {"repository": REPO, "workflows": list(WORKFLOWS), "branch": BRANCH,
            "monitor_run_id": os.environ.get("GITHUB_RUN_ID"),
            "monitor_sha": os.environ.get("GITHUB_SHA"), "runs": records}

def main():
    result = collect()
    path = Path(os.environ.get("ACTIONS_REPORT", "v2/reports/actions-last10.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for run in result["runs"]:
        print("run_id=%s sha=%s status=%s conclusion=%s url=%s" % (
            run["id"], run["head_sha"], run["status"], run["conclusion"], run["html_url"]))
    if len(result["runs"]) < 10:
        print("Only %d matching workflow runs returned by GitHub API" % len(result["runs"]))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("::error::" + str(exc), file=sys.stderr)
        raise SystemExit(1)
