#!/usr/bin/env python3
"""Immutable 4,955 historical URL SHA identities vs prior real worldwide AV.

Only evidence from already-completed 33,657-candidate global scan is
reconciled. Not a new live scan, not spoken-language or IBO device proof.
No plaintext stream URL, token or personal metadata is emitted.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

BASELINE_SHA = "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27"
WORLD_RUN_ID = 41715476184
SHA = re.compile(r"[0-9a-f]{64}\Z")


def read_historical(path):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=BASELINE_SHA:
        raise ValueError("Historical 4955 identity baseline changed")
    ids=[]
    for raw in data.splitlines():
        if raw.strip():
            row=json.loads(raw)
            h=row.get("url_sha256")
            if not isinstance(h,str) or not SHA.fullmatch(h):
                raise ValueError("Invalid original historical URL SHA")
            ids.append(h)
    if len(ids)!=4955 or len(set(ids))!=4955:
        raise ValueError("Original historical identity count differs")
    return set(ids)


def bridge(historical, world, current):
    if not isinstance(historical,set) or not historical or not all(
            isinstance(h,str) and SHA.fullmatch(h) for h in historical):
        raise ValueError("Invalid preserved historical baseline")
    if (world.get("schema") != 1 or
            world.get("kind")!="V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE" or
            world.get("protected_main_playlist_modified") is not False or
            world.get("plaintext_url_in_public_report") is not False or
            world.get("ibo_player_verified") is not False or
            world.get("probe_budget_expired") is not False):
        raise ValueError("World scan provenance or safety cannot be confirmed")
    rows=world.get("candidates")
    if (not isinstance(rows,list) or
            len(rows)!=world.get("unique_url_candidates") or
            world.get("probed")!=len(rows) or world.get("unprobed")!=0 or
            world.get("sealed_url_count")!=len(rows)):
        raise ValueError("World media evidence truncated or incomplete")
    by_hash={}
    successes=0
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("Malformed worldwide candidate")
        h=row.get("url_sha256")
        if not isinstance(h,str) or not SHA.fullmatch(h) or h in by_hash:
            raise ValueError("Duplicate or invalid world stream identity")
        decoded,video,audio=(row.get(x) is True for x in ("decoded","video","audio"))
        if any(type(row.get(x)) is not bool for x in ("decoded","video","audio")):
            raise ValueError("Incomplete real decoder evidence")
        if decoded and (not video or not audio or row.get("status")!="VIDEO_AUDIO_DECODED"):
            raise ValueError("False previous real video+audio claim")
        if row.get("status")=="VIDEO_AUDIO_DECODED" and not decoded:
            raise ValueError("World AV status contradicts decoder result")
        if decoded:
            successes+=1
        by_hash[h]=(decoded,video,audio,str(row.get("status","UNKNOWN")))
    if successes!=world.get("audio_video_decoded"):
        raise ValueError("World AV decoder total differs from published run")
    audit=current.get("source_content_audit",{})
    absent=audit.get("historical_identifiers_absent_sha256_sample")
    present=audit.get("historical_identifiers_present_in_current_sources")
    if (not isinstance(absent,list) or
            audit.get("historical_baseline_count")!=len(historical) or
            not isinstance(present,int) or present+len(absent)!=len(historical) or
            audit.get("historical_identifiers_absent_from_current_sources")!=len(absent) or
            len(set(absent))!=len(absent) or not set(absent)<=historical):
        raise ValueError("Current 63-source historical readback inconsistent")
    historical_present=historical & set(by_hash)
    decoded={h for h in historical_present if by_hash[h][0]}
    both_not_decoded={h for h in historical_present
                      if not by_hash[h][0] and by_hash[h][1] and by_hash[h][2]}
    status_counts=Counter(by_hash[h][3] for h in historical_present)
    missing_from_sources=set(absent)
    prior_decoded_missing=decoded & missing_from_sources
    out={
        "schema":1, "kind":"V2_4955_HISTORICAL_PRIOR_WORLD_REAL_AV_SHA_BRIDGE",
        "previous_world_actions_run_id":WORLD_RUN_ID,
        "world_candidate_sha_count":len(rows),
        "world_real_ffmpeg_video_audio_decoded_count":successes,
        "original_historical_identity_count":len(historical),
        "historical_hashes_present_in_world":len(historical_present),
        "historical_hashes_absent_from_world":len(historical-historical_present),
        "historical_hashes_with_prior_world_ffmpeg_video_audio":len(decoded),
        "historical_hashes_with_both_streams_without_ffmpeg_decode":len(both_not_decoded),
        "historical_hashes_in_world_not_decoded":len(historical_present-decoded),
        "prior_world_historical_probe_status_counts":dict(sorted(status_counts.items())),
        "currently_in_source_feeds":present,
        "currently_absent_from_source_feeds":len(missing_from_sources),
        "currently_absent_with_prior_world_ffmpeg_decode":len(prior_decoded_missing),
        "currently_absent_in_world_but_not_decoded":len(
            (missing_from_sources & historical_present)-prior_decoded_missing),
        "currently_absent_not_in_world_scan":len(missing_from_sources-set(by_hash)),
        "previous_evidence_only_not_current_playback":True,
        "media_urls_plaintext_exported":False,
        "original_historical_inventory_modified":False,
        "main_ibo_playlist_modified":False,
        "spoken_language_verified":False,
        "ibo_device_verified":False}
    if "://" in json.dumps(out):
        raise ValueError("Raw stream URL in anonymous historical bridge")
    return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--prior-world-report",type=Path,required=True)
    parser.add_argument("--current-source-report",type=Path,required=True)
    parser.add_argument("--historical-baseline",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.resolve() in (
                args.prior_world_report.resolve(),args.current_source_report.resolve(),
                args.historical_baseline.resolve())):
        parser.error("Refuse evidence overwrite or alias")
    historic=read_historical(args.historical_baseline)
    world=json.loads(args.prior_world_report.read_text(encoding="utf-8"))
    current=json.loads(args.current_source_report.read_text(encoding="utf-8"))
    result=bridge(historic,world,current)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print("HISTORICAL_4955_PRIOR_WORLD_REAL_AV",json.dumps({
        k:result[k] for k in (
            "original_historical_identity_count","historical_hashes_present_in_world",
            "historical_hashes_with_prior_world_ffmpeg_video_audio",
            "historical_hashes_in_world_not_decoded",
            "historical_hashes_absent_from_world",
            "currently_absent_from_source_feeds",
            "currently_absent_with_prior_world_ffmpeg_decode",
            "currently_absent_not_in_world_scan")},sort_keys=True))

if __name__=="__main__":
    main()
