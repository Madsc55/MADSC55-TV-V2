#!/usr/bin/env python3
"""Read-only live default-branch Actions exposure audit for MADSC55 TV V2.

GitHub's scheduler and default-branch workflows do not inherit safety changes
from the development branch. This audit reads an immutable main Git snapshot,
the main branch metadata and live GitHub workflow enabled states; it never
pushes, disables a workflow, changes a repository setting or edits playlists.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

PLAYLIST = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
EXPECTED_REPO = "Madsc55/MADSC55-TV-V2"
GIT_MUTATE = re.compile(r"(?<![\w-])git[ \t]+(?:-C[ \t]+\S+[ \t]+)?(?:push|commit)[ \t\n]", re.I)
SCHEDULE_EVENTS = {"schedule"}
PRIVILEGED_EVENTS = {"workflow_run", "pull_request_target", "repository_dispatch"}
GIT_MUTATE = re.compile(r"(?<![\w-])git[ \t]+(?:-C[ \t]+\S+[ \t]+)?(?:push|commit|add)[ \t\n]", re.I)
ALLOWED_REMOTE = re.compile(r"[0-9a-f]{40}\Z")


def _events(doc):
    raw = doc.get("on", {})
    if isinstance(raw, dict):
        return set(raw)
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return set(raw)
    raise ValueError("Invalid GitHub Actions event collection")


def summarize_default_branch(workflows, *, revision, protection=None,
                             enabled_states=None, rulesets=None, source_error=None,
                             pr_policy_verified=False):
    """Make a fail-closed finding from real YAML contents and optional server data."""
    if not isinstance(workflows, dict) or not workflows:
        raise ValueError("No default-branch workflows to inspect")
    if not ALLOWED_REMOTE.fullmatch(revision):
        raise ValueError("Non-immutable default-branch snapshot")
    counts = {"writable_publisher": [], "scheduled": [],
              "push_triggered": [], "playlist_writer": [],
              "unparseable": [], "enabled_writable_publisher": [],
              "enabled_scheduled": [], "state_unknown": [],
              "contents_write_permission": [], "enabled_contents_write_permission": [],
              "git_mutation_command": [], "enabled_git_mutation_command": [],
              "privileged_event": [], "enabled_privileged_event": []}
    details = {}
    for path, text in sorted(workflows.items()):
        if not path.startswith(".github/workflows/") or not path.endswith((".yml", ".yaml")):
            raise ValueError("Unexpected workflow pathname")
        try:
            doc = yaml.load(text, Loader=yaml.BaseLoader)
            if not isinstance(doc, dict) or not isinstance(doc.get("jobs"), dict):
                raise ValueError("Invalid workflow jobs")
            events = _events(doc)
            permissions = doc.get("permissions") or {}
            if not isinstance(permissions, dict):
                raise ValueError("Invalid workflow permissions")
            job_permissions = [
                spec.get("permissions") or {}
                for spec in doc["jobs"].values() if isinstance(spec, dict)
            ]
            if any(not isinstance(item, dict) for item in job_permissions):
                raise ValueError("Invalid job permission")
            write_permission = (permissions.get("contents") == "write" or
                                any(item.get("contents") == "write" for item in job_permissions))
            push = bool(re.search(r"(?<![\w-])git[ \t]+push\b", text, re.I))
            mutation = bool(GIT_MUTATE.search(text))
            privileged = bool(events & PRIVILEGED_EVENTS)
            # Same workflow path returned by the live GitHub workflow list.
            state = enabled_states.get(path) if enabled_states is not None else None
            if state is None:
                counts["state_unknown"].append(path)
            writable = write_permission and push
            scheduled = "schedule" in events
            pushed = "push" in events
            playlist_writer = writable and PLAYLIST in text
            if write_permission:
                counts["contents_write_permission"].append(path)
            if mutation:
                counts["git_mutation_command"].append(path)
            if privileged:
                counts["privileged_event"].append(path)
            if state == "active" and write_permission:
                counts["enabled_contents_write_permission"].append(path)
            if state == "active" and mutation:
                counts["enabled_git_mutation_command"].append(path)
            if state == "active" and privileged:
                counts["enabled_privileged_event"].append(path)
            if writable:
                counts["writable_publisher"].append(path)
            if scheduled:
                counts["scheduled"].append(path)
            if pushed:
                counts["push_triggered"].append(path)
            if playlist_writer:
                counts["playlist_writer"].append(path)
            if state == "active" and writable:
                counts["enabled_writable_publisher"].append(path)
            if state == "active" and scheduled:
                counts["enabled_scheduled"].append(path)
            details[path] = {
                "events": sorted(events), "workflow_state": state or "UNKNOWN",
                "contents_write_and_git_push": writable,
                "scheduled": scheduled, "playlist_mutation_path": playlist_writer,
                "contents_write": write_permission,
                "git_mutation_command": mutation,
                "privileged_event": privileged,
            }
        except (yaml.YAMLError, ValueError, TypeError) as exc:
            counts["unparseable"].append(path)
            details[path] = {"error": type(exc).__name__, "workflow_state": "UNKNOWN"}
    protected = protection is True or (isinstance(rulesets, list) and
                  any(isinstance(rule, dict) and rule.get("enforcement") == "active"
                      for rule in rulesets))
    # A protected:true flag alone does not prove required PR review or that
    # administrator bypasses are prevented. Do not issue an unsafe READY.
    missing_live = (protection is None or enabled_states is None or
                    rulesets is None or bool(source_error) or
                    pr_policy_verified is not True)
    unsafe = bool(counts["writable_publisher"] or counts["scheduled"] or
                  counts["contents_write_permission"] or
                  counts["git_mutation_command"] or counts["privileged_event"] or
                  counts["unparseable"] or not protected)
    if unsafe:
        readiness = "MAIN_DEFAULT_BRANCH_NOT_SAFE"
    elif missing_live or counts["state_unknown"]:
        readiness = "MAIN_DEFAULT_BRANCH_NOT_FULLY_VERIFIED"
    else:
        readiness = "MAIN_DEFAULT_BRANCH_READY"
    return {
        "schema": 1, "kind": "MADSC55_V2_ACTUAL_DEFAULT_BRANCH_READ_ONLY_EXPOSURE",
        "repository": EXPECTED_REPO, "default_branch": "main",
        "main_revision": revision,
        "source_files": len(workflows),
        "branch_protected": protection,
        "required_pr_policy_verified": pr_policy_verified is True,
        "active_rulesets": sum(1 for rule in (rulesets or [])
                               if isinstance(rule, dict) and rule.get("enforcement") == "active")
                           if rulesets is not None else None,
        "runtime_state_observed": enabled_states is not None,
        "external_evidence_error": source_error,
        "readiness": readiness,
        "counts": {key: len(value) for key, value in counts.items()},
        "paths": {key: value for key, value in counts.items()},
        "workflows": details,
        "protected_playlist_modified": False,
        "main_branch_modified": False,
        "automations_disabled_by_audit": False,
    }


def _git(*args):
    out = subprocess.run(["git", *args], check=True, text=True,
                         capture_output=True, timeout=30)
    return out.stdout


def main_snapshot(revision="refs/remotes/origin/main"):
    sha = _git("rev-parse", "--verify", revision + "^{commit}").strip()
    if not ALLOWED_REMOTE.fullmatch(sha):
        raise ValueError("Invalid main commit SHA")
    paths = _git("ls-tree", "-r", "--name-only", sha,
                 "--", ".github/workflows").splitlines()
    sources = {}
    for path in paths:
        if not path.endswith((".yml", ".yaml")):
            continue
        if not re.fullmatch(r"\.github/workflows/[A-Za-z0-9_.-]+\.(yml|yaml)", path):
            raise ValueError("Unsafe main workflow pathname")
        sources[path] = _git("show", sha + ":" + path)
    if not 30 <= len(sources) <= 200:
        raise ValueError("Unexpected main Actions workflow inventory")
    return sha, sources


def _api(endpoint):
    if not re.fullmatch(r"/repos/Madsc55/MADSC55-TV-V2/[A-Za-z0-9/_.?=&%-]+", endpoint):
        raise ValueError("Unexpected GitHub API endpoint")
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "MADSC55-TV-V2-Main-Actions-ReadOnly",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("https://api.github.com" + endpoint,
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Oversize GitHub response")
        return json.loads(data)
    except urllib.error.HTTPError as exc:
        # Never log response bodies or Authorization values.
        raise RuntimeError("GitHub API read rejected: HTTP " + str(exc.code)) from exc


def live_main_state(snapshot_sha):
    base = "/repos/Madsc55/MADSC55-TV-V2"
    branch = _api(base + "/branches/main")
    if branch.get("commit", {}).get("sha") != snapshot_sha:
        raise RuntimeError("Main advanced during snapshot; no stale readiness approval")
    rulesets = _api(base + "/rulesets?includes_parents=true")
    if not isinstance(rulesets, list):
        raise ValueError("Unexpected repository rulesets response")
    states = {}
    page = 1
    while page <= 4:
        result = _api(base + "/actions/workflows?per_page=100&page=" + str(page))
        workflows = result.get("workflows")
        if not isinstance(workflows, list):
            raise ValueError("Unexpected workflow state payload")
        for workflow in workflows:
            path = workflow.get("path")
            state = workflow.get("state")
            if isinstance(path, str) and isinstance(state, str):
                states[path] = state
        if len(workflows) < 100:
            break
        page += 1
    else:
        raise ValueError("Workflow state list exceeds pagination guard")
    # Prevent a concurrent main update during the multi-page state query.
    confirmation = _api(base + "/branches/main")
    if confirmation.get("commit", {}).get("sha") != snapshot_sha:
        raise RuntimeError("Main advanced during live state query")
    pr_policy_verified = False
    if branch.get("protected") is True:
        try:
            policy = _api(base + "/branches/main/protection")
            reviews = policy.get("required_pull_request_reviews")
            admins = policy.get("enforce_admins")
            pr_policy_verified = bool(
                isinstance(reviews, dict)
                and int(reviews.get("required_approving_review_count") or 0) >= 1
                and isinstance(admins, dict) and admins.get("enabled") is True
                and (policy.get("allow_force_pushes") or {}).get("enabled") is not True
                and (policy.get("allow_deletions") or {}).get("enabled") is not True
            )
        except (RuntimeError, ValueError, TypeError, urllib.error.URLError,
                TimeoutError, OSError):
            # Default Actions token may lack permission for this detail.
            pr_policy_verified = False
    return bool(branch.get("protected")), rulesets, states, pr_policy_verified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="refs/remotes/origin/main")
    parser.add_argument("--output", type=Path,
                        default=Path("v2/reports/ci/main-default-branch-risk.json"))
    args = parser.parse_args()
    sha, workflows = main_snapshot(args.revision)
    protection = rulesets = states = None
    pr_policy_verified = False
    source_error = None
    try:
        protection, rulesets, states, pr_policy_verified = live_main_state(sha)
    except (ValueError, RuntimeError, urllib.error.URLError, TimeoutError, OSError) as exc:
        source_error = type(exc).__name__ + ": " + str(exc)[:100]
    report = summarize_default_branch(
        workflows, revision=sha, protection=protection, rulesets=rulesets,
        enabled_states=states, source_error=source_error,
        pr_policy_verified=pr_policy_verified)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n")
    print("MAIN default branch:", report["readiness"],
          "SHA:", sha, "workflows:", report["source_files"],
          "publisher_write_paths:", report["counts"]["writable_publisher"],
          "scheduled_definitions:", report["counts"]["scheduled"],
          "active_write_paths:", report["counts"]["enabled_writable_publisher"],
          "active_schedules:", report["counts"]["enabled_scheduled"],
          "branch_protected:", protection,
          "required_pr_policy_verified:", pr_policy_verified,
          "runtime_states_verified:", states is not None)
    # This is a read-only diagnostic, NOT an assertion of production readiness.
    # Structural errors still cause CI failure; risk remains explicit as NOT_SAFE.
    if report["counts"]["unparseable"]:
        sys.exit("Malformed main workflow YAML requires manual review")


if __name__ == "__main__":
    main()
