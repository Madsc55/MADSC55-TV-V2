#!/usr/bin/env python3
"""Bounded read-only TR/AZ missing-stream and XMLTV guide candidate crosswalk.

Exact tvg-id+URL SHA from the M3U discovery is NOT FFmpeg AV proof. XMLTV
metadata and programme records are NOT proof of correct schedule or playback.
This module never exports plaintext stream URLs or edits protected playlists.
"""
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import io
import ipaddress
import json
from pathlib import Path
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
API=ROOT/"v2/reports/ci/traz-api-source-audit.json"
M3U=ROOT/"v2/reports/candidates.json"
EPG_CONFIG=ROOT/"v2/epg_sources.json"
OUT=ROOT/"v2/reports/ci/traz-missing-stream-epg-crosswalk.json"
HEX=re.compile(r"[0-9a-f]{64}\Z")
MAX_CANDIDATES=150000

# IPTV-org may emit channel IDs as Channel.tr@SD or Channel.tr@HD: @...
# is a stream/feed rendition, never a separate broadcaster. Only its own
# approved M3U source IDs can supply this exact metadata hint.
FEED_VARIANTS=frozenset({"SD","HD","FHD","UHD","QHD","4K","8K"})
def canonical_tvg_id(tvg,source_ids):
    if not isinstance(tvg,str) or len(tvg)>200:
        return None
    original=tvg.strip()
    if not original or "://" in original or any(ord(c)<32 for c in original):
        return None
    raw,mark,variant=original.rpartition("@")
    known=isinstance(source_ids,(list,tuple,set)) and any(
        isinstance(s,str) and (s == "iptv-org" or s.startswith("iptv-org-"))
        for s in source_ids)
    if mark and variant.upper() in FEED_VARIANTS and known and "." in raw:
        return raw.casefold()
    return original.casefold()
MAX_COMPRESSED=20_000_000
MAX_DECOMPRESSED=110_000_000

def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def exact_ids(items,label,expected=None):
    if not isinstance(items,list) or len(items)>100000:
        raise ValueError("Invalid "+label+" identities")
    if not all(isinstance(x,str) and 0<len(x)<=200 and
               "://" not in x and not any(ord(c)<32 for c in x) for x in items):
        raise ValueError("Unsafe "+label+" identity")
    if len(set(x.casefold() for x in items))!=len(items):
        raise ValueError("Duplicate "+label+" identity")
    if expected is not None and len(items)!=expected:
        raise ValueError(label+" count mismatch")
    return {x.casefold():x for x in items}

def reconcile(api,m3u):
    if (not isinstance(api,dict) or api.get("schema")!=1 or
            api.get("kind")!="TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS" or
            api.get("policy")!="READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES" or
            api.get("protected_playlist_modified") is not False or
            api.get("all_streams_av_verified") is not False):
        raise ValueError("Invalid public API report")
    if (not isinstance(m3u,dict) or m3u.get("schema")!=1 or
            m3u.get("playback_verified") is not False or
            m3u.get("candidate_status")!="UNVERIFIED"):
        raise ValueError("Invalid public M3U discovery report")
    total=api.get("target_unique_channel_ids")
    missing=exact_ids(api.get("identities_without_stream_url_lead"),"missing_stream")
    epg=exact_ids(api.get("identities_missing_epg"),"missing_epg",
                  api.get("target_identities_without_epg_reference"))
    if not isinstance(total,int) or total<0 or len(missing)>total or len(epg)>total:
        raise ValueError("Inconsistent API target identities")
    refs=api.get("stream_references")
    candidates=m3u.get("candidates")
    if (not isinstance(refs,list) or len(refs)!=api.get("unique_channel_url_pairs")
            or not isinstance(candidates,list) or len(candidates)>MAX_CANDIDATES
            or len(candidates)!=m3u.get("total_unique_candidates")):
        raise ValueError("Incomplete API/M3U candidate inventory")
    api_by_hash=defaultdict(set)
    for item in refs:
        if (not isinstance(item,dict) or "url" in item or
                item.get("av_verified") is not False or
                not isinstance(item.get("channel_id"),str) or
                not isinstance(item.get("url_sha256"),str) or
                not HEX.fullmatch(item["url_sha256"])):
            raise ValueError("Invalid API hash-only identity")
        api_by_hash[item["url_sha256"]].add(item["channel_id"].casefold())
    possible=defaultdict(dict)
    hash_to_matched_ids=defaultdict(set)
    seen=set()
    for item in candidates:
        if not isinstance(item,dict) or "url" in item:
            raise ValueError("Plaintext URL in supposedly public M3U report")
        h=item.get("url_sha256")
        tvg=item.get("tvg_id")
        if not isinstance(h,str) or not HEX.fullmatch(h) or h in seen:
            raise ValueError("Bad or duplicate M3U URL identity hash")
        seen.add(h)
        provenance=item.get("source_ids")
        if not isinstance(provenance,list): provenance=[]
        cid=missing.get(canonical_tvg_id(tvg,provenance))
        if cid is None: continue
        # Only stable source identifiers; strip uncontrolled URL-like metadata.
        refs_safe=sorted(set(x[:96] for x in provenance
            if isinstance(x,str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,96}",x)
            and "://" not in x))[:12]
        previously_other=bool(api_by_hash.get(h) and cid.casefold() not in api_by_hash[h])
        possible[cid][h]={
           "url_sha256":h,"source_ids":refs_safe,
           "also_used_by_different_api_identity":previously_other,
           "av_verified":False,"source_metadata_only":True}
        hash_to_matched_ids[h].add(cid)
    matches=[]
    manual=[]
    for cid,rows in sorted(possible.items()):
        unique=[]
        for h,record in sorted(rows.items()):
            if len(hash_to_matched_ids[h])>1 or record["also_used_by_different_api_identity"]:
                manual.append({"channel_id":cid,"url_sha256":h,
                    "status":"SHARED_HASH_OR_DIFFERENT_BROADCASTER_ID_REVIEW",
                    "playback_verified":False})
            else:
                unique.append(record)
        matches.append({"channel_id":cid,
           "candidate_m3u_url_hashes":unique,
           "candidate_count":len(unique),
           "manual_identity_review_count":len(rows)-len(unique),
           "playback_verified":False})
    matched_ids={x["channel_id"] for x in matches if x["candidate_count"]}
    return {
      "schema":1,"kind":"V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE",
      "policy":"READ_ONLY_PUBLIC_HASH_ONLY_NO_AUTO_IBO_PROMOTION",
      "api_target_identities":total,"missing_api_stream_identities":len(missing),
      "missing_api_epg_references":len(epg),
      "source_m3u_candidates":len(candidates),
      "source_scan_coverage":m3u.get("coverage_status","UNKNOWN"),
      "source_scan_complete":m3u.get("source_fetch_complete") is True,
      "exact_missing_stream_identities_with_other_m3u_leads":len(matched_ids),
      "exact_missing_stream_candidate_hashes":sum(x["candidate_count"] for x in matches),
      "still_without_exact_source_metadata":len(missing)-len(matched_ids),
      "identity_collisions_for_manual_review":manual,
      "candidate_identities":matches,
      "still_missing_api_guide_identities":sorted(epg.values()),
      "epg_xmltv":None,
      "new_video_audio_verified":0,"spoken_language_verified":False,
      "sweden_access_verified":False,"ibo_device_verified":False,
      "protected_playlist_modified":False,
      "stream_leads_are_not_av_or_ibo_device_proof":True,
      "xmltv_id_is_not_schedule_accuracy_proof":True}

def _host_is_public(host):
    if not host or host.lower() in ("localhost",) or host.lower().endswith((".local",".internal",".localhost")):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        pass
    try:
        addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(t[4][0]).is_global for t in addresses)
    except (OSError,ValueError):
        return False

def _source_check(url):
    if not isinstance(url,str):
        return False
    try:
        p=urlsplit(url)
        return (p.scheme=="https" and bool(p.hostname) and
                _host_is_public(p.hostname) and p.port in (None,443) and
                p.username is None and p.password is None and not p.fragment)
    except ValueError:
        return False

class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        original=urlsplit(req.full_url)
        target=urlsplit(newurl)
        if target.scheme!="https" or target.hostname!=original.hostname:
            raise ValueError("Cross-origin XMLTV redirect refused")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def _fetch_xmltv(url):
    if not _source_check(url):
        raise ValueError("Unsafe or unresolved EPG source")
    opener=urllib.request.build_opener(SameHostRedirect())
    req=urllib.request.Request(url,headers={"User-Agent":"MADSC55-TV-V2-XMLTV-GapAudit/1.0"})
    with opener.open(req,timeout=15) as response:
        raw=response.read(MAX_COMPRESSED+1)
    if len(raw)>MAX_COMPRESSED:
        raise ValueError("Compressed XMLTV source exceeds limit")
    if raw.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
            raw=compressed.read(MAX_DECOMPRESSED+1)
    if len(raw)>MAX_DECOMPRESSED:
        raise ValueError("XMLTV decompressed size exceeds limit")
    return raw

def inspect_xmltv(data,requested):
    if not isinstance(data,bytes):
        raise ValueError("Expected XMLTV bytes")
    channel_ids=set()
    duplicate_channel_ids=set()
    programmes=Counter()
    if len(data)>MAX_DECOMPRESSED:
        raise ValueError("Oversized XMLTV content")
    try:
        parser=ET.iterparse(io.BytesIO(data),events=("start","end"))
        event,root=next(parser)
        if event!="start" or root.tag!="tv":
            raise ValueError("Not XMLTV")
        for event,element in parser:
            if event!="end":continue
            if element.tag=="channel" and element.get("id") in requested:
                cid=element.get("id")
                if cid in channel_ids:
                    duplicate_channel_ids.add(cid)
                channel_ids.add(cid)
            if element.tag=="programme" and element.get("channel") in requested:
                programmes[element.get("channel")]+=1
            element.clear()
    except (ET.ParseError,StopIteration) as e:
        raise ValueError("Malformed XMLTV") from e
    if duplicate_channel_ids:
        raise ValueError("Duplicate XMLTV channel identity")
    return channel_ids,programmes

def inspect_epg_gap(epg_ids,source_urls,fetcher=_fetch_xmltv):
    wanted=set(epg_ids)
    inspected=[]
    matching=set()
    with_programme=set()
    channel_source_counts=Counter()
    seen_source_hashes=set()
    for url in source_urls:
        h=sha(url) if isinstance(url,str) else None
        if h is not None and h in seen_source_hashes:
            inspected.append({"epg_source_url_sha256":h,
                "status":"XMLTV_DUPLICATE_SOURCE_SKIPPED",
                "exact_missing_api_guide_ids":0,"matched_ids_with_programmes":0})
            continue
        try:
            raw=fetcher(url)
            channels,programmes=inspect_xmltv(raw,wanted)
            if h is not None:
                seen_source_hashes.add(h)
            status="XMLTV_PARSED"
            matching|=channels
            channel_source_counts.update(channels)
            with_programme|=(channels&set(programmes))
            inspected.append({"epg_source_url_sha256":h,"status":status,
                "exact_missing_api_guide_ids":len(channels),
                "matched_ids_with_programmes":len(channels&set(programmes))})
        except (OSError,ValueError,TypeError,EOFError,gzip.BadGzipFile,UnicodeError) as exc:
            inspected.append({"epg_source_url_sha256":h,
                "status":"XMLTV_UNVERIFIED_"+type(exc).__name__,
                "exact_missing_api_guide_ids":0,"matched_ids_with_programmes":0})
    return {
      "source_count":len(source_urls),
      "parsed_sources":sum(x["status"]=="XMLTV_PARSED" for x in inspected),
      "all_sources_parsed":bool(source_urls) and all(x["status"] in ("XMLTV_PARSED","XMLTV_DUPLICATE_SOURCE_SKIPPED") for x in inspected) and any(x["status"]=="XMLTV_PARSED" for x in inspected),
      "missing_api_guide_identities":len(wanted),
      "exact_xmltv_channel_id_candidates":len(matching),
      "exact_xmltv_ids_with_programme_records":len(with_programme),
      "remaining_without_xmltv_channel_id_candidate":len(wanted-matching),
      "exact_xmltv_candidate_ids":sorted(matching),
      "cross_source_xmltv_id_collisions":sorted(k for k,v in channel_source_counts.items() if v>1),
      "cross_source_xmltv_collision_count":sum(v>1 for v in channel_source_counts.values()),
      "cross_source_collision_requires_manual_review":any(v>1 for v in channel_source_counts.values()),
      "source_results":inspected,
      "schedules_correctly_verified":False,
      "stream_playback_verified":False,
      "protected_playlist_modified":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--without-live-xmltv",action="store_true")
    a=ap.parse_args()
    for p in (API,M3U):
        if p.is_symlink() or not p.is_file() or p.stat().st_size>85_000_000:
            raise SystemExit("Missing or unsafe immutable report")
    result=reconcile(json.loads(API.read_text(encoding="utf-8")),
                     json.loads(M3U.read_text(encoding="utf-8")))
    if not a.without_live_xmltv:
        conf=json.loads(EPG_CONFIG.read_text(encoding="utf-8"))
        sources=conf.get("sources")
        if not isinstance(sources,list) or not 0<len(sources)<=12:
            raise SystemExit("Invalid bounded XMLTV source inventory")
        result["epg_xmltv"]=inspect_epg_gap(
            result["still_missing_api_guide_identities"],sources)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("TR_AZ_GAP_RECONCILED",json.dumps({
       "api_streamless":result["missing_api_stream_identities"],
       "exact_other_m3u_leads":result["exact_missing_stream_identities_with_other_m3u_leads"],
       "still_without_source":result["still_without_exact_source_metadata"],
       "missing_api_epg":result["missing_api_epg_references"],
       "xmltv":result["epg_xmltv"],"new_av":0},ensure_ascii=False,sort_keys=True)[:1100])

if __name__=="__main__":
    main()
