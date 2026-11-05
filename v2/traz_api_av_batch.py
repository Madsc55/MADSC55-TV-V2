#!/usr/bin/env python3
"""Real, read-only FFmpeg video+audio batch for IPTV API candidates.

API references, HTTP success and FFprobe tracks are not playback proof.
The stream URLs are stored ONLY in RSA/AES encrypted artifact. Never touches
the production IBO playlist, backups, historic IDs or favorites.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import shutil
import time
from final_batch_acceptance import ROOT,LIVE,LIVE_BLOB,HISTORY,HISTORY_SHA,gitblob,sha,probe
from stage3_sealed_export import seal_rows
from traz_api_source_batch import KINDS,build,fetch_api,public_stream

REPORT=ROOT/"v2/reports/ci/traz-api-av-acceptance.json"
SEALED=ROOT/"v2/reports/ci/traz-api-av-evidence.sealed"
RSA_PUBLIC=ROOT/"v2/config/stage5_recovery_public.pem"

def prepare(rows):
    unique={}
    for r in rows:
        url=r.get("url")
        cid=r.get("channel_id")
        if not isinstance(cid,str) or not cid or not public_stream(url):
            raise ValueError("Unsafe or unidentified IPTV API URL")
        h=sha(url)
        record=unique.setdefault(h,{"url":url,"channel_ids":set(),"custom_headers":False})
        if record["url"]!=url:
            raise ValueError("SHA256 collision")
        record["channel_ids"].add(cid)
        record["custom_headers"]|=bool(r.get("referrer") or r.get("user_agent"))
    return unique

def summarize(unique,probes):
    items=[]
    for digest,lead in sorted(unique.items()):
        result=probes.get(digest,{"status":"NOT_PROBED_BUDGET",
            "video":False,"audio":False,"decoded":False,"audio_lang_tags":[]})
        if result.get("url_sha256",digest)!=digest:
            raise ValueError("Incorrect URL to playback evidence attribution")
        if result.get("decoded") is True and (
             result.get("status")!="VIDEO_AUDIO_DECODED" or
             result.get("video") is not True or result.get("audio") is not True):
            raise ValueError("False video+audio decode claim")
        items.append({"url_sha256":digest,"channel_ids":sorted(lead["channel_ids"]),
           "status":result["status"],"video":result["video"],"audio":result["audio"],
           "decoded":result["decoded"],"custom_headers_needed":lead["custom_headers"],
           "spoken_language_verified":False,"sweden_access_verified":False,
           "ibo_device_verified":False})
    return {"schema":1,"kind":"TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE",
       "policy":"ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS",
       "unique_url_candidates":len(items),"probed":len(probes),
       "unprobed":len(items)-len(probes),
       "video_audio_decoded":sum(row["decoded"] is True for row in items),
       "status_counts":dict(sorted(Counter(row["status"] for row in items).items())),
       "protected_playlist_modified":False,"spoken_language_verified":False,
       "sweden_access_verified":False,"ibo_device_verified":False,
       "one_time_av_does_not_prove_long_term_stability":True,
       "streams":items}

def validate():
    d=json.loads(REPORT.read_text(encoding="utf-8"))
    if d.get("kind")!="TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE":
        raise ValueError("Invalid real AV report")
    for key in ("protected_playlist_modified","spoken_language_verified",
                "sweden_access_verified","ibo_device_verified"):
        if d.get(key) is not False:
            raise ValueError("False AV, geography, device or production claim")
    if len(d.get("streams",[]))!=d.get("unique_url_candidates"):
        raise ValueError("Missing URL hash evidence")
    manifest=d.get("encrypted_evidence") or {}
    if manifest.get("sha256")!=sha(SEALED.read_bytes()) or (
       manifest.get("records")!=d["unique_url_candidates"]):
        raise ValueError("Encrypted URL evidence hash mismatch")
    if any(("url" in row or "referrer" in row or row["decoded"] and
            (row["status"]!="VIDEO_AUDIO_DECODED" or not row["video"] or not row["audio"]))
           for row in d["streams"]):
        raise ValueError("Leaked URL or invalid video+audio proof")
    return d

def scan(workers=24,budget=3300):
    if sha(HISTORY.read_bytes())!=HISTORY_SHA or gitblob(LIVE.read_bytes())!=LIVE_BLOB:
        raise RuntimeError("Protected source or IBO playlist changed")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Real ffmpeg and ffprobe binaries required")
    api={kind:fetch_api(kind) for kind in KINDS}
    metadata,leads=build(*(api[k] for k in KINDS))
    unique=prepare(leads)
    if not 0<len(unique)<=4955:
        raise RuntimeError("Unexpected API URL batch size")
    pairs=sorted(unique.items())
    checks={}
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for offset in range(0,len(pairs),64):
            if time.monotonic()-started>=budget:
                break
            current=[(h,item["url"]) for h,item in pairs[offset:offset+64]]
            for result in executor.map(probe,current):
                checks[result["url_sha256"]]=result
            print("TR_AZ_REAL_AV_BULK",len(checks),"/",len(pairs),flush=True)
    public=summarize(unique,checks)
    public["target_channel_identities"]=metadata["target_unique_channel_ids"]
    public["target_epg_identities"]=metadata["epg_target_identities"]
    sealed_rows=[]
    for digest,item in pairs:
        result=checks.get(digest,{"status":"NOT_PROBED_BUDGET",
                                 "video":False,"audio":False,"decoded":False})
        sealed_rows.append({"url":item["url"],"url_sha256":digest,
           "channel_ids":sorted(item["channel_ids"]),
           "probe_status":result["status"],"video":result["video"],
           "audio":result["audio"],"decoded":result["decoded"]})
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    seal_rows(sealed_rows,RSA_PUBLIC,SEALED)
    public["encrypted_evidence"]={"sha256":sha(SEALED.read_bytes()),
                                  "records":len(sealed_rows),"name":SEALED.name}
    REPORT.write_text(json.dumps(public,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    validate()
    print("TR_AZ_REAL_AV_RESULT",json.dumps({
       "unique_urls":public["unique_url_candidates"],"probed":public["probed"],
       "real_video_audio_decoded":public["video_audio_decoded"],
       "unprobed":public["unprobed"]},sort_keys=True),flush=True)
    if public["unprobed"]:
        raise RuntimeError("Incomplete real AV scan; sealed evidence retained")

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--workers",type=int,default=24)
    a.add_argument("--budget-seconds",type=int,default=3300)
    a.add_argument("--validate-only",action="store_true")
    args=a.parse_args()
    if not 1<=args.workers<=32 or not 60<=args.budget_seconds<=5400:
        a.error("Invalid controlled AV budget")
    if args.validate_only:
        d=validate()
        if d["unprobed"]:
            raise SystemExit("Real AV probe coverage incomplete")
        print("AV_EVIDENCE_VALIDATED",d["video_audio_decoded"])
    else: scan(args.workers,args.budget_seconds)

if __name__=="__main__":
    main()
