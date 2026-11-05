#!/usr/bin/env python3
"""Review exact TR/AZ IPTV API + real FFmpeg evidence without another scan.

Produces one anonymous, actionable queue for source repair, missing EPG,
real AV candidates and their alternatives. One successful AV sample is never
claimed to prove Swedish access, spoken language, stability or IBO playback.
Never reads plaintext stream URLs or writes any playlist.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
API=ROOT/"v2/reports/ci/traz-api-source-audit.json"
AV=ROOT/"v2/reports/ci/traz-api-av-acceptance.json"
OUT=ROOT/"v2/reports/ci/traz-api-next-bulk-review.json"
SHA=re.compile(r"[0-9a-f]{64}\Z")
MAX_ROWS=120000

def checked_rows(doc, key, kind, policy):
    if not isinstance(doc,dict) or doc.get("schema")!=1 or doc.get("kind")!=kind or doc.get("policy")!=policy:
        raise ValueError("Invalid "+key+" report source")
    rows=doc.get(key)
    if not isinstance(rows,list) or len(rows)>MAX_ROWS:
        raise ValueError("Unbounded or missing "+key+" records")
    if doc.get("protected_playlist_modified") is not False or doc.get("ibo_device_verified") is not False:
        raise ValueError("Unexpected production change or device claim")
    return rows

def audit(api,av):
    metadata=checked_rows(api,"stream_references","TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
                           "READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES")
    probes=checked_rows(av,"streams","TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE",
                        "ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS")
    if (api.get("unique_channel_url_pairs")!=len(metadata)
            or av.get("unique_url_candidates")!=len(probes)
            or av.get("probed")!=len(probes)
            or av.get("unprobed")!=0):
        raise ValueError("Incomplete or unverified source/AV coverage")
    by_hash=defaultdict(dict)
    for m in metadata:
        if not isinstance(m,dict) or "url" in m:
            raise ValueError("Unsafe public metadata row")
        h,cid=m.get("url_sha256"),m.get("channel_id")
        if not isinstance(h,str) or not SHA.fullmatch(h) or not isinstance(cid,str) or not cid:
            raise ValueError("Bad API URL hash or broadcaster ID")
        if cid in by_hash[h]:
            raise ValueError("Duplicate API channel URL association")
        by_hash[h][cid]=m
    seen=set()
    good=defaultdict(list)
    failures=defaultdict(list)
    statuses=Counter()
    for p in probes:
        if not isinstance(p,dict) or "url" in p:
            raise ValueError("Unsafe public AV row")
        h=p.get("url_sha256")
        if not isinstance(h,str) or not SHA.fullmatch(h) or h in seen or h not in by_hash:
            raise ValueError("Missing, unknown or duplicate AV hash")
        seen.add(h)
        ids=p.get("channel_ids")
        if not isinstance(ids,list) or sorted(ids)!=sorted(by_hash[h]):
            raise ValueError("AV hash matched to wrong channel identity")
        decoded=p.get("decoded")
        state=p.get("status")
        if not isinstance(state,str):
            raise ValueError("Missing AV probe status")
        if decoded is True and (
            state!="VIDEO_AUDIO_DECODED" or p.get("video") is not True or p.get("audio") is not True):
            raise ValueError("False audio+video decode status")
        if state=="VIDEO_AUDIO_DECODED" and decoded is not True:
            raise ValueError("False success status")
        statuses[state]+=1
        for cid in ids:
            row=by_hash[h][cid]
            item={"url_sha256":h,"status":state,
                  "country_metadata":row.get("country_metadata"),
                  "feed_language_metadata":row.get("feed_language_metadata") or [],
                  "epg_guide_reference":row.get("epg_guide_reference") is True,
                  "declared_quality_not_measured":row.get("declared_quality") or None,
                  "geo_label_only_not_tested_in_sweden":row.get("geo_label_only") is True,
                  "requires_custom_headers":row.get("custom_headers_needed") is True}
            (good if decoded is True else failures)[cid].append(item)
    if seen!=set(by_hash) or sum(statuses.values())!=av["unique_url_candidates"]:
        raise ValueError("API / AV hash coverage is not exact")
    if statuses!=Counter(av.get("status_counts") or {}):
        raise ValueError("AV status totals altered")
    if sum(state=="VIDEO_AUDIO_DECODED" for state in (p["status"] for p in probes))!=av.get("video_audio_decoded"):
        raise ValueError("Actual FFmpeg decoded count mismatch")
    identities=sorted(set(good)|set(failures))
    channel_rows=[]
    for cid in identities:
        success=sorted(good.get(cid,[]),key=lambda x:x["url_sha256"])
        failed=sorted(failures.get(cid,[]),key=lambda x:x["url_sha256"])
        channel_rows.append({
           "channel_id":cid,
           "status":"AV_DECODED_DEVICE_PENDING" if success else "NO_CURRENT_AV_PROOF",
           "decoded_stream_hashes":[r["url_sha256"] for r in success],
           "decoded_stream_count":len(success),
           "alternative_decoded_streams":max(len(success)-1,0),
           "unverified_stream_hashes":[r["url_sha256"] for r in failed],
           "unverified_statuses":dict(Counter(r["status"] for r in failed)),
           "has_epg_reference":any(r["epg_guide_reference"] for r in success+failed),
           "geo_label_only_not_sweden_access_proof":any(r["geo_label_only_not_tested_in_sweden"] for r in success+failed),
           "custom_header_candidates":any(r["requires_custom_headers"] for r in success+failed),
           "quality_and_codecs":"MEASUREMENT_NOT_IN_THIS_REPORT",
           "spoken_language":"UNVERIFIED_METADATA_ONLY",
           "sweden_access":"UNVERIFIED_NO_SWEDEN_BASED_PROBE",
           "reliability_score":None,
           "reliability_reason":"ONLY_ONE_TIME_GROUPED_AV_SNAPSHOT_NO_STABILITY_OR_IBO_PROOF",
           "ibo_device_verified":False})
    missing_epg=api.get("identities_missing_epg")
    missing_stream=api.get("identities_without_stream_url_lead")
    for arr,count,name in (
       (missing_epg,api.get("target_identities_without_epg_reference"),"missing_epg"),
       (missing_stream,api.get("target_unique_channel_ids")-len(identities),"missing_stream")):
        if not isinstance(arr,list) or len(arr)!=count or len(set(arr))!=len(arr) or not all(isinstance(x,str) and x for x in arr):
            raise ValueError("Invalid "+name+" backlog")
    decoded=sum(r["decoded_stream_count"] for r in channel_rows)
    report={
       "schema":1,"kind":"V2_TR_AZ_API_SOURCE_EPG_REAL_AV_BULK_REVIEW",
       "policy":"ANONYMOUS_REVIEW_ONLY_NOT_AUTOMATIC_PLAYLIST_PROMOTION",
       "api_target_channel_ids":api["target_unique_channel_ids"],
       "source_candidates_with_stream_addresses":len(channel_rows),
       "identities_with_no_stream_url_lead":len(missing_stream),
       "missing_epg_reference_count":len(missing_epg),
       "url_hashes_tested":len(probes),"video_audio_decoded_url_hashes":av["video_audio_decoded"],
       "unverified_or_failed_url_hashes":len(probes)-av["video_audio_decoded"],
       "unprobed":0,"identities_with_decoded_av":sum(bool(x["decoded_stream_count"]) for x in channel_rows),
       "decoded_av_alternative_urls":sum(x["alternative_decoded_streams"] for x in channel_rows),
       "epg_missing_identity_queue":sorted(missing_epg),
       "source_missing_identity_queue":sorted(missing_stream),
       "individual_channels":channel_rows,
       "probe_status_counts":dict(sorted(statuses.items())),
       "spoken_language_verified":False,"sweden_access_verified":False,
       "long_term_reliability_verified":False,"ibo_device_verified":False,
       "protected_playlist_modified":False,
       "limitations":[
          "1 successful FFmpeg decode is not stable 24/7 playback",
          "API country/feed language tags are not Turkish/Azerbaijani speech evidence",
          "Guide metadata is not verified XMLTV programme accuracy",
          "No Swedish network vantage point was tested",
          "No IBO device test performed and no plaintext stream URLs exported"
       ]}
    if decoded!=report["video_audio_decoded_url_hashes"]:
        raise ValueError("AV identity and stream totals disagree")
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--api",type=Path,default=API)
    parser.add_argument("--av",type=Path,default=AV)
    parser.add_argument("--out",type=Path,default=OUT)
    args=parser.parse_args()
    for path in (args.api,args.av):
        if not path.is_file() or path.is_symlink() or path.stat().st_size>25_000_000:
            raise SystemExit("Missing or unsafe API / AV evidence input")
    result=audit(json.loads(args.api.read_text(encoding="utf-8")),
                 json.loads(args.av.read_text(encoding="utf-8")))
    if args.out.is_symlink() or args.out.suffix!=".json" or args.out.name.startswith("private"):
        raise SystemExit("Unsafe anonymous audit destination")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"api_target":result["api_target_channel_ids"],
      "verified_av_addresses":result["video_audio_decoded_url_hashes"],
      "av_backed_channel_ids":result["identities_with_decoded_av"],
      "av_alternatives":result["decoded_av_alternative_urls"],
      "no_stream_identities":result["identities_with_no_stream_url_lead"],
      "missing_epg_identities":result["missing_epg_reference_count"],
      "spoken_language_verified":False,"ibo_device_verified":False},sort_keys=True))

if __name__=="__main__":
    main()
