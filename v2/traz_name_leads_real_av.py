#!/usr/bin/env python3
"""Read-only real AV sampling of exact-name-only TR/AZ stream leads.

These 15 identity metadata hints were NOT exact TVG-ID matches. Validating a
short FFmpeg video+audio segment can prove a URL decoded at one moment but
cannot identify the broadcaster, spoken language, Swedish location, persistent
uptime or IBO device compatibility. No plaintext URL is exported.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/"v2/reports/ci/traz-missing-name-xmltv-review.json"
OUT=ROOT/"v2/reports/ci/traz-name-leads-real-av.json"
SEALED=ROOT/"v2/reports/ci/traz-name-leads-real-av.sealed"
HEX=re.compile(r"[0-9a-f]{64}\Z")

def targets(report):
    if (not isinstance(report,dict) or report.get("schema")!=1 or
        report.get("kind")!="V2_TR_AZ_STREAM_XMLTV_EXACT_NAME_REVIEW" or
        report.get("policy")!="READ_ONLY_METADATA_LEADS_NOT_VIDEO_AUDIO_OR_EPG_ACCURACY" or
        report.get("protected_playlist_modified") is not False or
        report.get("ibo_device_verified") is not False or
        report.get("new_av_proof")!=0):
        raise ValueError("Untrusted metadata-only name review")
    stream=report.get("stream_name_review")
    if not isinstance(stream,dict) or not isinstance(stream.get("candidate_identities"),list):
        raise ValueError("Missing name-only stream candidates")
    expected={}
    ids=set()
    for row in stream["candidate_identities"]:
        cid=row.get("channel_id")
        hashes=row.get("source_url_sha256")
        if (not isinstance(cid,str) or not cid or cid in ids or
            not isinstance(hashes,list) or
            row.get("metadata_only") is not True or
            row.get("needs_exact_identity_and_real_av") is not True):
            raise ValueError("Malformed candidate identity review")
        ids.add(cid)
        for h in hashes:
            if not isinstance(h,str) or not HEX.fullmatch(h) or h in expected:
                raise ValueError("Duplicate or unsafe candidate stream hash")
            expected[h]=cid
    if (len(ids)!=stream.get("name_only_candidate_identities") or
        len(expected)!=stream.get("name_only_candidate_hashes") or
        len(ids)>600 or len(expected)>150000):
        raise ValueError("Name candidate coverage mismatch")
    return expected

def match_sources(expected,source_results,names):
    """Exact URL SHA, unambiguous authoritative display name and no conflicting TVG ID."""
    from traz_gap_crosswalk import canonical_tvg_id
    from traz_missing_name_xmltv_review import key
    matched={}
    statuses={}
    for sid,rows,status in source_results:
        if sid in statuses:raise ValueError("Duplicate fetched M3U source")
        statuses[sid]=status
        if status!="FETCHED":continue
        for item in rows:
            if not isinstance(item,dict) or not isinstance(item.get("url"),str):
                continue
            url=item["url"]
            h=hashlib.sha256(url.encode()).hexdigest()
            cid=expected.get(h)
            if cid is None:continue
            # Source metadata must still correspond to the authoritative
            # unique broadcaster name when the old SHA is re-fetched.
            if names.get(key(item.get("name")))!=cid:continue
            raw_tvg=item.get("tvg_id") or ""
            if raw_tvg and canonical_tvg_id(raw_tvg,[sid])!=cid.casefold():
                continue
            prior=matched.setdefault(h,{"url":url,"channel_id":cid,"source_ids":set()})
            if prior["url"]!=url or prior["channel_id"]!=cid:
                raise ValueError("Source identity hash collision")
            prior["source_ids"].add(sid)
    return matched,statuses

def aggregate(expected,matched,statuses,checks):
    if set(checks)!=set(matched):
        raise ValueError("Incomplete or extra URL FFmpeg probe")
    rows=[]
    for h,cid in sorted(expected.items()):
        p=checks.get(h)
        if p is None:
            row={"url_sha256":h,"channel_id_metadata_hint":cid,
                 "status":"SOURCE_NO_LONGER_MATCHES_NAME_AND_HASH",
                 "decoded":False}
        else:
            if (p.get("url_sha256")!=h or p.get("decoded") not in (True,False) or
                not isinstance(p.get("status"),str) or
                (p["decoded"] and (p["status"]!="VIDEO_AUDIO_DECODED" or
                     p.get("video") is not True or p.get("audio") is not True))):
                raise ValueError("False FFmpeg AV result")
            row={"url_sha256":h,"channel_id_metadata_hint":cid,
                 "source_ids":sorted(matched[h]["source_ids"]),
                 "status":p["status"],"decoded":p["decoded"]}
        rows.append(row)
    verified_ids={r["channel_id_metadata_hint"] for r in rows if r["decoded"]}
    return {"schema":1,"kind":"V2_TR_AZ_NAME_ONLY_M3U_REAL_AV_UNCONFIRMED_BROADCASTER",
            "policy":"READ_ONLY_RSA_SEALED_AV_URLS_BROADCASTER_ID_PENDING",
            "name_candidate_stream_hashes":len(expected),
            "name_candidate_channel_ids":len(set(expected.values())),
            "current_exact_name_sha_source_hashes":len(matched),
            "ffmpeg_probed":len(checks),
            "video_audio_decoded_hashes":sum(x["decoded"] for x in rows),
            "av_decoded_metadata_identity_hints":len(verified_ids),
            "channel_identities_confirmed_by_video":0,
            "unmatched_source_hashes":len(expected)-len(matched),
            "source_fetch_errors":{sid:state for sid,state in statuses.items() if state!="FETCHED"},
            "results":rows,"source_metadata_is_not_broadcaster_proof":True,
            "spoken_language_verified":False,"sweden_access_verified":False,
            "long_term_uptime_verified":False,"ibo_device_verified":False,
            "protected_playlist_modified":False,
            "old_historical_orphan_50_auto_recovered":False}

def run(workers=20):
    import shutil
    from final_batch_acceptance import HISTORY,HISTORY_SHA,LIVE,LIVE_BLOB,gitblob,sha,fetch_one,probe,KEY
    from stage3_sealed_export import seal_rows
    from traz_api_source_batch import fetch_api
    from traz_missing_target_av import configured_sources
    from traz_missing_name_xmltv_review import registry_names
    if not 1<=workers<=24:raise ValueError("Invalid probe worker count")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("Actual media probes not installed")
    if sha(HISTORY.read_bytes())!=HISTORY_SHA or gitblob(LIVE.read_bytes())!=LIVE_BLOB:
        raise ValueError("Protected IBO or history bytes changed")
    if CANDIDATES.is_symlink() or not CANDIDATES.is_file() or CANDIDATES.stat().st_size>10000000:
        raise ValueError("Missing prior immutable name review")
    expected=targets(json.loads(CANDIDATES.read_text(encoding="utf-8")))
    names,_=registry_names(fetch_api("channels"))
    configured=configured_sources()
    with ThreadPoolExecutor(max_workers=16) as pool:
        sources=list(pool.map(fetch_one,list(configured.values())))
    found,statuses=match_sources(expected,sources,names)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        probes=list(pool.map(probe,[(h,d["url"]) for h,d in sorted(found.items())]))
    checks={p["url_sha256"]:p for p in probes}
    if len(checks)!=len(probes):raise ValueError("Duplicate FFmpeg check")
    report=aggregate(expected,found,statuses,checks)
    sealed=[{"url":d["url"],"url_sha256":h,"channel_id_metadata_hint":d["channel_id"],
             "source_ids":sorted(d["source_ids"]),
             "av_decoded":True,"broadcaster_identity_verified":False}
            for h,d in sorted(found.items()) if checks[h]["decoded"]]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    seal_rows(sealed,KEY,SEALED)
    report["rsa_sealed_av"]={"name":SEALED.name,
                             "records_encrypted":len(sealed),
                             "sha256":sha(SEALED.read_bytes())}
    OUT.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("TR_AZ_NAME_ONLY_REAL_AV",json.dumps({
        "name_candidate_hashes":report["name_candidate_stream_hashes"],
        "matched_current_sources":report["current_exact_name_sha_source_hashes"],
        "probed":report["ffmpeg_probed"],
        "av_decoded_metadata_hints":report["av_decoded_metadata_identity_hints"],
        "decoded_urls":report["video_audio_decoded_hashes"],
        "confirmed_channel_ids":0},sort_keys=True))

if __name__=="__main__":
    run()
