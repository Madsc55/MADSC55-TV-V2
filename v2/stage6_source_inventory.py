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
    outstanding = sorted(x["id"] for x in statuses
                         if x["id"] <= 33 and x.get("status") != "completed")
    stage6 = next((x for x in statuses if x["id"] == 34), {})
    return {
        "kind": "STAGE6_OFFLINE_READINESS_NOT_NETWORK_OR_AV_EVIDENCE",
        "configured_sources": len(sources),
        "enabled_sources": len(active),
        "scopes": scopes,
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
    parser.add_argument("--strict", action="store_true",
                        help="fail when source configuration is invalid")
    args = parser.parse_args()
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    statuses = json.loads(STATE.read_text(encoding="utf-8"))["statuses"]
    report = evaluate(sources, statuses)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and any(report[k] for k in (
        "missing_required_scopes", "invalid_https_source_ids",
        "duplicate_source_ids", "duplicate_active_urls")):
        raise SystemExit("Source configuration failed validation")
    if args.strict and report["unfinished_predecessor_ids"]:
        raise SystemExit("Stage 6 blocked: unfinished tasks 1-33; see report")

if __name__ == "__main__":
    main()
