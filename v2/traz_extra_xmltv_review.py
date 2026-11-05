#!/usr/bin/env python3
"""Try bounded additional public XMLTV sources for previously unmatched TR/AZ IDs.

A channel/alias in a guide and a programme record are metadata, not confirmed
schedules, speech, playback or IBO device proof. Original five-source evidence
is immutable. This is a strictly additional read-only crosswalk.
"""
from collections import Counter,defaultdict
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from traz_api_source_batch import fetch_api
from traz_missing_name_xmltv_review import registry_names,key
from traz_gap_crosswalk import _fetch_xmltv,API,ROOT

PREV=ROOT/"v2/reports/ci/traz-missing-name-xmltv-review.json"
GAP=ROOT/"v2/reports/ci/traz-missing-stream-epg-crosswalk.json"
OUT=ROOT/"v2/reports/ci/traz-additional-xmltv-gap.json"
SOURCES=(
    "https://dearbulut.github.io/iptv/epg/tr.xml.gz",
    "https://dearbulut.github.io/iptv/epg/az.xml.gz",
    "https://dearbulut.github.io/iptv/epg/guide.xml.gz",
    "https://iptvx.one/epg/epg.xml.gz",
)
TIME=re.compile(r"^(\d{14})\s+([+-]\d{4})$")

def sha(x):return hashlib.sha256(x.encode("utf-8")).hexdigest()

def remaining_guide_ids(api,gap,previous):
    if (not isinstance(api,dict) or api.get("schema")!=1 or
        api.get("kind")!="TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS" or
        api.get("policy")!="READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES" or
        api.get("protected_playlist_modified") is not False or
        not isinstance(gap,dict) or gap.get("schema")!=1 or
        gap.get("kind")!="V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE" or
        gap.get("protected_playlist_modified") is not False or
        not isinstance(previous,dict) or previous.get("schema")!=1 or
        previous.get("kind")!="V2_TR_AZ_STREAM_XMLTV_EXACT_NAME_REVIEW" or
        previous.get("protected_playlist_modified") is not False):
        raise ValueError("Untrusted previous XMLTV gap evidence")
    old=api.get("identities_missing_epg")
    exact=gap.get("epg_xmltv")
    name=previous.get("epg_name_review")
    if (not isinstance(old,list) or len(old)!=gap.get("missing_api_epg_references") or
        len(old)!=len(set(old)) or not isinstance(exact,dict) or
        not isinstance(exact.get("exact_xmltv_candidate_ids"),list) or
        not isinstance(name,dict) or not isinstance(name.get("candidate_identities"),list)):
        raise ValueError("Incomplete guide source baseline")
    exact_ids=set(exact["exact_xmltv_candidate_ids"])
    named_ids={item.get("channel_id") for item in name["candidate_identities"]}
    if (not exact_ids.issubset(set(old)) or not named_ids.issubset(set(old)) or
        len(exact_ids)!=exact.get("exact_xmltv_channel_id_candidates") or
        len(named_ids)!=name.get("display_name_review_identities") or
        len(set(old)-exact_ids-named_ids)!=name.get("still_without_display_name_lead")):
        raise ValueError("Inconsistent original 5-source gap")
    return set(old)-exact_ids-named_ids,len(old),len(exact_ids|named_ids)

def _valid_times(start,stop):
    if not isinstance(start,str) or not isinstance(stop,str):return False
    a,b=TIME.fullmatch(start),TIME.fullmatch(stop)
    if not a or not b:return False
    try:
        from datetime import timedelta,timezone
        def parse(m):
            tz=m.group(2);sign=1 if tz[0]=="+" else -1
            offset=timedelta(hours=int(tz[1:3]),minutes=int(tz[3:]))
            if offset>timedelta(hours=14):return None
            return datetime.strptime(m.group(1),"%Y%m%d%H%M%S").replace(
                tzinfo=timezone(sign*offset))
        left,right=parse(a),parse(b)
        return bool(left and right and left<right)
    except (ValueError,OverflowError):return False

def parse_guide(raw,wanted,unique_names):
    if not isinstance(raw,bytes) or len(raw)>110000000:
        raise ValueError("Invalid decompressed XMLTV bytes")
    candidates={}
    programme=Counter()
    timed=Counter()
    try:
        parser=ET.iterparse(io.BytesIO(raw),events=("start","end"))
        event,root=next(parser)
        if event!="start" or root.tag!="tv":
            raise ValueError("Not XMLTV")
        current=None
        display_names=set()
        for event,el in parser:
            if event=="start" and el.tag=="channel":
                current=el.get("id")
                display_names=set()
            elif event=="end" and el.tag=="display-name" and current:
                match=unique_names.get(key(el.text))
                if match in wanted:display_names.add(match)
                el.clear()
            elif event=="end" and el.tag=="channel":
                if current and current in wanted:
                    # Exact XMLTV ID takes precedence, but contradictory authoritative
                    # display-name evidence is held for review, never promoted.
                    if not display_names or display_names=={current}:
                        candidates[current]=(current,"EXACT_XMLTV_ID")
                elif current and len(display_names)==1:
                    cid=next(iter(display_names))
                    candidates[current]=(cid,"UNIQUE_REGISTRY_DISPLAY_NAME")
                current=None
                display_names=set()
                el.clear()
            elif event=="end" and el.tag=="programme":
                pid=el.get("channel")
                if isinstance(pid,str) and pid and len(pid)<=200:
                    programme[pid]+=1
                    if _valid_times(el.get("start"),el.get("stop")):timed[pid]+=1
                el.clear()
    except (ET.ParseError,StopIteration) as exc:
        raise ValueError("Malformed XMLTV") from exc
    matched=defaultdict(set)
    with_records=set()
    with_timed=set()
    for provider,(cid,match_kind) in candidates.items():
        h=sha(provider)
        matched[cid].add((h,match_kind))
        if programme[provider]:with_records.add(cid)
        if timed[provider]:with_timed.add(cid)
    return matched,with_records,with_timed

def review(api,gap,previous,channels,source_urls=SOURCES,fetcher=_fetch_xmltv):
    wanted,total,previous_hits=remaining_guide_ids(api,gap,previous)
    unique,ambiguous=registry_names(channels)
    if (not isinstance(source_urls,(list,tuple)) or len(source_urls)>6 or
        len(source_urls)!=len(set(source_urls)) or
        any(u not in SOURCES for u in source_urls)):
        raise ValueError("Unapproved extra EPG source")
    found=defaultdict(set)
    records=set()
    timed=set()
    sources=[]
    for url in source_urls:
        try:
            data=fetcher(url)
            matched,with_programmes,with_valid_times=parse_guide(data,wanted,unique)
            for cid,items in matched.items():
                for pid,method in items:found[cid].add((sha(url),pid,method))
            records.update(with_programmes)
            timed.update(with_valid_times)
            sources.append({"source_url_sha256":sha(url),
                "status":"XMLTV_PARSED_METADATA_ONLY",
                "matched_target_identities":len(matched),
                "with_programmes":len(with_programmes)})
        except (OSError,ValueError,TypeError,UnicodeError,EOFError) as exc:
            sources.append({"source_url_sha256":sha(url),
                "status":"XMLTV_UNVERIFIED_"+type(exc).__name__,
                "matched_target_identities":0,"with_programmes":0})
    rows=[{"channel_id":cid,
        "source_ids_sha256":sorted({a for a,_,_ in provenance}),
        "provider_xmltv_ids_sha256":sorted({b for _,b,_ in provenance}),
        "match_methods":sorted({c for _,_,c in provenance}),
        "programme_record_present":cid in records,
        "valid_time_range_present_not_schedule_accuracy":cid in timed}
        for cid,provenance in sorted(found.items())]
    return {"schema":1,"kind":"V2_TR_AZ_EXTRA_XMLTV_METADATA_GAP_AUDIT",
        "policy":"READ_ONLY_NO_SCHEDULE_OR_IBO_DEVICE_CLAIMS",
        "original_missing_epg_api_identities":total,
        "already_matched_from_original_sources":previous_hits,
        "previously_without_xmltv_candidate":len(wanted),
        "additional_guide_candidate_identities":len(rows),
        "additional_with_programme_records":len(records),
        "additional_with_well_formed_programme_times":len(timed),
        "still_missing_epg_identities":len(wanted)-len(rows),
        "new_candidate_identities":rows,
        "source_audit":sources,
        "all_new_sources_parsed":bool(sources) and all(
            s["status"]=="XMLTV_PARSED_METADATA_ONLY" for s in sources),
        "unambiguous_registry_names":len(unique),
        "ambiguous_registry_names_not_matched":ambiguous,
        "programme_schedule_accuracy_verified":False,
        "new_stream_av_verified":False,
        "spoken_language_verified":False,"sweden_access_verified":False,
        "ibo_device_verified":False,"protected_playlist_modified":False}

def run():
    paths=(API,GAP,PREV)
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size>15000000 for p in paths):
        raise SystemExit("Missing immutable original XMLTV evidence")
    api,gap,prior=[json.loads(p.read_text(encoding="utf-8")) for p in paths]
    result=review(api,gap,prior,fetch_api("channels"))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("TR_AZ_EXTRA_XMLTV_GAP_REVIEW",json.dumps({
        "before":result["previously_without_xmltv_candidate"],
        "new_metadata_matches":result["additional_guide_candidate_identities"],
        "with_programme_records":result["additional_with_programme_records"],
        "remaining":result["still_missing_epg_identities"],
        "sources_parsed":sum(x["status"]=="XMLTV_PARSED_METADATA_ONLY" for x in result["source_audit"])},sort_keys=True))

if __name__=="__main__":run()
