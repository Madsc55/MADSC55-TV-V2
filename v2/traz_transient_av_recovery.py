#!/usr/bin/env python3
"""One bounded FFmpeg retry for transient TR/AZ failures, never all 158 again.

Resolves exact previously recorded URL SHA+TVG ID through authenticated current
source rows. Old decoded evidence remains immutable. Unavailable sources never
erase historical identities. New successful stream URLs are RSA/AES sealed.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"v2/reports/ci/traz-missing-target-real-av.json"
OLD_SEALED=ROOT/"v2/reports/ci/traz-missing-target-av.sealed"
GAP=ROOT/"v2/reports/ci/traz-missing-stream-epg-crosswalk.json"
OUT=ROOT/"v2/reports/ci/traz-transient-av-retry.json"
SEALED=ROOT/"v2/reports/ci/traz-transient-av-retry.sealed"
SHA=re.compile(r"[0-9a-f]{64}\Z")
RETRYABLE=frozenset({
    "PROBE_FAILED_NETWORK_TIMEOUT",
    "PROBE_FAILED_HTTP_RESPONSE_ERROR",
    "PROBE_FAILED_UNKNOWN_NETWORK_OR_MEDIA_ERROR",
    "UNSAFE_OR_UNRESOLVED_HOST",
    "VIDEO_ONLY",
    "PROBE_UNCONFIRMED",
    "VIDEO_AUDIO_STREAMS_ONLY",
})

def select_retry(prior,gap):
    if (not isinstance(prior,dict) or prior.get("schema")!=1 or
        prior.get("kind")!="V2_TR_AZ_MISSING_M3U_REAL_AV_READONLY" or
        prior.get("policy")!="PUBLIC_SHA_ONLY_RSA_AES_SEALED_STREAM_URLS" or
        prior.get("protected_playlist_modified") is not False or
        prior.get("ibo_device_verified") is not False or
        prior.get("old_historical_orphan_50_auto_recovered") is not False or
        not isinstance(gap,dict) or gap.get("schema")!=1 or
        gap.get("kind")!="V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE" or
        gap.get("protected_playlist_modified") is not False):
        raise ValueError("Untrusted real FFmpeg or source provenance")
    results=prior.get("results")
    groups=gap.get("candidate_identities")
    if (not isinstance(results,list) or not isinstance(groups,list) or
        len(results)!=prior.get("candidate_hashes") or
        len(results)>5000):
        raise ValueError("Incomplete original URL SHA evidence")
    expected={}
    for group in groups:
        cid=group.get("channel_id")
        rows=group.get("candidate_m3u_url_hashes")
        if not isinstance(cid,str) or not isinstance(rows,list) or len(rows)!=group.get("candidate_count"):
            raise ValueError("Invalid original exact broadcaster target")
        for row in rows:
            h=row.get("url_sha256")
            if (not isinstance(h,str) or not SHA.fullmatch(h) or
                h in expected or row.get("av_verified") is not False):
                raise ValueError("Duplicate or false source hash")
            expected[h]=cid
    if len(expected)!=len(results):
        raise ValueError("Different original source target inventory")
    retry={}
    known_av=set()
    counts=Counter()
    source_matched=0
    for row in results:
        if not isinstance(row,dict) or "url" in row:
            raise ValueError("Unsafe original target AV row")
        h=row.get("url_sha256")
        cid=row.get("exact_channel_id")
        if h not in expected or expected.pop(h)!=cid:
            raise ValueError("Wrong or duplicated URL hash channel association")
        status=row.get("status")
        decoded=row.get("decoded")
        source_ids=row.get("source_ids")
        if (not isinstance(status,str) or type(decoded) is not bool
            or not isinstance(source_ids,list) or len(source_ids)>30
            or any(not isinstance(s,str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,96}",s)
                   or "://" in s for s in source_ids)):
            raise ValueError("Malformed previous source or FFmpeg result")
        if status!="NOT_FOUND_IN_CURRENT_SOURCE":source_matched+=1
        if decoded:
            if status!="VIDEO_AUDIO_DECODED" or row.get("video") is not True or row.get("audio") is not True:
                raise ValueError("Fabricated previous AV")
            known_av.add(cid)
        elif status in RETRYABLE and source_ids:
            retry[h]={"channel_id":cid,"source_ids":set(source_ids)}
        counts[status]+=1
    if (expected or dict(counts)!=prior.get("av_status_counts") or
        source_matched!=prior.get("matched_current_source_hashes") or
        len(results)-source_matched!=prior.get("unmatched_or_unavailable_hashes") or
        sum(x=="VIDEO_AUDIO_DECODED" for x in counts.elements())!=prior.get("real_video_audio_decoded_hashes") or
        len(known_av)!=prior.get("real_video_audio_channel_ids")):
        raise ValueError("Tampered original FFmpeg totals")
    return retry,known_av,counts

def aggregate(targets,known_av,found,source_statuses,unknown,proofs,old_status_counts):
    if set(proofs)!=set(found):
        raise ValueError("Live real FFmpeg coverage missing")
    rows=[]
    added_ids=set()
    for h,item in sorted(targets.items()):
        p=proofs.get(h)
        if p is None:
            rows.append({"url_sha256":h,"channel_id":item["channel_id"],
                         "status":"NOT_FOUND_IN_FRESH_SOURCE","decoded":False})
        else:
            if (p.get("url_sha256")!=h or type(p.get("decoded")) is not bool or
                not isinstance(p.get("status"),str) or
                (p["decoded"] and (p.get("status")!="VIDEO_AUDIO_DECODED" or
                                     p.get("video") is not True or p.get("audio") is not True)) or
                (not p["decoded"] and p.get("status")=="VIDEO_AUDIO_DECODED")):
                raise ValueError("Fake FFmpeg recovery")
            rows.append({"url_sha256":h,"channel_id":item["channel_id"],
                         "status":p["status"],"decoded":p["decoded"]})
            if p["decoded"]:
                added_ids.add(item["channel_id"])
    new_only=sorted(added_ids-known_av)
    return {"schema":1,"kind":"V2_TR_AZ_TRANSIENT_TARGET_REAL_AV_RETRY",
            "policy":"READ_ONLY_NEW_RSA_SEALED_FFMPEG_PROOF_ONLY",
            "original_av_channel_identities":len(known_av),
            "retryable_original_hashes":len(targets),
            "recovered_exact_current_url_hashes":len(found),
            "reprobed_url_hashes":len(proofs),
            "previous_failures_not_retried":sum(old_status_counts.values())-len(targets),
            "fresh_video_audio_decoded_hashes":sum(x["decoded"] for x in rows),
            "fresh_video_audio_channel_ids":len(added_ids),
            "additional_channel_ids_not_previously_av_proven":new_only,
            "new_distinct_av_identities":len(new_only),
            "unavailable_original_url_hashes":len(targets)-len(found),
            "source_fetch_errors":{k:v for k,v in source_statuses.items() if v!="FETCHED"},
            "source_id_references_no_longer_resolvable":unknown,
            "results":rows,
            "old_historical_orphan_50_auto_recovered":False,
            "long_term_uptime_verified":False,
            "spoken_language_verified":False,"sweden_access_verified":False,
            "ibo_device_verified":False,"protected_playlist_modified":False}

def main():
    from final_batch_acceptance import HISTORY,HISTORY_SHA,LIVE,LIVE_BLOB,gitblob,fetch_one,probe,KEY,sha
    from traz_missing_target_av import configured_sources,source_selection,match_fetched
    from stage3_sealed_export import seal_rows
    import shutil
    parser=argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=16)
    opt=parser.parse_args()
    if not 1<=opt.workers<=24:parser.error("Invalid bounded worker count")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("Real FFmpeg and ffprobe required")
    if sha(HISTORY.read_bytes())!=HISTORY_SHA or gitblob(LIVE.read_bytes())!=LIVE_BLOB:
        raise SystemExit("Protected playlist or 4955 historical identity bytes changed")
    for p in (EVIDENCE,OLD_SEALED,GAP):
        if p.is_symlink() or not p.is_file() or p.stat().st_size>10000000:
            raise SystemExit("Original encrypted FFmpeg/source artifact is missing")
    prior=json.loads(EVIDENCE.read_text())
    gap=json.loads(GAP.read_text())
    envelope=prior.get("rsa_sealed_matches")
    if not isinstance(envelope,dict) or envelope.get("sha256")!=sha(OLD_SEALED.read_bytes()):
        raise SystemExit("Original RSA source evidence digest mismatch")
    targets,old_ids,old_counts=select_retry(prior,gap)
    selected,unknown=source_selection(targets,configured_sources())
    with ThreadPoolExecutor(max_workers=12) as pool:
        outputs=list(pool.map(fetch_one,selected))
    matched,statuses=match_fetched(targets,outputs)
    with ThreadPoolExecutor(max_workers=opt.workers) as pool:
        probes=list(pool.map(probe,[(h,d["url"]) for h,d in sorted(matched.items())]))
    checks={r["url_sha256"]:r for r in probes}
    if len(checks)!=len(probes):raise ValueError("Duplicate live FFmpeg results")
    report=aggregate(targets,old_ids,matched,statuses,unknown,checks,old_counts)
    sealed=[{"url":d["url"],"url_sha256":h,
             "channel_id":d["channel_id"],"source_ids":sorted(d["source_ids"]),
             "status":"VIDEO_AUDIO_DECODED","av_decoded":True}
            for h,d in sorted(matched.items()) if checks[h]["decoded"]]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    seal_rows(sealed,KEY,SEALED)
    report["new_rsa_evidence"]={"name":SEALED.name,
                                "sha256":sha(SEALED.read_bytes()),
                                "records_encrypted":len(sealed)}
    OUT.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("TR_AZ_TRANSIENT_AV_BULK",json.dumps({
        "selected_retries":report["retryable_original_hashes"],
        "real_ffmpeg_reprobed":report["reprobed_url_hashes"],
        "newly_av_proven_identities":report["new_distinct_av_identities"],
        "fresh_decoded_urls":report["fresh_video_audio_decoded_hashes"],
        "old_success_preserved":len(old_ids),
        "missing_source_hashes":report["unavailable_original_url_hashes"]},sort_keys=True))

if __name__=="__main__":main()
