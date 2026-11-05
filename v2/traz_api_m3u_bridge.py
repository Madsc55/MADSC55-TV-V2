#!/usr/bin/env python3
"""Cross-match IPTV API leads against V2 M3U discovery by URL hash and exact TVG ID.

Hash-only overlaps with missing or different identity require review.
No plain URLs, AV proof or IBO device claims are created by this module.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
API=ROOT/"v2/reports/ci/traz-api-source-audit.json"
M3U=ROOT/"v2/reports/candidates.json"
SHA=re.compile(r"[0-9a-f]{64}\Z")
MAX_ROWS=120_000

def join(api,scan):
    if not isinstance(api,dict) or api.get("schema")!=1 or api.get("kind")!="TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS" or api.get("policy")!="READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES":
        raise ValueError("Invalid API source report")
    if api.get("all_streams_av_verified") is not False or api.get("protected_playlist_modified") is not False:
        raise ValueError("Unsafe API proof claim")
    if not isinstance(scan,dict) or scan.get("schema")!=1 or scan.get("playback_verified") is not False:
        raise ValueError("Invalid or falsely verified M3U scan")
    refs=api.get("stream_references")
    candidates=scan.get("candidates")
    if not isinstance(refs,list) or not isinstance(candidates,list) or len(refs)>MAX_ROWS or len(candidates)>MAX_ROWS:
        raise ValueError("Unbounded API/M3U report")
    if api.get("unique_channel_url_pairs")!=len(refs):
        raise ValueError("Invalid API pair count")
    api_by_hash=defaultdict(dict)
    seen_pairs=set()
    for row in refs:
        if not isinstance(row,dict) or "url" in row or row.get("av_verified") is not False:
            raise ValueError("Invalid API reference")
        digest,cid=row.get("url_sha256"),row.get("channel_id")
        if not isinstance(digest,str) or not SHA.fullmatch(digest) or not isinstance(cid,str) or not cid:
            raise ValueError("Invalid API identity hash")
        pair=(cid.casefold(),digest)
        if pair in seen_pairs: raise ValueError("Duplicate API identity pair")
        seen_pairs.add(pair)
        api_by_hash[digest][cid.casefold()]=row
    exact=[]
    review=[]
    seen_m3u=set()
    for row in candidates:
        if not isinstance(row,dict):
            raise ValueError("Invalid candidate")
        digest=row.get("url_sha256")
        if not isinstance(digest,str) or not SHA.fullmatch(digest):
            raise ValueError("Invalid M3U stream hash")
        if digest in seen_m3u:
            raise ValueError("Duplicate M3U stream hash")
        seen_m3u.add(digest)
        providers=api_by_hash.get(digest)
        if not providers: continue
        tvg=str(row.get("tvg_id") or "").strip()
        key=tvg.casefold()
        if key in providers:
            reference=providers[key]
            exact.append({
                "url_sha256":digest,"exact_channel_id":reference["channel_id"],
                "source_ids":row.get("source_ids") if isinstance(row.get("source_ids"),list) else [],
                "epg_guide_reference":reference.get("epg_guide_reference") is True,
                "country_metadata":reference.get("country_metadata"),
                "feed_language_metadata":reference.get("feed_language_metadata") or [],
                "custom_headers_needed":reference.get("custom_headers_needed") is True,
                "geo_label_only":reference.get("geo_label_only") is True,
                "identity_match_only":True,"av_verified":False,
                "spoken_language_verified":False,"ibo_device_verified":False})
        else:
            review.append({"url_sha256":digest,
                           "candidate_tvg_id":tvg[:150],
                           "possible_api_channel_ids":sorted(p["channel_id"] for p in providers.values()),
                           "status":"URL_HASH_OVERLAP_NOT_EXACT_IDENTITY"})
    mapped={r["url_sha256"] for r in exact}
    report={
        "schema":1,"kind":"V2_IPTV_API_TO_M3U_EXACT_IDENTITY_HASH_CROSSWALK",
        "policy":"READ_ONLY_EXACT_ID_AND_URL_HASH_NOT_AV",
        "api_url_hashes":len(api_by_hash),
        "api_channel_url_pairs":len(seen_pairs),
        "m3u_candidates":len(candidates),
        "m3u_url_hashes_present_in_api":len(api_by_hash.keys()&seen_m3u),
        "exact_channel_and_url_hash_matches":len(exact),
        "exact_matched_distinct_stream_hashes":len(mapped),
        "url_hash_overlaps_without_exact_channel_id":len(review),
        "api_url_hashes_not_in_m3u":len(api_by_hash.keys()-seen_m3u),
        "epg_matched_exact_streams":sum(r["epg_guide_reference"] for r in exact),
        "m3u_entries_not_in_api":len(seen_m3u-api_by_hash.keys()),
        "source_report_status":"EXACT_MATCHES_AND_MANUAL_REVIEW_ONLY",
        "exact_matches":exact,
        "identity_review":review,
        "all_streams_av_verified":False,
        "spoken_language_verified":False,
        "ibo_device_verified":False,
        "main_playlist_modified":False}
    return report

def load_and_join(api_path=API,m3u_path=M3U):
    p=Path(api_path)
    m=Path(m3u_path)
    for path in (p,m):
        if path.is_symlink() or not path.is_file() or path.stat().st_size>80_000_000:
            raise ValueError("Missing or oversized crosswalk report")
    return join(json.loads(p.read_text(encoding="utf-8")),
                json.loads(m.read_text(encoding="utf-8")))

if __name__=="__main__":
    print(json.dumps(load_and_join(),ensure_ascii=False,sort_keys=True))
