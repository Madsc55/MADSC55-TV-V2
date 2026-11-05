#!/usr/bin/env python3
"""Read-only exact IPTV-org API joins for worldwide TR/AZ channel discovery.

These URL references are NOT decoded AV, spoken language, Swedish access,
reliable uptime or IBO device proof. Protected playlists are never written.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from webpage_source_discovery import public_hostname

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"v2/reports/ci/traz-api-source-audit.json"
PRIVATE=ROOT/"v2/reports/private-traz-api-candidates.json"
HOST="iptv-org.github.io"
KINDS=("channels","feeds","streams","guides")
MAX_BYTES=40_000_000
MAX_ROWS=120_000

def fetch_api(kind):
    if kind not in KINDS: raise ValueError("Unapproved API collection")
    url="https://"+HOST+"/api/"+kind+".json"
    class OnlyOfficialRedirect(HTTPRedirectHandler):
        def redirect_request(self,request,fp,code,msg,headers,newurl):
            p=urlsplit(newurl)
            if p.scheme!="https" or p.hostname!=HOST or p.path!="/api/"+kind+".json":
                raise ValueError("Unsafe API redirect")
            return super().redirect_request(request,fp,code,msg,headers,newurl)
    with build_opener(OnlyOfficialRedirect()).open(
            Request(url,headers={"User-Agent":"MADSC55-V2-ApiMetadata/1.0"}),
            timeout=35) as response:
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError("Oversized API response")
    data=json.loads(raw)
    if not isinstance(data,list) or len(data)>MAX_ROWS: raise ValueError("Invalid API list")
    return data

def public_stream(url):
    if not isinstance(url,str) or len(url)>4096: return False
    try:
        p=urlsplit(url)
        host=(p.hostname or "").lower()
        if re.fullmatch(r"[0-9.]+|0x[0-9a-f]+|0[0-7]+",host):
            return False
        return (p.scheme in ("http","https") and bool(host)
                and public_hostname(host) and p.username is None
                and p.password is None and not p.fragment
                and p.port in (None,80,443,8000,8080,8443)
                and host not in ("youtube.com","youtu.be","www.youtube.com")
                and not host.endswith((".googlevideo.com",".youtube-nocookie.com")))
    except ValueError:
        return False

def build(channels,feeds,streams,guides):
    for name,data in (("channels",channels),("feeds",feeds),
                      ("streams",streams),("guides",guides)):
        if not isinstance(data,list) or len(data)>MAX_ROWS:
            raise ValueError("Invalid "+name+" data")
    feed_languages={}
    for row in feeds:
        if isinstance(row,dict) and isinstance(row.get("channel"),str) and isinstance(row.get("languages"),list):
            feed_languages.setdefault(row["channel"],set()).update(
                lang for lang in row["languages"] if lang in ("tur","aze"))
    identity={}
    for row in channels:
        if not isinstance(row,dict): continue
        cid=row.get("id")
        if not isinstance(cid,str) or not cid or row.get("closed") or row.get("is_nsfw"): continue
        country=row.get("country")
        langs=feed_languages.get(cid,set())
        if country not in ("TR","AZ") and not langs: continue
        if cid in identity: raise ValueError("Duplicate exact channel ID")
        identity[cid]={"country":country,"languages":sorted(langs),
                       "aliases":len(row["alt_names"]) if isinstance(row.get("alt_names"),list) else 0}
    guide_ids={row["channel"] for row in guides if isinstance(row,dict) and isinstance(row.get("channel"),str)}
    public,private,seen=[],[],set()
    dropped=header_count=geo_count=0
    for row in streams:
        if not isinstance(row,dict) or not isinstance(row.get("channel"),str) or row["channel"] not in identity or not public_stream(row.get("url")):
            dropped+=1
            continue
        cid,url=row["channel"],row["url"]
        if (cid,url) in seen: continue
        seen.add((cid,url))
        digest=hashlib.sha256(url.encode("utf-8")).hexdigest()
        labels=row.get("labels") if isinstance(row.get("labels"),list) else []
        geo=any(isinstance(s,str) and "geo" in s.casefold() for s in labels)
        headers=bool(row.get("referrer") or row.get("user_agent"))
        geo_count+=int(geo)
        header_count+=int(headers)
        data=identity[cid]
        public.append({"channel_id":cid,"url_sha256":digest,
                       "country_metadata":data["country"],
                       "feed_language_metadata":data["languages"],
                       "alias_count":data["aliases"],
                       "epg_guide_reference":cid in guide_ids,
                       "declared_quality":str(row.get("quality") or "")[:30],
                       "geo_label_only":geo,"custom_headers_needed":headers,
                       "av_verified":False,"spoken_language_verified":False,
                       "sweden_access_verified":False,"ibo_device_verified":False})
        private.append({"channel_id":cid,"url":url,
                        "country_metadata":data["country"],
                        "feed_language_metadata":data["languages"],
                        "declared_quality":str(row.get("quality") or "")[:30],
                        "referrer":row.get("referrer"),
                        "user_agent":row.get("user_agent"),
                        "geo_label_only":geo})
    hashes={r["url_sha256"] for r in public}
    report={"schema":1,"kind":"TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
            "policy":"READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES",
            "api_collections":list(KINDS),
            "target_unique_channel_ids":len(identity),
            "country_tr_az_identities":sum(v["country"] in ("TR","AZ") for v in identity.values()),
            "worldwide_language_feed_identities":sum(v["country"] not in ("TR","AZ") for v in identity.values()),
            "epg_target_identities":len(set(identity)&guide_ids),
            "target_identities_without_epg_reference":len(set(identity)-guide_ids),
            "unique_channel_url_pairs":len(public),
            "unique_stream_url_hashes":len(hashes),
            "same_url_multiple_channel_id_pairs":len(public)-len(hashes),
            "excluded_unmatched_or_unsafe_stream_rows":dropped,
            "custom_header_candidates":header_count,"geoblock_label_candidates":geo_count,
            "all_streams_av_verified":False,"spoken_language_verified":False,
            "sweden_access_verified":False,"ibo_device_verified":False,
            "protected_playlist_modified":False,"stream_references":public}
    return report,private

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--public-only",action="store_true")
    opts=arg.parse_args()
    data={kind:fetch_api(kind) for kind in KINDS}
    report,private=build(*(data[kind] for kind in KINDS))
    PUBLIC.parent.mkdir(parents=True,exist_ok=True)
    PUBLIC.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    if not opts.public_only:
        PRIVATE.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(PRIVATE,os.O_CREAT|os.O_WRONLY|os.O_TRUNC,0o600)
        with os.fdopen(descriptor,"w",encoding="utf-8") as out:
            json.dump({"schema":1,"kind":"PRIVATE_API_STREAM_LEADS",
                       "av_verified":False,"items":private},out,ensure_ascii=False)
            out.write("\n")
    print(json.dumps({"channel_identities":report["target_unique_channel_ids"],
                      "stream_url_leads":report["unique_channel_url_pairs"],
                      "epg_identities":report["epg_target_identities"],
                      "real_av_verified":False},sort_keys=True))

if __name__=="__main__":
    main()
