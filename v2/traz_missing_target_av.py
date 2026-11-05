#!/usr/bin/env python3
"""Bounded real FFmpeg AV recheck of exact new TR/AZ M3U source hash leads.

Only exact tvg-id + URL SHA-256 candidates from the immutable source/EPG gap
artifact are eligible. Public output is anonymous; raw URLs are RSA sealed.
Source outage does NOT delete or permanently disqualify historic identities.
Never modifies the primary IBO playlist or any protected category.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shutil
from final_batch_acceptance import (
    ROOT,LIVE,LIVE_BLOB,HISTORY,HISTORY_SHA,gitblob,sha,fetch_one,probe,KEY)
from discover import SOURCES,load_original_run60_sources
from stage3_sealed_export import seal_rows

TARGET=ROOT/"v2/reports/ci/traz-missing-stream-epg-crosswalk.json"
OUT=ROOT/"v2/reports/ci/traz-missing-target-real-av.json"
SEALED=ROOT/"v2/reports/ci/traz-missing-target-av.sealed"
HEX=re.compile(r"[0-9a-f]{64}\Z")

def select_targets(data):
    if (not isinstance(data,dict) or data.get("schema")!=1 or
        data.get("kind")!="V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE" or
        data.get("policy")!="READ_ONLY_PUBLIC_HASH_ONLY_NO_AUTO_IBO_PROMOTION" or
        data.get("protected_playlist_modified") is not False or
        data.get("new_video_audio_verified")!=0 or
        data.get("ibo_device_verified") is not False):
        raise ValueError("Unsafe targeted source report")
    rows=data.get("candidate_identities")
    if not isinstance(rows,list) or len(rows)>600:
        raise ValueError("Invalid target identity count")
    chosen,by_id={},set()
    for row in rows:
        if not isinstance(row,dict) or row.get("playback_verified") is not False:
            raise ValueError("False source playback claim")
        cid=row.get("channel_id")
        if not isinstance(cid,str) or not cid or cid.casefold() in by_id:
            raise ValueError("Duplicate or empty exact identity")
        by_id.add(cid.casefold())
        streams=row.get("candidate_m3u_url_hashes")
        if not isinstance(streams,list) or len(streams)>100:
            raise ValueError("Unbounded target stream list")
        if row.get("candidate_count")!=len(streams):
            raise ValueError("Target candidate count mismatch")
        for item in streams:
            if not isinstance(item,dict) or item.get("av_verified") is not False:
                raise ValueError("False target AV evidence")
            h=item.get("url_sha256")
            if not isinstance(h,str) or not HEX.fullmatch(h):
                raise ValueError("Invalid target URL hash")
            if h in chosen and chosen[h]["channel_id"].casefold()!=cid.casefold():
                raise ValueError("One URL hash targets multiple channel identities")
            source_ids=item.get("source_ids")
            if not isinstance(source_ids,list) or any(
                    not isinstance(s,str) or len(s)>96 for s in source_ids):
                raise ValueError("Untrusted target source evidence")
            chosen[h]={"channel_id":cid,"source_ids":set(source_ids)}
    if len(chosen)!=data.get("exact_missing_stream_candidate_hashes"):
        raise ValueError("Target hash/identity count differs from saved gap report")
    return chosen

def configured_sources():
    config=json.loads(SOURCES.read_text(encoding="utf-8"))
    if config.get("policy")!="discovery-only; never modify live playlist":
        raise ValueError("Invalid source policy")
    current=[row for row in config.get("sources",[]) if row.get("enabled",True) is not False]
    original=load_original_run60_sources(ROOT/"v2/history/run60-dynamic-source-ledger.json")
    sources={}
    for item in current+original:
        sid=item.get("id")
        if not isinstance(sid,str) or sid in sources:
            raise ValueError("Invalid repeated source ID")
        sources[sid]=item
    return sources

def source_selection(targets,known):
    wanted={s for row in targets.values() for s in row["source_ids"]}
    return [known[k] for k in sorted(wanted&set(known))],sorted(wanted-set(known))

def match_fetched(targets,outputs):
    found={}
    statuses={}
    for sid,rows,state in outputs:
        if sid in statuses:raise ValueError("Duplicate fetched source")
        statuses[sid]=state
        if state!="FETCHED":continue
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get("tvg_id"),str):
                continue
            url=row.get("url")
            if not isinstance(url,str):continue
            h=sha(url)
            expected=targets.get(h)
            if expected is None or row["tvg_id"].strip().casefold()!=expected["channel_id"].casefold():
                continue
            if sid not in expected["source_ids"]:
                continue
            entry=found.setdefault(h,{"url":url,
                "channel_id":expected["channel_id"],"source_ids":set()})
            if entry["url"]!=url:
                raise ValueError("SHA256 collision in authenticated stream")
            entry["source_ids"].add(sid)
    return found,statuses

def public_report(targets,matched,statuses,unknown,checks):
    for h,proof in checks.items():
        if h not in matched or proof.get("url_sha256")!=h:
            raise ValueError("AV proof belongs to wrong stream hash")
        if proof.get("decoded") and (proof.get("status")!="VIDEO_AUDIO_DECODED" or
            proof.get("video") is not True or proof.get("audio") is not True):
            raise ValueError("False FFmpeg dual-track decode")
    rows=[]
    for h,identity in sorted(targets.items()):
        proof=checks.get(h,{"status":"NOT_FOUND_IN_CURRENT_SOURCE",
             "decoded":False,"video":False,"audio":False})
        rows.append({"url_sha256":h,"exact_channel_id":identity["channel_id"],
             "source_ids":sorted(matched[h]["source_ids"]) if h in matched else [],
             "status":proof["status"],"video":proof["video"],"audio":proof["audio"],
             "decoded":proof["decoded"],"ibo_device_verified":False})
    ids={r["exact_channel_id"] for r in rows if r["decoded"]}
    return {"schema":1,"kind":"V2_TR_AZ_MISSING_M3U_REAL_AV_READONLY",
      "policy":"PUBLIC_SHA_ONLY_RSA_AES_SEALED_STREAM_URLS",
      "candidate_hashes":len(targets),
      "matched_current_source_hashes":len(matched),
      "unmatched_or_unavailable_hashes":len(targets)-len(matched),
      "source_attempted":len(statuses),
      "source_errors":{k:v for k,v in statuses.items() if v!="FETCHED"},
      "target_source_ids_unresolved":unknown,
      "ffmpeg_probed":len(checks),
      "real_video_audio_decoded_hashes":sum(x["decoded"] for x in rows),
      "real_video_audio_channel_ids":len(ids),
      "channel_ids_with_new_av":sorted(ids),
      "av_status_counts":dict(sorted(Counter(x["status"] for x in rows).items())),
      "spoken_language_verified":False,"sweden_access_verified":False,
      "ibo_device_verified":False,"protected_playlist_modified":False,
      "old_historical_orphan_50_auto_recovered":False,
      "non_av_candidates_not_promoted":True,"results":rows}

def scan(workers=24):
    if sha(HISTORY.read_bytes())!=HISTORY_SHA or gitblob(LIVE.read_bytes())!=LIVE_BLOB:
        raise ValueError("Protected historical and IBO bytes changed")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("Actual ffmpeg and ffprobe required")
    if TARGET.is_symlink() or not TARGET.is_file() or TARGET.stat().st_size>10_000_000:
        raise ValueError("Missing pinned anonymous target gap artifact")
    targets=select_targets(json.loads(TARGET.read_text(encoding="utf-8")))
    known=configured_sources()
    selected,unknown=source_selection(targets,known)
    with ThreadPoolExecutor(max_workers=12) as pool:
        outputs=list(pool.map(fetch_one,selected))
    matched,statuses=match_fetched(targets,outputs)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        proofs=list(pool.map(probe,[(h,v["url"]) for h,v in sorted(matched.items())]))
    checks={p["url_sha256"]:p for p in proofs}
    if len(checks)!=len(proofs):
        raise ValueError("Duplicate FFmpeg URL result")
    report=public_report(targets,matched,statuses,unknown,checks)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    sealed=[{"url":v["url"],"url_sha256":h,"channel_id":v["channel_id"],
        "source_ids":sorted(v["source_ids"]),
        "ffmpeg_status":checks[h]["status"],"av_decoded":checks[h]["decoded"]}
        for h,v in sorted(matched.items())]
    seal_rows(sealed,KEY,SEALED)
    report["rsa_sealed_matches"]={"name":SEALED.name,
        "records_encrypted":len(sealed),"sha256":sha(SEALED.read_bytes())}
    OUT.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print("TR_AZ_NEW_MISSING_SOURCE_REAL_AV",json.dumps({
        "target_hashes":report["candidate_hashes"],
        "available_exact_sources":report["matched_current_source_hashes"],
        "probed":report["ffmpeg_probed"],
        "decoded_audio_video":report["real_video_audio_decoded_hashes"],
        "decoded_channel_ids":report["real_video_audio_channel_ids"],
        "unavailable":report["unmatched_or_unavailable_hashes"],
        "source_outages":len(report["source_errors"]),
        "unknown_source_ids":len(unknown)},sort_keys=True))
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--workers",type=int,default=24)
    a=p.parse_args()
    if not 1<=a.workers<=32:p.error("Invalid probe worker count")
    scan(workers=a.workers)

if __name__=="__main__":
    main()
