#!/usr/bin/env python3
"""Read-only exact-name leads for V2 missing TR/AZ streams and XMLTV schedules.

An unambiguous name is NOT a verified channel identity, playable AV, a
correct programme guide, Swedish access or IBO device evidence.
"""
import argparse
from collections import defaultdict, Counter
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
from traz_gap_crosswalk import _fetch_xmltv, EPG_CONFIG, API, M3U
from traz_api_source_batch import fetch_api

OUT=API.with_name("traz-missing-name-xmltv-review.json")
HEX=re.compile(r"[0-9a-f]{64}\Z")
MAX_CANDIDATES=150000

def key(text):
    if not isinstance(text,str) or len(text)>200 or any(ord(c)<32 for c in text):
        return ""
    return " ".join(unicodedata.normalize("NFKC",text).casefold().split())

def registry_names(channels):
    if not isinstance(channels,list) or len(channels)>600000:
        raise ValueError("Invalid bounded official channel registry")
    names=defaultdict(set)
    for row in channels:
        if not isinstance(row,dict) or not isinstance(row.get("id"),str):
            continue
        cid=row["id"]
        if not 0<len(cid)<=200:continue
        alternates=row.get("alt_names") if isinstance(row.get("alt_names"),list) else []
        if len(alternates)>100:raise ValueError("Unbounded aliases")
        for name in [row.get("name")]+alternates:
            n=key(name)
            if len(n)>=4:names[n].add(cid)
    return ({n:next(iter(ids)) for n,ids in names.items() if len(ids)==1},
            sum(len(ids)>1 for ids in names.values()))

def verify_inputs(api,scan,gap):
    if (not isinstance(api,dict) or api.get("schema")!=1 or
        api.get("kind")!="TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS" or
        api.get("policy")!="READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES" or
        api.get("protected_playlist_modified") is not False or
        api.get("all_streams_av_verified") is not False or
        not isinstance(scan,dict) or scan.get("schema")!=1 or
        scan.get("candidate_status")!="UNVERIFIED" or
        scan.get("playback_verified") is not False or
        not isinstance(gap,dict) or gap.get("schema")!=1 or
        gap.get("kind")!="V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE" or
        gap.get("protected_playlist_modified") is not False):
        raise ValueError("Untrusted API/M3U/XMLTV evidence")
    rows=scan.get("candidates")
    if not isinstance(rows,list) or len(rows)>MAX_CANDIDATES:
        raise ValueError("Invalid candidate inventory")
    ids=api.get("identities_without_stream_url_lead")
    guides=api.get("identities_missing_epg")
    if (not isinstance(ids,list) or not isinstance(guides,list) or
        len(set(ids))!=len(ids) or len(set(guides))!=len(guides) or
        len(ids)!=gap.get("missing_api_stream_identities") or
        len(guides)!=gap.get("missing_api_epg_references") or
        len(rows)!=scan.get("total_unique_candidates")):
        raise ValueError("Mismatched API source coverage")
    exact_ids={r["channel_id"] for r in gap.get("candidate_identities",[])
               if r.get("candidate_count",0)>0}
    if (len(exact_ids)!=gap.get("exact_missing_stream_identities_with_other_m3u_leads")
        or not exact_ids.issubset(set(ids))):
        raise ValueError("Inconsistent exact-ID crosswalk")
    xml=gap.get("epg_xmltv")
    if not isinstance(xml,dict) or not isinstance(xml.get("exact_xmltv_candidate_ids"),list):
        raise ValueError("Missing XMLTV exact-ID evidence")
    return set(ids)-exact_ids,set(guides)-set(xml["exact_xmltv_candidate_ids"])

def stream_name_review(api,scan,gap,channels):
    missing,epg_missing=verify_inputs(api,scan,gap)
    names,ambiguous=registry_names(channels)
    candidates=defaultdict(set)
    conflicting=0
    seen=set()
    for row in scan["candidates"]:
        if not isinstance(row,dict) or any(
            k in row for k in ("url","stream_url","raw_url","href")):
            raise ValueError("Unsafe plaintext or malformed M3U candidate")
        h=row.get("url_sha256")
        if not isinstance(h,str) or not HEX.fullmatch(h) or h in seen:
            raise ValueError("Duplicate or invalid URL SHA256")
        seen.add(h)
        cid=names.get(key(row.get("name")))
        if cid not in missing:continue
        tvg=row.get("tvg_id") or ""
        if not isinstance(tvg,str):raise ValueError("Malformed tvg-id")
        if tvg.strip() and tvg.strip().casefold()!=cid.casefold():
            conflicting+=1
            continue
        candidates[cid].add(h)
    rows=[{"channel_id":cid,"source_url_sha256":sorted(hashes),
           "metadata_only":True,"needs_exact_identity_and_real_av":True}
          for cid,hashes in sorted(candidates.items())]
    return ({"missing_without_exact_id_source":len(missing),
             "unambiguous_registry_names":len(names),
             "ambiguous_registry_names_rejected":ambiguous,
             "name_only_candidate_identities":len(rows),
             "name_only_candidate_hashes":sum(len(x["source_url_sha256"]) for x in rows),
             "conflicting_tvg_id_rows_rejected":conflicting,
             "still_without_name_lead":len(missing)-len(rows),
             "candidate_identities":rows},names,epg_missing)

def xmltv_display_candidates(raw,names,wanted):
    if not isinstance(raw,bytes) or len(raw)>110000000:
        raise ValueError("Invalid XMLTV size")
    channel_matches=defaultdict(set)
    programmes=Counter()
    current_id=None
    try:
        parser=ET.iterparse(io.BytesIO(raw),events=("start","end"))
        event,root=next(parser)
        if event!="start" or root.tag!="tv":raise ValueError("Not XMLTV")
        for event,el in parser:
            if event=="start" and el.tag=="channel":
                current_id=el.get("id")
            elif event=="end" and el.tag=="display-name" and current_id:
                cid=names.get(key(el.text))
                if cid in wanted:channel_matches[cid].add(current_id)
                el.clear()
            elif event=="end" and el.tag=="channel":
                current_id=None
                el.clear()
            elif event=="end" and el.tag=="programme":
                pid=el.get("channel")
                if isinstance(pid,str):programmes[pid]+=1
                el.clear()
    except (ET.ParseError,StopIteration) as exc:
        raise ValueError("Malformed XMLTV") from exc
    with_programme={cid for cid,ids in channel_matches.items()
                    if any(programmes[pid]>0 for pid in ids)}
    return channel_matches,with_programme

def epg_review(wanted,names,sources,fetcher=_fetch_xmltv):
    if not isinstance(sources,list) or len(sources)>12:
        raise ValueError("Unsafe XMLTV source list")
    matched=defaultdict(set)
    with_programme=set()
    audits=[]
    for url in sources:
        source_sha=hashlib.sha256(url.encode()).hexdigest() if isinstance(url,str) else None
        try:
            hits,programmes=xmltv_display_candidates(fetcher(url),names,wanted)
            for cid,ids in hits.items():
                for pid in ids:
                    matched[cid].add((source_sha,hashlib.sha256(pid.encode()).hexdigest()))
            with_programme.update(programmes)
            audits.append({"xmltv_source_sha256":source_sha,
                           "status":"XMLTV_PARSED_METADATA_ONLY",
                           "matched_guide_identities":len(hits)})
        except (OSError,ValueError,TypeError,UnicodeError,EOFError) as exc:
            audits.append({"xmltv_source_sha256":source_sha,
                           "status":"XMLTV_UNVERIFIED_"+type(exc).__name__,
                           "matched_guide_identities":0})
    rows=[{"channel_id":cid,
           "provider_xmltv_ids_sha256":sorted({pid for _,pid in links}),
           "xmltv_source_sha256":sorted({src for src,_ in links}),
           "programme_records_seen":cid in with_programme,
           "metadata_only_not_correct_schedule":True}
          for cid,links in sorted(matched.items())]
    return {"missing_without_exact_xmltv_id":len(wanted),
            "display_name_review_identities":len(rows),
            "with_programme_records":len(with_programme),
            "still_without_display_name_lead":len(wanted)-len(rows),
            "all_sources_parsed":bool(audits) and all(
                a["status"]=="XMLTV_PARSED_METADATA_ONLY" for a in audits),
            "source_results":audits,"candidate_identities":rows}

def build(api,scan,gap,channels,sources,fetcher=_fetch_xmltv):
    streams,names,epg_missing=stream_name_review(api,scan,gap,channels)
    guides=epg_review(epg_missing,names,sources,fetcher)
    return {"schema":1,"kind":"V2_TR_AZ_STREAM_XMLTV_EXACT_NAME_REVIEW",
            "policy":"READ_ONLY_METADATA_LEADS_NOT_VIDEO_AUDIO_OR_EPG_ACCURACY",
            "stream_name_review":streams,"epg_name_review":guides,
            "new_av_proof":0,"spoken_language_verified":False,
            "sweden_access_verified":False,"epg_schedule_accuracy_verified":False,
            "ibo_device_verified":False,"old_historical_orphan_50_auto_recovered":False,
            "protected_playlist_modified":False}

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--out",type=Path,default=OUT)
    opts=arg.parse_args()
    paths=[API,M3U,API.with_name("traz-missing-stream-epg-crosswalk.json"),EPG_CONFIG]
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size>85000000 for p in paths):
        raise SystemExit("Missing real crosswalk source inputs")
    api,scan,gap,config=[json.loads(p.read_text(encoding="utf-8")) for p in paths]
    result=build(api,scan,gap,fetch_api("channels"),config.get("sources"))
    if opts.out.is_symlink() or opts.out.suffix!=".json" or opts.out.name.startswith("private"):
        raise SystemExit("Unsafe public report destination")
    opts.out.parent.mkdir(parents=True,exist_ok=True)
    opts.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("TR_AZ_STREAM_XMLTV_NAME_REVIEW",json.dumps({
        "name_source_identities":result["stream_name_review"]["name_only_candidate_identities"],
        "source_identities_still_missing":result["stream_name_review"]["still_without_name_lead"],
        "xmltv_name_identities":result["epg_name_review"]["display_name_review_identities"],
        "xmltv_identities_still_missing":result["epg_name_review"]["still_without_display_name_lead"],
        "new_av_proof":0},sort_keys=True))

if __name__=="__main__":main()
