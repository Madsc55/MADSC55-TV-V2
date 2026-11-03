#!/usr/bin/env python3
"""Repository-wide V2 GitHub Actions trigger / write-permission safety gate.

This is a fail-closed, source-only audit: inspect every workflow in the current
checkout, forbid automated publishing and premature full IPTV/decoder scans,
and preserve read-only CI where explicitly approved. This cannot change GitHub
server-side Actions settings or default-branch workflow revisions.
"""
import argparse
import json
from pathlib import Path
import re
import sys

import yaml

DEV = "madsc/v2-discovery-bulk-20261031"
IBO = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"

LOCKED_PUBLISHERS = frozenset({
    "alphabetize-yeni-turk",
    "backups-logo-audit",
    "full-turkish-backups-audit",
    "import-backup-candidates",
    "move-turkish-backups",
    "repair-playlist-grouping",
    "sort-backups-enrich-logos",
    "turkish-backup-identity-audit",
    "turkish-backups-fifth-audit",
    "turkish-backups-fourth-audit",
    "turkish-backups-second-pass",
    "turkish-backups-third-pass",
    "turkish-category-audit",
    "v2-bruksel-logo-png",
    "v2-promote-yedekler",
})
MANUAL_ARTIFACT_ONLY = frozenset({"v2-epg", "v2-logo-backup"})
MANUAL_NETWORK_OR_MEDIA = frozenset({
    "ibo-real-scan",
    "v2-batched-playback",
    "v2-full-decoder",
    "v2-github-source-discovery",
    "v2-official-sites",
    "v2-turkish-stream-catalog",
    "v2-turkish-stream-decode",
    "v2-turkish-stream-probe",
    "v2-youtube-discovery",
    "v2-historical-recovery",
    "v2-historical-targeted-playback",
    "v2-orphan-m3u-recovery",
    "v2-stage5-orphan-reseal",
    "v2-stage5-historical-reseal",
    "v2-independent-archive-restore",
    "v2-spoken-language-existing-snapshot",
    "v2-stage3-real-history",
    "v2-stage3-historical-inventory",
    "v2-source-live-validation",
    "v2-turkish-stream-review",
    "v2-world-discovery",
    "v2-turkish-tv-health",
    "v2-postscan-triage",
    "v2-manual-source-audit",
})
# These are existing read-only regression / source-feed coverage checks. The
# whitelist is explicit so a newly added workflow cannot opt into push scans.
SAFE_PUSH_CI = frozenset({
    "v2-actions-monitor",
    "v2-current-scanner-offline-gate",
    "v2-eight-stage-verification",
    "v2-master-engine",
    "v2-ibo-parity",
    "v2-one-shot-final-contract",
    "v2-ordered-preflight",
    "v2-playlist-safety",
    "v2-source-adapter-batch",
    "v2-stage5-archive-acceptance",
    "v2-stage5-final-production-archive",
    "v2-turkish-m3u-source-coverage",
    "v2-actions-trigger-protection",
})
ALLOWED_EVENTS = frozenset({"push", "pull_request", "workflow_dispatch"})
GIT_WRITER = re.compile(r"(?<![\w-])git[ \t]+(?:-C[ \t]+\S+[ \t]+)?(?:push|commit|add)[ \t\n]", re.I)


def _mapping(value, kind):
    if not isinstance(value, dict):
        raise ValueError(f"{kind} must be a YAML mapping")
    return value


def _events(doc):
    raw = doc.get("on")
    if isinstance(raw, str):
        return {raw: None}
    if isinstance(raw, list):
        return {item: None for item in raw}
    return _mapping(raw, "on")


def validate_workflow(path, source):
    name = path.stem
    errors = []
    try:
        doc = yaml.load(source, Loader=yaml.BaseLoader)
        doc = _mapping(doc, "root workflow")
        events = _events(doc)
        permissions = _mapping(doc.get("permissions"), "top-level permissions")
        jobs = _mapping(doc.get("jobs"), "jobs")
    except (yaml.YAMLError, ValueError) as exc:
        return [f"INVALID_WORKFLOW_STRUCTURE:{type(exc).__name__}"], {}
    if not events:
        errors.append("NO_EVENTS")
    for event in events:
        if event not in ALLOWED_EVENTS:
            errors.append("UNAPPROVED_EVENT:" + str(event))
    if "schedule" in source and re.search(r"(?m)^  schedule:", source):
        errors.append("SCHEDULE_IS_FORBIDDEN_BEFORE_FINAL_SCAN")
    if permissions.get("contents") != "read":
        errors.append("CONTENTS_MUST_BE_READ_ONLY")
    for perm, value in permissions.items():
        if value == "write" and not (perm == "id-token" and name == "v2-independent-archive-restore"):
            errors.append("UNEXPECTED_REPOSITORY_WRITE_PERMISSION:" + perm)
    if GIT_WRITER.search(source):
        errors.append("GIT_REPOSITORY_MUTATION_COMMAND")
    if re.search(r"(?m)^\s*persist-credentials:[ \t]*true[ \t]*$", source):
        errors.append("PERSISTED_WRITE_CREDENTIALS")
    for job, spec in jobs.items():
        if not isinstance(spec, dict):
            errors.append("INVALID_JOB:" + str(job))
            continue
        if "permissions" in spec:
            for perm, value in _mapping(spec["permissions"], "job permissions").items():
                if value == "write" and not (perm == "id-token" and name == "v2-independent-archive-restore"):
                    errors.append("UNEXPECTED_JOB_WRITE_PERMISSION:" + perm)
    has_push = "push" in events
    has_pr = "pull_request" in events
    if has_pr and name != "v2-ordered-preflight":
        errors.append("UNAPPROVED_PULL_REQUEST_TRIGGER")
    if has_push:
        if name not in SAFE_PUSH_CI:
            errors.append("UNAPPROVED_AUTOMATIC_PUSH")
        branches = _mapping(events["push"], "push event").get("branches") if isinstance(events["push"], dict) else None
        if name == "v2-playlist-safety":
            # Path-filtered immutable-playlist check must also catch main.
            paths = _mapping(events["push"], "push event").get("paths", [])
            if IBO not in paths:
                errors.append("PLAYLIST_SAFETY_MUST_WATCH_ORIGINAL")
        elif name == "v2-ordered-preflight":
            if not isinstance(branches, list) or set(branches) != {"main", DEV}:
                errors.append("PREFLIGHT_MUST_BE_SCOPED_TO_MAIN_AND_DEV")
        elif branches != [DEV]:
            errors.append("PUSH_MUST_BE_SCOPED_TO_DEV")
    if name in LOCKED_PUBLISHERS:
        if set(events) != {"workflow_dispatch"} or permissions.get("contents") != "read":
            errors.append("LEGACY_PLAYLIST_PUBLISHER_NOT_LOCKED")
        if "protected-readonly-check" not in jobs:
            errors.append("LEGACY_PUBLISHER_MISSING_READONLY_LOCK")
        if "4b1c3cea4b5107a425abab60f62d41f9f81e05a7" not in source:
            errors.append("LEGACY_PUBLISHER_MISSING_PLAYLIST_HASH")
    if name in MANUAL_NETWORK_OR_MEDIA | MANUAL_ARTIFACT_ONLY and set(events) != {"workflow_dispatch"}:
        errors.append("NETWORK_OR_MEDIA_NOT_MANUAL_ONLY")
    if name in MANUAL_NETWORK_OR_MEDIA and name not in LOCKED_PUBLISHERS:
        if permissions.get("contents") != "read":
            errors.append("NETWORK_JOB_NOT_READ_ONLY")
    return sorted(set(errors)), {
        "workflow": name, "events": sorted(events),
        "permissions": dict(permissions), "jobs": len(jobs),
    }


def audit_repository(workflow_root, minimum_workflows=54):
    files = sorted(Path(workflow_root).glob("*.yml")) + sorted(Path(workflow_root).glob("*.yaml"))
    report = {"schema": 1, "kind": "V2_WORKFLOW_TRIGGER_PROTECTION_READONLY",
              "workflows_checked": len(files), "minimum_expected": minimum_workflows,
              "protected_main_blob_expected": "4b1c3cea4b5107a425abab60f62d41f9f81e05a7",
              "default_branch_runtime_schedules_disabled": "NOT_VERIFIABLE_FROM_DEV_BRANCH",
              "branch_protection_admin_rules": "NOT_VERIFIABLE_WITH_CURRENT_GITHUB_INTEGRATION",
              "issues": [], "events": {}, "locked_publishers": 0}
    if len(files) < minimum_workflows:
        report["issues"].append("WORKFLOW_INVENTORY_INCOMPLETE")
    names = set()
    for path in files:
        if path.stem in names:
            report["issues"].append("DUPLICATE_WORKFLOW_FILENAME:" + path.stem)
        names.add(path.stem)
        errors, info = validate_workflow(path, path.read_text(encoding="utf-8"))
        report["events"][path.name] = info.get("events", [])
        if path.stem in LOCKED_PUBLISHERS and not errors:
            report["locked_publishers"] += 1
        for error in errors:
            report["issues"].append(path.name + ":" + error)
    if LOCKED_PUBLISHERS - names:
        report["issues"].append("MISSING_LEGACY_LOCKED_WORKFLOWS")
    if MANUAL_NETWORK_OR_MEDIA - names:
        report["issues"].append("MISSING_MANUAL_NETWORK_WORKFLOWS")
    report["issues"].sort()
    report["status"] = "DEVELOPMENT_BRANCH_TRIGGER_GATE_PASS" if not report["issues"] else "DEVELOPMENT_BRANCH_TRIGGER_GATE_FAIL"
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workflows", type=Path, default=Path(".github/workflows"))
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = audit_repository(args.workflows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("V2 Actions workflow trigger protection:", result["status"],
          "files:", result["workflows_checked"], "locked publishers:", result["locked_publishers"],
          "issues:", len(result["issues"]))
    for issue in result["issues"]:
        print("ERROR:", issue)
    if result["issues"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
