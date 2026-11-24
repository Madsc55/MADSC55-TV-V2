#!/usr/bin/env python3
"""Extend existing safe YEDEKLER decoder with measured media duration and quality.
No playlist writes, no arbitrary network egress from FFmpeg, no access bypass.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import http.client
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.parse import urljoin
from shared_url_safe_probe import vetted_target, PinnedHTTP, PinnedHTTPS, SafeFetchError
from full_playlist_url_audit import write_json_atomic
from yedekler_deep_review import load_scope, CURRENT_SHA, REVIEW, PLAYLIST, parse_manifest, local_frame, sha, yedekler_records

SHARDS=8
MAX_BYTES=24*1024*1024
MEDIA_SECONDS=20

def get_quality_decoder():
    # Use the OS decoder, not the static imageio binary that can crash on MPEG-TS.
    return shutil.which("ffmpeg", path="/usr/bin:/bin")
def load_targets(prior, deep):
    raw, scope=load_scope(prior, allow_other_groups=True)
    doc=json.loads(deep.read_text())
    if doc.get("playlist_sha256")!=CURRENT_SHA or doc.get("complete") is not True or doc.get("total")!=1226:
        raise ValueError("Invalid second-stage evidence")
    results=doc["results"]
    keys=lambda rows:[(r["position"],r["url_sha256"],r["record_sha256"]) for r in rows]
    if keys(scope)!=keys(results):
        raise ValueError("Invalid prior coverage")
    counts=Counter(r["classification"] for r in results)
    if counts["AV_VERIFIED"]!=16 or counts["CONFIRMED_UNAVAILABLE"]!=1 or sum(counts[k] for k in REVIEW)!=1209:
        raise ValueError("Invalid prior counts")
    return raw,[{**r,"previous":p["classification"],"prior_outcomes":[x["status"] for x in p["first"]+p["second"]]}
                for r,p in zip(scope,results) if p["classification"] in REVIEW]

def safe_sample(url,limit=MAX_BYTES,*,root=False, connection_factory=None):
    """Existing public-IP pinning per hop, at most 2 redirects; no cookies/auth.
    HTTPS downgrade, private targets, unsupported ports, encodings remain blocked.
    Retain partial bytes on read timeout instead of discarding playable samples.
    """
    current=url
    for hop in range(3):
        scheme,host,port,ip,path=vetted_target(current)
        factory=connection_factory or (PinnedHTTPS if scheme=="https" else PinnedHTTP)
        con=factory(host,port,ip,8)
        try:
            con.request("GET",path,headers={"Accept-Encoding":"identity",
                "User-Agent":"MADSC55-TV-V2-QualityAudit/1.0"})
            response=con.getresponse()
            if response.status in (301,302,303,307,308):
                dest=response.getheader("Location")
                if not dest or hop==2:
                    raise SafeFetchError("REDIRECT_LIMIT")
                nxt=urljoin(current,dest)
                next_scheme,*_=vetted_target(nxt)
                if scheme=="https" and next_scheme!="https":
                    raise SafeFetchError("HTTPS_DOWNGRADE_BLOCKED")
                current=nxt
                continue
            if response.status not in (200,206):
                if root and hop==0 and response.status in (404,410):
                    raise SafeFetchError("ORIGINAL_HTTP_"+str(response.status))
                raise SafeFetchError("HTTP_"+str(response.status))
            if response.getheader("Content-Encoding","identity").lower()!="identity":
                raise SafeFetchError("ENCODING_BLOCKED")
            chunks=[]
            size=0
            deadline=time.monotonic()+22
            while size<limit and time.monotonic()<deadline:
                try:
                    chunk=response.read1(min(65536,limit-size))
                except (OSError,TimeoutError,http.client.HTTPException):
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                size+=len(chunk)
            if not chunks:
                raise SafeFetchError("EMPTY_OR_TIMEOUT")
            return b"".join(chunks),current
        except SafeFetchError:
            raise
        except (OSError,ValueError,http.client.HTTPException):
            raise SafeFetchError("FETCH_FAILED") from None
        finally:
            con.close()
    raise SafeFetchError("REDIRECT_LIMIT")

def quality(data,fmt,exe):
    """Observe up to 20.5 seconds of local media, not a 20-second network promise."""
    cmd=[exe,"-nostdin","-hide_banner","-nostats","-loglevel","info","-threads","1",
         "-filter_threads","1","-protocol_whitelist","pipe","-f",fmt,"-i","pipe:0",
         "-map","0:v:0","-map","0:a:0","-t","20.5",
         "-vf","blackdetect=d=2:pix_th=0.10,freezedetect=n=-60dB:d=2,showinfo",
         "-af","silencedetect=n=-50dB:d=2,ashowinfo",
         "-threads","1","-f","null","pipe:1"]
    try:
        r=subprocess.run(cmd,input=data,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                         timeout=40,check=False)
        logs=r.stderr.decode("utf-8",errors="replace")
    except (OSError,subprocess.TimeoutExpired,ValueError):
        return {"status":"LOCAL_DECODE_TIMEOUT","video":False,"audio":False}
    def span(tag):
        times=[float(m.group(1)) for line in logs.splitlines() if tag in line
               for m in [re.search(r"\bpts_time:([-+]?\d+(?:\.\d+)?)",line)] if m]
        return round(max(times)-min(times),3) if len(times)>1 else 0.0
    vspan=span("Parsed_showinfo")
    aspan=span("Parsed_ashowinfo")
    v=vspan>0 or local_frame(data,fmt,"v",exe)
    a=aspan>0 or local_frame(data,fmt,"a",exe)
    full=r.returncode==0 and min(vspan,aspan)>=19.5
    flags=[label for pattern,label in [(r"black_start:","BLACK_INTERVAL"),(r"freeze_start:","FREEZE_INTERVAL"),
            (r"silence_start:","SILENCE_INTERVAL")] if re.search(pattern,logs)]
    return {"status":"MEDIA_20S" if full else "SHORT_OR_PARTIAL_MEDIA",
            "video":v,"audio":a,"video_seconds":vspan,"audio_seconds":aspan,
            "quality_flags":flags,"full_sample":full,"decoder_returncode":r.returncode}

def inspect(url,exe):
    attempts=[]
    calls=0
    budget=MAX_BYTES
    def get(target,limit=MAX_BYTES,root=False):
        nonlocal calls,budget
        calls+=1
        if calls>12 or budget<=0:
            raise SafeFetchError("REQUEST_BUDGET")
        data,final=safe_sample(target,min(limit,budget),root=root)
        budget-=len(data)
        return data,final
    def visit(data,target,depth=0):
        if depth>2:
            raise SafeFetchError("HLS_DEPTH_LIMIT")
        if not data.lstrip().startswith((b"#EXTM3U",b"\xef\xbb\xbf#EXTM3U")):
            fmt="mov" if len(data)>12 and data[4:8] in (b"ftyp",b"moov",b"styp") else "mpegts"
            attempts.append(quality(data,fmt,exe))
            return
        lines,uris=parse_manifest(data)
        if any(x.startswith("#EXT-X-STREAM-INF:") for x in lines):
            # One advertised variant per attempt; no alternate credentials or DRM.
            variant,final=get(urljoin(target,uris[0]),512000)
            visit(variant,final,depth+1)
            return
        if not any(x.startswith("#EXTINF:") for x in lines):
            raise SafeFetchError("UNKNOWN_HLS_FORMAT")
        maps=[x for x in lines if x.startswith("#EXT-X-MAP:")]
        init=b""
        if maps:
            if len(set(maps))!=1 or "BYTERANGE=" in maps[0]:
                raise SafeFetchError("FMP4_MAP_UNSUPPORTED")
            m=re.search(r'URI="([^"]+)"',maps[0])
            if not m:
                raise SafeFetchError("FMP4_MAP_UNSUPPORTED")
            init,_=get(urljoin(target,m.group(1)),512000)
        segments=[]
        for u in uris[-5:]:
            if budget<65536:
                break
            try:
                part,_=get(urljoin(target,u),6*1024*1024)
                segments.append(part)
            except SafeFetchError as e:
                attempts.append({"status":str(e),"video":False,"audio":False})
                break
        if segments:
            attempts.append(quality(init+b"".join(segments),"mov" if init else "mpegts",exe))
    try:
        data,final=get(url,root=True)
        visit(data,final)
    except SafeFetchError as e:
        attempts.append({"status":str(e),"video":False,"audio":False})
    except Exception:
        attempts.append({"status":"UNEXPECTED_ERROR","video":False,"audio":False})
    return attempts

def classify(first,second,radio=False):
    all_rows=first+second
    if any(x.get("full_sample") and not x.get("quality_flags") for x in all_rows):
        return "AV_20S_VERIFIED"
    if any(x.get("full_sample") and x.get("quality_flags") for x in all_rows):
        return "AV_20S_QUALITY_REVIEW"
    if any(x["video"] and x["audio"] for x in all_rows):
        return "AV_SHORT_VERIFIED"
    if radio:
        return "RADIO_OR_NON_TV_REVIEW"
    if len(first)==len(second)==1 and all(x["status"] in ("ORIGINAL_HTTP_404","ORIGINAL_HTTP_410") for x in all_rows):
        return "CONFIRMED_UNAVAILABLE"
    if any(x["video"] for x in all_rows) and not any(x["audio"] for x in all_rows):
        return "VIDEO_ONLY_REVIEW"
    if any(x["audio"] for x in all_rows) and not any(x["video"] for x in all_rows):
        return "AUDIO_ONLY_REVIEW"
    return "RECHECK_REQUIRED"

def review(row,exe):
    first=inspect(row["url"],exe)
    second=[] if any(x.get("full_sample") and not x.get("quality_flags") for x in first) else inspect(row["url"],exe)
    radio=row["previous"]=="RADIO_OR_NON_TV_REVIEW" or bool(re.search(r"\b(?:radio|radyo|fm)\b",row["name"],re.I))
    return {**{k:v for k,v in row.items() if k!="url"},"first":first,"second":second,
            "classification":classify(first,second,radio)}

def self_test():
    a={"status":"MEDIA_20S","video":True,"audio":True,"full_sample":True,"quality_flags":[]}
    b={**a,"quality_flags":["BLACK_INTERVAL"]}
    c={"status":"ORIGINAL_HTTP_404","video":False,"audio":False}
    assert classify([a],[])=="AV_20S_VERIFIED"
    assert classify([b],[])=="AV_20S_QUALITY_REVIEW"
    assert classify([c],[c])=="CONFIRMED_UNAVAILABLE"
    assert classify([c],[c],True)=="RADIO_OR_NON_TV_REVIEW"
    # A change outside YEDEKLER is safe; any change to its exact records is not.
    from unittest.mock import patch
    from yedekler_deep_review import verify_current_scope
    original=b'#EXTM3U\n#EXTINF:-1 group-title="YEDEKLER",A\nhttps://example.org/a\n#EXTINF:-1 group-title="OTHER",B\nhttps://example.org/b\n'
    unrelated=original.replace(b",B\n",b",C\n")
    altered=original.replace(b",A\n",b",C\n")
    with patch("yedekler_deep_review.CURRENT_SHA", sha(original)):
        verify_current_scope(original, unrelated, True)
        for candidate, allow in [(unrelated, False), (altered, True)]:
            try:
                verify_current_scope(original, candidate, allow)
            except ValueError:
                pass
            else:
                raise AssertionError("Scope verification accepted unexpected change")
    # Verify synthetic local media with actual FFmpeg, without network requests.
    exe=get_quality_decoder()
    if not exe:
        raise RuntimeError("System FFmpeg unavailable")
    print(subprocess.run([exe,"-version"],capture_output=True,text=True,check=True,timeout=10).stdout.splitlines()[0])
    if exe:
        for black in (False,True):
            src="color=c=black:s=64x64:r=10" if black else "testsrc2=s=64x64:r=10"
            sound="anullsrc=r=48000:cl=mono" if black else "sine=frequency=440:sample_rate=48000"
            data=subprocess.run([exe,"-nostdin","-v","error","-f","lavfi","-i",src,
                "-f","lavfi","-i",sound,"-t","21","-c:v","mpeg2video","-c:a","mp2",
                "-f","mpegts","pipe:1"],capture_output=True,timeout=30,check=True).stdout
            res=quality(data,"mpegts",exe)
            assert res["full_sample"],res
            if black:
                assert {"BLACK_INTERVAL","FREEZE_INTERVAL","SILENCE_INTERVAL"}.issubset(res["quality_flags"]),res
            else:
                assert not res["quality_flags"],res
            print("Synthetic quality fixture passed:", "black/frozen/silent" if black else "moving/audible", res)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prior",type=Path)
    p.add_argument("--deep",type=Path)
    p.add_argument("--shard",type=int)
    p.add_argument("--merge-dir",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        self_test()
        return
    raw,scope=load_targets(a.prior,a.deep)
    if a.merge_dir:
        parts=[json.loads(x.read_text()) for x in a.merge_dir.rglob("quality-*.json")]
        if len(parts)!=SHARDS or {x["shard"] for x in parts}!=set(range(SHARDS)) or any(not x["complete"] or x["playlist_sha256"]!=CURRENT_SHA or x.get("current_playlist_sha256")!=sha(raw) for x in parts):
            raise ValueError("Missing or stale shards")
        rows=sorted([r for x in parts for r in x["results"]],key=lambda r:r["position"])
        keys=lambda xs:[(r["position"],r["url_sha256"],r["record_sha256"]) for r in xs]
        if keys(rows)!=keys(scope):
            raise ValueError("Coverage mismatch")
        counts=dict(Counter(x["classification"] for x in rows))
        statuses=dict(Counter(x["status"] for r in rows for x in r["first"]+r["second"]))
        report={"playlist_sha256":CURRENT_SHA,"current_playlist_sha256":sha(raw),"complete":True,"total":len(rows),"counts":counts,"attempt_statuses":statuses,"results":rows}
        write_json_atomic(a.output,report)
        print(json.dumps({"total":len(rows),"counts":counts,"attempt_statuses":statuses,
            "confirmed_unavailable_positions":[r["position"] for r in rows if r["classification"]=="CONFIRMED_UNAVAILABLE"]}))
    else:
        if a.shard not in range(SHARDS):
            raise ValueError("Invalid shard")
        exe=get_quality_decoder()
        if not exe:
            raise ValueError("Decoder missing")
        target=[r for i,r in enumerate(scope) if i%SHARDS==a.shard]
        report={"playlist_sha256":CURRENT_SHA,"current_playlist_sha256":sha(raw),"shard":a.shard,"complete":False,"results":[]}
        write_json_atomic(a.output,report)
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs=[pool.submit(review,r,exe) for r in target]
            for f in as_completed(jobs):
                report["results"].append(f.result())
                if len(report["results"])%10==0:
                    write_json_atomic(a.output,report)
        report["results"].sort(key=lambda r:r["position"])
        report["complete"]=len(report["results"])==len(target)
        write_json_atomic(a.output,report)
        print(json.dumps({"shard":a.shard,"count":len(target),"counts":dict(Counter(r["classification"] for r in report["results"]))}))
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Playlist changed")
if __name__=="__main__":
    main()
