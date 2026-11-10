#!/usr/bin/env python3
"""Read V2 Eight-Stage verification Actions runs, jobs and failed steps."""
import json
import re
from datetime import datetime, timezone
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "Madsc55/MADSC55-TV-V2")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
WORKFLOWS = ("v2-eight-stage-verification.yml", "v2-master-engine.yml",
             "v2-source-integration-batch.yml", "v2-ordered-preflight.yml",
             "v2-actions-monitor.yml")
BRANCH = "madsc/v2-discovery-bulk-20261031"
WORKFLOW_NAMES = {
    "v2-eight-stage-verification.yml": "V2 Eight-Stage Runner Verification",
    "v2-master-engine.yml": "V2 Master Engine",
    "v2-source-integration-batch.yml": "V2 Source Integration Batch",
    "v2-ordered-preflight.yml": "V2 Sirali Hazirlik Testleri",
    "v2-actions-monitor.yml": "V2 Actions Status Monitor",
}

def api(path):
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing; actions:read required")
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "MADSC55-V2-Actions-Monitor",
    })
    # Retry only bounded transient API failures. Never retry authorization or
    # malformed responses; the monitor must fail closed rather than show green.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError("GitHub Actions API HTTP %d; check actions:read and repository access" % exc.code) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == 2:
                raise RuntimeError("GitHub Actions API transport failure after bounded retries") from exc
        time.sleep(min(2 ** attempt, 2))

def stalled_run(run, now=None, threshold_seconds=7200):
    """Flag a running workflow whose creation time exceeds a bounded window.

    This is advisory only: never cancel, retry, or declare failure based on age.
    Invalid or missing timestamps fail closed to unknown (None).
    """
    if run.get("status") not in ("in_progress", "queued", "waiting", "pending", "requested"):
        return False
    raw = run.get("run_started_at") or run.get("created_at")
    if not isinstance(raw, str):
        return None
    try:
        started = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if started.tzinfo is None:
            return None
        current = now if now is not None else datetime.now(timezone.utc)
        age = (current - started).total_seconds()
    except (ValueError, TypeError, OverflowError):
        return None
    if age < 0:
        return None
    return age >= threshold_seconds


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
    if any(type(run.get("id")) is not int or run["id"] <= 0
           or not isinstance(run.get("head_sha"), str)
           or re.fullmatch(r"[0-9a-f]{40}", run["head_sha"]) is None
           or run.get("html_url") !=
           "https://github.com/" + REPO + "/actions/runs/" + str(run["id"])
           for run in runs):
        raise RuntimeError("GitHub API returned incomplete or untrusted workflow run identity")
    records = []
    for run in runs:
        record = {key: run.get(key) for key in (
            "id", "run_number", "run_attempt", "event", "head_sha",
            "status", "conclusion", "html_url", "created_at", "run_started_at", "updated_at"
        )}
        record["workflow_file"] = run["_workflow_file"]
        record["name"] = WORKFLOW_NAMES[run["_workflow_file"]]
        # Source integration has a configured 300-minute job budget; its
        # ordinary 2-hour age is not a stuck-job signal.
        stall_threshold = (6 * 3600 if run["_workflow_file"] ==
                           "v2-source-integration-batch.yml" else
                           3 * 3600 if run["_workflow_file"] ==
                           "v2-master-engine.yml" else 2 * 3600)
        record["stall_threshold_seconds"] = stall_threshold
        record["possibly_stalled"] = stalled_run(run, threshold_seconds=stall_threshold)
        record["automatic_retry_permitted"] = False
        record["head_branch"] = run.get("head_branch")
        record["run_event"] = run.get("event")
        record["same_development_branch"] = run.get("head_branch") == BRANCH
        record["eligible_event"] = run.get("event") in ("push", "workflow_dispatch")
        monitor_sha = os.environ.get("GITHUB_SHA", "")
        record["same_monitor_sha"] = (len(monitor_sha) == 40
            and run.get("head_sha") == monitor_sha)
        # A historical green run cannot qualify as acceptance for this monitor commit.
        # This is still only a candidate: grouped job evidence is required separately.
        record["acceptance_candidate"] = (record["same_development_branch"]
            and record["eligible_event"] and record["same_monitor_sha"]
            and run.get("status") == "completed"
            and run.get("conclusion") == "success")
        record["jobs"] = []
        record["jobs_total_count"] = None
        record["jobs_checked"] = False
        record["failure_reasons"] = []
        if run.get("status") in ("in_progress","queued","waiting","pending","requested") and record["possibly_stalled"] is True:
            # Inspect the active job without cancelling or retrying long AV scans.
            active = api(base + "/runs/%s/jobs?per_page=100" % run["id"])
            jobs = active.get("jobs")
            total = active.get("total_count")
            if type(total) is int and total>len(jobs or []) and isinstance(jobs,list):
                all_jobs=list(jobs)
                for page in range(2,(total+99)//100+1):
                    part=api(base + "/runs/%s/jobs?per_page=100&page=%s" % (run["id"],page))
                    chunk=part.get("jobs")
                    if type(part.get("total_count")) is not int or part["total_count"]!=total or not isinstance(chunk,list) or not chunk:
                        all_jobs=[]
                        break
                    all_jobs.extend(chunk)
                jobs=all_jobs
            if (type(total) is not int or not isinstance(jobs,list) or
                    total != len(jobs) or
                    any(type(job.get("id")) is not int or job["id"]<=0 for job in jobs if isinstance(job,dict)) or
                    any(not isinstance(job,dict) for job in jobs) or
                    len({job["id"] for job in jobs})!=len(jobs)):
                record["active_job_evidence_complete"] = False
                record["failure_reasons"].append("incomplete_active_job_inventory")
            else:
                record["active_job_evidence_complete"] = True
                record["active_jobs"] = [{
                    "id": job.get("id"), "name": job.get("name"),
                    "status": job.get("status"), "conclusion": job.get("conclusion"),
                    "started_at": job.get("started_at")
                } for job in jobs if job.get("status") in ("in_progress","queued","waiting","pending","requested")]
        if run.get("status") == "completed":
            # GitHub paginates workflow jobs at 100 entries. Never classify a
            # truncated first page as complete or drop evidence from later pages.
            response = api(base + "/runs/%s/jobs?per_page=100" % run["id"])
            jobs = response.get("jobs")
            if (isinstance(jobs, list) and
                    type(response.get("total_count")) is int and
                    response["total_count"] > len(jobs)):
                total = response["total_count"]
                all_jobs = list(jobs)
                for page in range(2, (total + 99) // 100 + 1):
                    part = api(base + "/runs/%s/jobs?per_page=100&page=%s" %
                               (run["id"], page))
                    chunk = part.get("jobs")
                    if (type(part.get("total_count")) is not int or
                            part["total_count"] != total or
                            not isinstance(chunk, list) or not chunk):
                        raise RuntimeError("Incomplete Actions job details for run %s" % run["id"])
                    all_jobs.extend(chunk)
                response = dict(response, jobs=all_jobs)
                jobs = all_jobs
            # GitHub can finish a failed/cancelled run before creating any jobs.
            # Preserve that negative evidence without aborting unrelated runs.
            if (jobs == [] and type(response.get("total_count")) is int
                    and response["total_count"] == 0
                    and run.get("conclusion") in ("failure", "cancelled", "timed_out")):
                record["acceptance_candidate"] = False
                record["jobs_total_count"] = 0
                record["failure_reasons"] = [
                    "workflow_" + run["conclusion"], "no_jobs_created"]
                records.append(record)
                continue
            if (not isinstance(jobs, list) or
                    type(response.get("total_count")) is not int or
                    response["total_count"] != len(jobs) or not jobs):
                raise RuntimeError("Incomplete Actions job details for run %s" % run["id"])
            record["jobs_checked"] = True
            record["jobs_total_count"] = response["total_count"]
            record["jobs"] = [{
                "id": job.get("id"), "name": job.get("name"),
                "status": job.get("status"), "conclusion": job.get("conclusion"),
                "steps": [{"number": step.get("number"), "conclusion": step.get("conclusion")}
                          for step in (job.get("steps") or [])],
                "failed_steps": [{
                    "number": step.get("number"), "name": step.get("name"),
                    "conclusion": step.get("conclusion")
                } for step in (job.get("steps") or []) if step.get("conclusion") in (
                    "failure", "cancelled", "timed_out", "skipped", "neutral"
                )]
            } for job in jobs]
            # A workflow-level green with no job evidence or skipped jobs is not AV acceptance.
            record["acceptance_candidate"] = (record["acceptance_candidate"]
                and bool(jobs) and response.get("total_count") == len(jobs)
                and all(job.get("status") == "completed"
                        and job.get("conclusion") == "success"
                        and isinstance(job.get("steps"), list)
                        and bool(job["steps"])
                        and all(step.get("conclusion") == "success"
                                for step in job["steps"])
                        for job in jobs))
        if run.get("status") != "completed":
            record["failure_reasons"].append("workflow_not_completed")
        elif run.get("conclusion") != "success":
            record["failure_reasons"].append("workflow_" + str(run.get("conclusion")))
        if record["jobs_checked"]:
            for job in record["jobs"]:
                if job["status"] != "completed" or job["conclusion"] != "success":
                    record["failure_reasons"].append(
                        "job_%s_%s" % (job["id"], job["conclusion"]))
                for step in job["failed_steps"]:
                    record["failure_reasons"].append(
                        "job_%s_step_%s_%s" % (
                            job["id"], step["number"], step["conclusion"]))
            if not record["acceptance_candidate"] and not record["failure_reasons"]:
                record["failure_reasons"].append("not_current_commit_or_incomplete_step_evidence")
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
        if run["possibly_stalled"] is True:
            print("::warning::Potentially stalled Actions run %s workflow=%s; review manually, no automatic retry" % (run["id"], run["workflow_file"]))
        print("run_id=%s sha=%s status=%s conclusion=%s url=%s" % (
            run["id"], run["head_sha"], run["status"], run["conclusion"], run["html_url"]))
        # Surface failed steps in the Actions console, not just the JSON artifact.
        for reason in run.get("failure_reasons", []):
            print("::warning::V2 run %s (%s): %s" % (
                run["id"], run["workflow_file"], reason))
        for job in run.get("jobs", []):
            for step in job.get("failed_steps", []):
                print("::warning::V2 run %s job %s step %s (%s): %s" % (
                    run["id"], job["id"], step["number"],
                    step["name"], step["conclusion"]))
    if len(result["runs"]) < 10:
        print("Only %d matching workflow runs returned by GitHub API" % len(result["runs"]))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("::error::" + str(exc), file=sys.stderr)
        raise SystemExit(1)
