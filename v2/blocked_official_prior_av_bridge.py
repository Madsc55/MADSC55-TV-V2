#!/usr/bin/env python3
"""Verify exact candidate SHA overlap with a preserved *prior* real AV scan.

This bridge compares SHA-only provenance and previous decoder results. It never
downloads streams, changes playlists, claims a current AV pass, or invents
links to media files. A result from a past AV scan is historical evidence only.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from blocked_official_source_handoff import TARGETS

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "history/blocked-official-prior-real-av-sha.json"
VALID = {"VIDEO_AUDIO_DECODED", "PROBE_FAILED_NETWORK_TIMEOUT",
         "UNSAFE_OR_UNRESOLVED_HOST"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def reconcile(current, old):
    if (current.get("kind") != "BLOCKED_OFFICIAL_PAGES_EXACT_SOURCE_ONLY"
            or current.get("video_audio_verified") is not False
            or current.get("no_plaintext_stream_urls") is not True
            or current.get("protected_ibo_playlist_modified") is not False):
        raise ValueError("Malformed current source-only evidence")
    if (old.get("schema") != 1 or
            old.get("kind") != "V2_BLOCKED_OFFICIAL_PRIOR_REAL_AV_SHA_ONLY" or
            old.get("source_report_sha256") !=
               "d7245c4d74f536511b39395081e5c973d08a6243b62b286195a44c565faaafa6" or
            old.get("source_artifact_id") != 13366661937 or
            old.get("source_scope_probed") != 9197 or
            old.get("plaintext_urls_in_ledger") is not False or
            old.get("now_verified_video_audio") is not False):
        raise ValueError("Missing prior real AV artifact provenance")
    rows = old.get("records")
    if not isinstance(rows,list) or len(rows) != 8:
        raise ValueError("The exact prior AV evidence must include 8 URL hashes")
    seen={}
    for row in rows:
        sha,page,status=row.get("url_sha256"),row.get("page_id"),row.get("prior_probe_status")
        if not isinstance(sha,str) or not HEX.fullmatch(sha) or sha in seen:
            raise ValueError("Duplicate or invalid previous URL identity")
        if page not in TARGETS or status not in VALID:
            raise ValueError("Unreviewed previous channel identity or probe status")
        seen[sha]=row
    previous_decoded=sum(x["prior_probe_status"]=="VIDEO_AUDIO_DECODED" for x in rows)
    if previous_decoded != old.get("verified_previous_video_audio_count"):
        raise ValueError("Previous decoder evidence count mismatch")
    hashes=current.get("candidate_url_sha256")
    if (not isinstance(hashes,list) or len(hashes)!=len(set(hashes)) or
            any(not isinstance(x,str) or not HEX.fullmatch(x) for x in hashes) or
            current.get("candidate_url_count") != len(hashes)):
        raise ValueError("Inconsistent current candidate hash inventory")
    statuses=Counter()
    pages_with_past_av=set()
    previous_count=0
    for sha in hashes:
        item=seen.get(sha)
        if item is None:
            statuses["NOT_PRESENT_IN_PRIOR_AV_ARTIFACT"]+=1
            continue
        statuses[item["prior_probe_status"]]+=1
        if item["prior_probe_status"]=="VIDEO_AUDIO_DECODED":
            previous_count+=1
            pages_with_past_av.add(item["page_id"])
    return {
        "schema":1, "kind":"V2_BLOCKED_OFFICIAL_PRIOR_AV_SHA_RECONCILIATION",
        "current_exact_candidates":len(hashes),
        "previous_real_av_probe_scope":old["source_scope_probed"],
        "previous_decoder_verified_candidates":previous_count,
        "previous_decoder_verified_channel_pages":sorted(pages_with_past_av),
        "previous_status_counts":dict(sorted(statuses.items())),
        "current_video_audio_verified":False,
        "current_ibo_device_verified":False,
        "remaining_http_403_redirect_errors_resolved":False,
        "historical_url_sha256_provenance_only":True,
        "protected_playlist_modified":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--current-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args=p.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.resolve()==args.current_report.resolve():
        p.error("Refusing to overwrite evidence")
    current=json.loads(args.current_report.read_text(encoding="utf-8"))
    prior=json.loads(LEDGER.read_text(encoding="utf-8"))
    result=reconcile(current,prior)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("BLOCKED_OFFICIAL_PRIOR_AV",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
