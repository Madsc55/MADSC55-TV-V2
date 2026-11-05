#!/usr/bin/env python3
"""Trusted IPTV-org @SD/@HD feed variants missing from old exact-ID crosswalk.

Fetch four bounded official M3U sources; match ONLY base IPTV-org channel IDs
already present in original 309-source-gap inventory, excluding prior
exact-ID candidates. Names, feed suffixes and URLs are NOT playback proof.
No plaintext URLs in public artifacts. FFmpeg acceptance is separate.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from discover import ROOT, fetch, entries
from traz_api_source_batch import public_stream
from traz_gap_crosswalk import canonical_tvg_id

API=ROOT/"v2/reports/ci/traz-api-source-audit.json"
BASELINE=ROOT/"v2/reports/ci/traz-missing-stream-epg-crosswalk.json"
OUT=ROOT/"v2/reports/ci/traz-official-feed-variant-gap.json"
OFFICIAL={
    "iptv-org-tr-streams":"https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u",
    "iptv-org-az-streams":"https://raw.githubusercontent.com/iptv-org/iptv/master/streams/az.m3u",
    "iptv-org-tur-language":"https://iptv-org.github.io/iptv/languages/tur.m3u",
    "iptv-org-aze-language":"https://iptv-org.github.io/iptv/languages/aze.m3u",
}
SHA=re.compile(r"[0-9a-f]{64}\Z")
FEED=re.compile(r"^(.+)@(?:SD|HD|FHD|UHD|QHD|4K|8K)$",re.I)

def reconcile(api,old,source_rows,errors=None):
    if (not isinstance(api,dict) or api.get("schema")!=1 or
        api.get("kind")!="TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS" or
        api.get("policy")!="READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES" or
        api.get("protected_playlist_modified") is not False or
        api.get("all_streams_av_verified") is not False or
        not isinstance(old,dict) or old.get("schema")!=1 or
        old.get("kind")!="V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE" or
        old.get("protected_playlist_modified") is not False or
        not isinstance(source_rows,dict) or
        not set(source_rows).issubset(set(OFFICIAL))):
        raise ValueError("Untrusted official feed source evidence")
    missing=api.get("identities_without_stream_url_lead")
    prior=old.get("candidate_identities")
    if (not isinstance(missing,list) or len(set(missing))!=len(missing) or
        not isinstance(prior,list) or len(missing)!=old.get("missing_api_stream_identities")):
        raise ValueError("Incomplete exact source baseline")
    old_ids={r["channel_id"] for r in prior if r.get("candidate_count",0)>0}
    if (len(old_ids)!=old.get("exact_missing_stream_identities_with_other_m3u_leads")
        or not old_ids.issubset(set(missing))):
        raise ValueError("Tampered original exact-M3U candidate IDs")
    remaining={x.casefold():x for x in missing if x not in old_ids}
    by_hash=defaultdict(set)
    selected=defaultdict(dict)
    scanned=0
    for sid,rows in source_rows.items():
        if not isinstance(rows,list) or len(rows)>10000:
            raise ValueError("Unbounded source playlist")
        for row in rows:
            if not isinstance(row,dict) or "url" not in row:
                raise ValueError("Malformed M3U source entry")
            tvg=row.get("tvg_id")
            if not isinstance(tvg,str) or not FEED.fullmatch(tvg.strip()):
                continue
            cid=remaining.get(canonical_tvg_id(tvg,[sid]))
            if not cid:continue
            url=row.get("url")
            if not public_stream(url):continue
            scanned+=1
            h=hashlib.sha256(url.encode()).hexdigest()
            if not SHA.fullmatch(h):raise ValueError("Malformed stream hash")
            selected[cid].setdefault(h,set()).add(sid)
            by_hash[h].add(cid)
    collisions={h for h,ids in by_hash.items() if len(ids)>1}
    targets=[]
    for cid,hashes in sorted(selected.items()):
        records=[{"url_sha256":h,"source_ids":sorted(sources),
                  "av_verified":False,"source_metadata_only":True}
                 for h,sources in sorted(hashes.items()) if h not in collisions]
        if records:
            targets.append({"channel_id":cid,"candidate_m3u_url_hashes":records,
                            "candidate_count":len(records),"playback_verified":False})
    if errors is None:errors={}
    if not isinstance(errors,dict) or not set(errors).issubset(set(OFFICIAL)):
        raise ValueError("Unknown official source failure")
    for source in errors:
        if source in source_rows:
            raise ValueError("Official source both fetched and failed")
    return {"schema":1,"kind":"V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE",
            "policy":"READ_ONLY_PUBLIC_HASH_ONLY_NO_AUTO_IBO_PROMOTION",
            "missing_api_stream_identities":len(remaining),
            "original_missing_api_stream_identities":len(missing),
            "original_exact_source_matched_identities":len(old_ids),
            "trusted_official_source_count":len(OFFICIAL),
            "official_sources_fetched":len(source_rows),
            "source_errors":errors,
            "source_scan_complete":len(source_rows)==len(OFFICIAL) and not errors,
            "feed_variant_metadata_candidates_before_collision":scanned,
            "conflicting_stream_hashes_not_promoted":len(collisions),
            "exact_missing_stream_identities_with_other_m3u_leads":len(targets),
            "exact_missing_stream_candidate_hashes":sum(r["candidate_count"] for r in targets),
            "still_without_exact_feed_variant_source":len(remaining)-len(targets),
            "candidate_identities":targets,
            "new_video_audio_verified":0,"spoken_language_verified":False,
            "sweden_access_verified":False,"ibo_device_verified":False,
            "protected_playlist_modified":False,
            "old_historical_orphan_50_auto_recovered":False}

def run():
    for p in (API,BASELINE):
        if p.is_symlink() or not p.is_file() or p.stat().st_size>25000000:
            raise SystemExit("Missing immutable API/84-ID source history")
    api=json.loads(API.read_text(encoding="utf-8"))
    old=json.loads(BASELINE.read_text(encoding="utf-8"))
    seen={}
    failures={}
    for sid,url in OFFICIAL.items():
        try:
            raw=fetch(url)
            if not raw.lstrip().startswith("#EXTM3U"):
                raise ValueError("Not M3U")
            seen[sid]=list(entries(raw))
        except (OSError,ValueError,UnicodeError,TypeError) as exc:
            failures[sid]=type(exc).__name__
    report=reconcile(api,old,seen,failures)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("TR_AZ_OFFICIAL_FEED_VARIANT_LEADS",json.dumps({
        "original_no_source_ids":report["original_missing_api_stream_identities"],
        "previously_other_m3u_ids":report["original_exact_source_matched_identities"],
        "new_exact_feed_identity_leads":report["exact_missing_stream_identities_with_other_m3u_leads"],
        "new_exact_feed_url_hashes":report["exact_missing_stream_candidate_hashes"],
        "remaining_missing_feed_identity":report["still_without_exact_feed_variant_source"],
        "sources_fetched":report["official_sources_fetched"],
        "new_av":False},sort_keys=True))

if __name__=="__main__":run()
