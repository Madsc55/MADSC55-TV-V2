#!/usr/bin/env python3
"""Read-only Stage 6 source coverage preflight. This is NOT live AV acceptance."""
import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "v2/config/sources.json"
STATE = ROOT / "v2/tasks/state.json"
REQUIRED_SCOPES = {"TR", "AZ", "world"}
REQUIRED_PLATFORMS = {"github", "gist", "gitlab", "codeberg"}

def source_platform(url):
    host = (urlparse(url or "").hostname or "").lower()
    if host == "gist.githubusercontent.com" or host == "gist.github.com":
        return "gist"
    if host in ("github.com", "raw.githubusercontent.com") or host.endswith(".github.io"):
        return "github"
    if host == "gitlab.com" or host.endswith(".gitlab.io") or host.endswith(".gitlab.com"):
        return "gitlab"
    if host == "codeberg.org" or host.endswith(".codeberg.page"):
        return "codeberg"
    return "other"


def evaluate(sources, statuses):
    active = [s for s in sources if s.get("enabled", True)]
    ids = [s.get("id") for s in sources]
    urls = [s.get("url") for s in active]
    bad_urls = [s.get("id") for s in active if
                urlparse(s.get("url", "")).scheme != "https" or
                not urlparse(s.get("url", "")).netloc]
    duplicate_ids = sorted(k for k, n in Counter(ids).items() if n > 1)
    duplicate_urls = sorted(k for k, n in Counter(urls).items() if n > 1)
    scopes = sorted(set(s.get("scope") for s in active if s.get("scope")))
    platform_counts = dict(sorted(Counter(source_platform(s.get("url")) for s in active).items()))
    outstanding = sorted(x["id"] for x in statuses
                         if x["id"] <= 33 and x.get("status") != "completed")
    stage6 = next((x for x in statuses if x["id"] == 34), {})
    return {
        "kind": "STAGE6_OFFLINE_READINESS_NOT_NETWORK_OR_AV_EVIDENCE",
        "configured_sources": len(sources),
        "enabled_sources": len(active),
        "scopes": scopes,
        "platform_counts": platform_counts,
        "missing_required_platforms": sorted(REQUIRED_PLATFORMS - set(platform_counts)),
        "missing_required_scopes": sorted(REQUIRED_SCOPES - set(scopes)),
        "invalid_https_source_ids": bad_urls,
        "duplicate_source_ids": duplicate_ids,
        "duplicate_active_urls": duplicate_urls,
        "unfinished_predecessor_ids": outstanding,
        "task34_status": stage6.get("status", "missing"),
        "live_network_scan_performed": False,
        "ffmpeg_video_audio_verified": False,
        "protected_ibo_modified": False,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-config", action="store_true",
                        help="validate source configuration and report live scan blockers")
    parser.add_argument("--strict", action="store_true",
                        help="require valid configuration and all live scan prerequisites")
    args = parser.parse_args()
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    statuses = json.loads(STATE.read_text(encoding="utf-8"))["statuses"]
    report = evaluate(sources, statuses)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if (args.strict or args.validate_config) and any(report[k] for k in (
        "missing_required_scopes", "invalid_https_source_ids",
        "duplicate_source_ids", "duplicate_active_urls")):
        raise SystemExit("Source configuration failed validation")
    if args.strict and report["unfinished_predecessor_ids"]:
        raise SystemExit("Stage 6 blocked: unfinished tasks 1-33; see report")
    if args.strict and report["missing_required_platforms"]:
        raise SystemExit("Stage 6 blocked: missing required source platforms; see report")

if __name__ == "__main__":
    main()
