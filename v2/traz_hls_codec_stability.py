#!/usr/bin/env python3
"""Recheck prior FFmpeg-verified streams for short-term AV and HLS/codec clues.

Two snapshots are NOT 24-hour reliability, Swedish access, spoken language,
broadcaster authorization, or IBO device playback. Only URL SHA values appear
in anonymous reports. Production playlists are not accessed for writing.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from traz_api_source_batch import fetch_api,public_stream
from final_batch_acceptance import ROOT,LIVE,LIVE_BLOB,HISTORY,HISTORY_SHA,sha,gitblob,public_dns

PRIOR=ROOT/"v2/reports/ci/traz-api-av-acceptance.json"
OUT=ROOT/"v2/reports/ci/traz-hls-codec-shortterm-av.json"
SHA=re.compile(r"[0-9a-f]{64}\Z")

def prior_verified(document):
    if (document.get("schema")!=1 or document.get("kind")!="TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE"
        or document.get("policy")!="ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS"
        or document.get("protected_playlist_modified") is not False
        or document.get("ibo_device_verified") is not False
        or document.get("unprobed")!=0 or document.get("probed")!=document.get("unique_url_candidates")):
        raise ValueError("Invalid pinned real AV evidence")
    rows=document.get("streams")
    if not isinstance(rows,list) or len(rows)!=document["probed"] or len(rows)>500:
        raise ValueError("Invalid prior AV coverage")
    found={}
    all_seen=set()
    for row in rows:
        h=row.get("url_sha256")
        if not isinstance(h,str) or not SHA.fullmatch(h) or h in all_seen or "url" in row:
            raise ValueError("Bad URL hash or private address")
        all_seen.add(h)
        if row.get("decoded") is True:
            if (row.get("status")!="VIDEO_AUDIO_DECODED" or row.get("video") is not True
                or row.get("audio") is not True or not isinstance(row.get("channel_ids"),list)):
                raise ValueError("False prior AV claim")
            found[h]=tuple(sorted(row["channel_ids"]))
    if len(found)!=document.get("video_audio_decoded"):
        raise ValueError("Wrong prior AV total")
    return found

def current_exact_urls(streams,verified):
    if not isinstance(streams,list) or len(streams)>600000:
        raise ValueError("Unbounded live stream metadata")
    urls,identities={},{}
    for row in streams:
        if not isinstance(row,dict): continue
        u,cid=row.get("url"),row.get("channel")
        if not isinstance(cid,str) or not public_stream(u):continue
        h=sha(u)
        if h not in verified:continue
        if h in urls and urls[h]!=u:raise ValueError("SHA collision")
        urls[h]=u
        identities.setdefault(h,set()).add(cid)
    mismatched=sorted(h for h in urls if tuple(sorted(identities[h]))!=verified[h])
    accepted={h:u for h,u in urls.items() if h not in mismatched}
    return accepted,mismatched,sorted(set(verified)-set(urls))

def decode_details(stderr):
    video=audio=None
    width=height=None
    for line in str(stderr).splitlines():
        if "Stream #" not in line:continue
        if "Video:" in line and video is None:
            m=re.search(r"\bVideo:\s*([A-Za-z0-9_.+-]+)",line)
            if m:video=m.group(1)[:28]
            size=re.search(r"(?<!\d)([1-9]\d{2,4})x([1-9]\d{2,4})(?!\d)",line)
            if size and int(size.group(1))<=10000 and int(size.group(2))<=10000:
                width,height=int(size.group(1)),int(size.group(2))
        if "Audio:" in line and audio is None:
            m=re.search(r"\bAudio:\s*([A-Za-z0-9_.+-]+)",line)
            if m:audio=m.group(1)[:28]
    return {"video_codec":video,"audio_codec":audio,"width":width,"height":height}

def sample(url,runner=subprocess.run,resolver=public_dns):
    empty=decode_details("")
    if not public_stream(url) or not resolver(url):
        return {"status":"UNSAFE_OR_UNRESOLVED_HOST","decoded":False,**empty}
    try:
        args=["ffmpeg","-nostdin","-hide_banner","-loglevel","info",
              "-rw_timeout","6000000","-protocol_whitelist",
              "http,https,tcp,tls,crypto","-i",url,"-map","0:v:0",
              "-map","0:a:0","-t","1","-f","null","-"]
        p=runner(args,capture_output=True,text=True,stdin=subprocess.DEVNULL,timeout=28)
        return {"status":"VIDEO_AUDIO_DECODED" if p.returncode==0 else "CURRENT_AV_UNVERIFIED",
                "decoded":p.returncode==0,**decode_details(p.stderr)}
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):
        return {"status":"PROBE_ERROR_NOT_DEAD","decoded":False,**empty}

def hls_tags(text):
    if not isinstance(text,str) or not text.lstrip().startswith("#EXTM3U"):
        return {"status":"INVALID_HLS","variant_count":None,"max_declared_height":None}
    tags=re.findall(r"(?m)^#EXT-X-STREAM-INF:([^\r\n]+)",text)
    if tags:
        heights=[]
        for tag in tags:
            sizes=re.findall(r"(?:^|,)RESOLUTION=\d+x(\d+)(?:,|$)",tag)
            heights.extend(int(v) for v in sizes if 0<int(v)<=10000)
        return {"status":"HLS_MASTER_METADATA_NOT_AV","variant_count":len(tags),
                "max_declared_height":max(heights) if heights else None}
    return {"status":"HLS_MEDIA_PLAYLIST" if "#EXTINF" in text or "#EXT-X-TARGETDURATION" in text else "HLS_UNKNOWN",
            "variant_count":0,"max_declared_height":None}

def manifest(url,resolver=public_dns):
    p=urlsplit(url)
    if p.scheme!="https" or not p.path.lower().endswith(".m3u8") or not resolver(url):
        return {"status":"NOT_INSPECTED","variant_count":None,"max_declared_height":None}
    class LimitedRedirect(HTTPRedirectHandler):
        def redirect_request(self,request,fp,code,msg,headers,newurl):
            q=urlsplit(newurl)
            if q.scheme!="https" or q.hostname!=p.hostname:
                raise ValueError("Unapproved manifest redirect")
            return super().redirect_request(request,fp,code,msg,headers,newurl)
    try:
        opener=build_opener(LimitedRedirect())
        with opener.open(Request(url,headers={"User-Agent":"MADSC55-TV-V2-HLS-Check/1.0"}),timeout=8) as res:
            data=res.read(250001)
        if len(data)>250000:raise ValueError("Large HLS manifest")
        return hls_tags(data.decode("utf-8-sig",errors="replace"))
    except (OSError,ValueError,UnicodeError):
        return {"status":"UNAVAILABLE","variant_count":None,"max_declared_height":None}

def aggregate(prior,urls,bad,missing,first,second,hls):
    rows=[]
    for h in sorted(prior):
        a,b=first.get(h),second.get(h)
        rows.append({"url_sha256":h,"exact_channel_ids":list(prior[h]),
           "current_api":"PRESENT" if h in urls else "IDENTITY_REVIEW" if h in bad else "ABSENT",
           "av_round_1":a["status"] if a else "NOT_CHECKED",
           "av_round_2":b["status"] if b else "NOT_CHECKED",
           "both_samples_decode":bool(a and b and a["decoded"] and b["decoded"]),
           "video_codec_measured":a.get("video_codec") if a else None,
           "audio_codec_measured":a.get("audio_codec") if a else None,
           "width_measured":a.get("width") if a else None,
           "height_measured":a.get("height") if a else None,
           "manifest":hls.get(h,{"status":"NOT_CHECKED"}),
           "reliability_score":None,"long_term_uptime_verified":False,
           "spoken_language_verified":False,"sweden_access_verified":False,
           "ibo_device_verified":False})
    return {"schema":1,"kind":"TR_AZ_REAL_FFMPEG_HLS_CODEC_SHORT_TERM",
      "policy":"PUBLIC_SHA_ONLY_NO_PLAYLIST_PROMOTION",
      "prior_av_verified_streams":len(prior),
      "current_api_exact_urls":len(urls),
      "api_identity_mismatches":len(bad),"api_urls_no_longer_listed":len(missing),
      "both_short_av_samples_decoded":sum(x["both_samples_decode"] for x in rows),
      "codec_pairs_measured":sum(x["video_codec_measured"] is not None and x["audio_codec_measured"] is not None for x in rows),
      "hls_masters":sum(x["manifest"].get("status")=="HLS_MASTER_METADATA_NOT_AV" for x in rows),
      "short_interval_does_not_prove_24h_uptime":True,
      "spoken_language_verified":False,"sweden_access_verified":False,
      "ibo_device_verified":False,"protected_playlist_modified":False,"streams":rows}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=20)
    parser.add_argument("--interval",type=int,default=35)
    a=parser.parse_args()
    if not 1<=a.workers<=24 or not 20<=a.interval<=300:parser.error("Invalid bounds")
    if sha(HISTORY.read_bytes())!=HISTORY_SHA or gitblob(LIVE.read_bytes())!=LIVE_BLOB:
        raise SystemExit("Protected historical and IBO bytes changed")
    if not shutil.which("ffmpeg"):raise SystemExit("Real FFmpeg is unavailable")
    if PRIOR.is_symlink() or not PRIOR.is_file():raise SystemExit("Missing prior proof")
    prior=prior_verified(json.loads(PRIOR.read_text(encoding="utf-8")))
    urls,bad,missing=current_exact_urls(fetch_api("streams"),prior)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        first=dict(zip(urls,pool.map(sample,urls.values())))
    time.sleep(a.interval)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        second=dict(zip(urls,pool.map(sample,urls.values())))
    with ThreadPoolExecutor(max_workers=12) as pool:
        manifests=dict(zip(urls,pool.map(manifest,urls.values())))
    result=aggregate(prior,urls,bad,missing,first,second,manifests)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print("HLS_CODEC_MULTI_SAMPLE_REAL_AV",json.dumps({k:result[k] for k in
        ("prior_av_verified_streams","current_api_exact_urls","api_identity_mismatches",
         "api_urls_no_longer_listed","both_short_av_samples_decoded",
         "codec_pairs_measured","hls_masters")},sort_keys=True))

if __name__=="__main__":
    main()
