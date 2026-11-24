#!/usr/bin/env python3
"""One-shot review of exactly 1226 unresolved YEDEKLER records. Never writes playlist."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin

from full_playlist_av_decode import get_local_ffmpeg, decoded_frame
from full_playlist_url_audit import write_json_atomic
from shared_url_safe_probe import bounded_get, SafeFetchError, program_table
from yedekler_av_20261124 import inventory, EXPECTED_SHA as OLD_SHA

ROOT=Path(__file__).resolve().parents[1]
PLAYLIST=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
CURRENT_SHA="cae52b3780c4c65c7727b6a240f33058187c0f39a62131f1adcb247882c1c642"
OLD_COMMIT="5e4dc27ce377f6c96a09946debcfc788c5493882"
SHARDS=8
LIMIT=3_000_000
REVIEW={"RECHECK_REQUIRED","VIDEO_ONLY_REVIEW","AUDIO_ONLY_REVIEW","RADIO_OR_NON_TV_REVIEW"}
def sha(b):
    return hashlib.sha256(b).hexdigest()

def yedekler_records(raw):
    """Exact ordered YEDEKLER record bytes, independent of other categories."""
    return [r for r in re.split(rb"(?m)(?=^#EXTINF:)", raw)[1:]
            if re.search(rb'group-title="[^"]*YEDEKLER', r.split(b"\n", 1)[0])]

def verify_current_scope(expected, raw, allow_other_groups=False):
    if sha(expected)!=CURRENT_SHA:
        raise ValueError("Reconstructed historical evidence hash mismatch")
    if expected!=raw and (not allow_other_groups or
                          yedekler_records(expected)!=yedekler_records(raw)):
        raise ValueError("Prior YEDEKLER scope differs from expected")

def load_scope(prior_path, *, allow_other_groups=False):
    original=subprocess.check_output(["git","show",OLD_COMMIT+":"+PLAYLIST.name],cwd=ROOT)
    old=inventory(original)
    raw=PLAYLIST.read_bytes()
    if sha(raw)!=CURRENT_SHA and not allow_other_groups:
        raise ValueError("Unexpected current playlist hash")
    prior=json.loads(prior_path.read_text())
    if prior.get("playlist_sha256")!=OLD_SHA or prior.get("complete") is not True or prior.get("total")!=1562:
        raise ValueError("Invalid initial evidence")
    results=prior["results"]
    if [(x["position"],x["record_sha256"],x["url_sha256"]) for x in results]!=[(x["position"],x["record_sha256"],x["url_sha256"]) for x in old]:
        raise ValueError("Prior evidence identity mismatch")
    counts=Counter(x["classification"] for x in results)
    if counts["AV_VERIFIED"]!=281 or counts["CONFIRMED_UNAVAILABLE"]!=55 or sum(counts[k] for k in REVIEW)!=1226:
        raise ValueError("Prior result count mismatch")
    # Confirm that the only difference is the already authorized 55 prefixes.
    selected={x["position"] for x in results if x["classification"]=="CONFIRMED_UNAVAILABLE"}
    records=re.split(rb"(?m)(?=^#EXTINF:)",original)
    pos=0
    for i,r in enumerate(records[1:],1):
        h,sep,tail=r.partition(b"\n")
        if not re.search(rb'group-title="[^"]*YEDEKLER',h):
            continue
        pos+=1
        if pos in selected:
            meta,comma,name=h.rpartition(b",")
            records[i]=meta+comma+"❌ ".encode()+name+sep+tail
    verify_current_scope(b"".join(records), raw, allow_other_groups)
    target=[]
    for row,prev in zip(old,results):
        if prev["classification"] in REVIEW:
            target.append({**row,"previous":prev["classification"],
                           "previous_statuses":[x["status"] for x in prev["attempts"]]})
    return raw,target

def local_frame(data,fmt,kind,exe):
    if fmt=="mpegts":
        return decoded_frame(data,kind,exe)
    cmd=[exe,"-nostdin","-hide_banner","-loglevel","error","-threads","1",
         "-filter_threads","1","-protocol_whitelist","pipe","-f","mov",
         "-i","pipe:0","-map","0:"+kind+":0","-frames:"+kind,"1","-f","framemd5","pipe:1"]
    try:
        r=subprocess.run(cmd,input=data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=12,check=False)
        return r.returncode==0 and any(len(x.split(b","))==6 and not x.startswith(b"#") for x in r.stdout.splitlines())
    except (OSError,subprocess.TimeoutExpired,ValueError):
        return False

def parse_manifest(data):
    if len(data)>256000:
        raise SafeFetchError("HLS_MANIFEST_TOO_LARGE")
    lines=[x.strip() for x in data.decode("utf-8-sig",errors="replace").splitlines() if x.strip()]
    if any(x.startswith("#EXT-X-KEY:") and "METHOD=NONE" not in x for x in lines):
        raise SafeFetchError("ENCRYPTED_HLS_UNSUPPORTED")
    if any(x.startswith("#EXT-X-BYTERANGE:") for x in lines):
        raise SafeFetchError("BYTERANGE_UNSUPPORTED")
    uri=[x for x in lines if not x.startswith("#")]
    if not uri:
        raise SafeFetchError("HLS_WITHOUT_SEGMENTS")
    return lines,uri

def inspect(url,exe):
    outcomes=[]
    requests=0
    def get(target,limit=LIMIT):
        nonlocal requests
        requests+=1
        if requests>9:
            raise SafeFetchError("REQUEST_BUDGET")
        # Existing DNS/public-IP pinning, no redirects, no credentials or private egress.
        return bounded_get(target,limit,timeout=10,report_http_status=(target==url))
    def decode(data,fmt):
        v=local_frame(data,fmt,"v",exe)
        a=local_frame(data,fmt,"a",exe)
        programs=program_table(data) if fmt=="mpegts" else []
        outcomes.append({"status":"SAMPLED_"+fmt.upper(),"video":v,"audio":a,
                         "video_track":any(p["video_pids"] for p in programs),
                         "audio_track":any(p["audio_pids"] for p in programs)})
        return v and a
    def visit(target,data,depth=0):
        if depth>2:
            raise SafeFetchError("HLS_DEPTH_LIMIT")
        if not data.lstrip().startswith((b"#EXTM3U",b"\xef\xbb\xbf#EXTM3U")):
            fmt="mov" if len(data)>12 and data[4:8] in (b"ftyp",b"moov",b"styp") else "mpegts"
            return decode(data,fmt)
        lines,uris=parse_manifest(data)
        if any(x.startswith("#EXT-X-STREAM-INF:") for x in lines):
            for u in list(dict.fromkeys([uris[0],uris[-1]])):
                try:
                    dest=urljoin(target,u)
                    if visit(dest,get(dest),depth+1):
                        return True
                except SafeFetchError as e:
                    outcomes.append({"status":str(e),"video":False,"audio":False})
            return False
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
            init=get(urljoin(target,m.group(1)),512000)
        for u in list(dict.fromkeys(uris[-2:][::-1])):
            try:
                segment=get(urljoin(target,u))
                if decode(init+segment,"mov" if init else "mpegts"):
                    return True
            except SafeFetchError as e:
                outcomes.append({"status":str(e),"video":False,"audio":False})
        return False
    try:
        visit(url,get(url))
    except SafeFetchError as e:
        outcomes.append({"status":str(e),"video":False,"audio":False})
    except Exception:
        outcomes.append({"status":"UNEXPECTED_ERROR","video":False,"audio":False})
    return outcomes

def review(row,exe):
    first=inspect(row["url"],exe)
    second=[] if any(x["video"] and x["audio"] for x in first) else inspect(row["url"],exe)
    outcomes=first+second
    if any(x["video"] and x["audio"] for x in outcomes):
        status="AV_VERIFIED"
    elif row["previous"]=="RADIO_OR_NON_TV_REVIEW" or re.search(r"\b(?:radio|radyo|fm)\b",row["name"],re.I):
        status="RADIO_OR_NON_TV_REVIEW"
    elif len(first)==len(second)==1 and all(x["status"] in ("HTTP_404","HTTP_410") for x in outcomes):
        status="CONFIRMED_UNAVAILABLE"
    elif any(x["video"] for x in outcomes) and not any(x["audio"] for x in outcomes):
        status="VIDEO_ONLY_REVIEW"
    elif any(x["audio"] for x in outcomes) and not any(x["video"] for x in outcomes):
        status="AUDIO_ONLY_REVIEW"
    else:
        status="RECHECK_REQUIRED"
    return {**{k:v for k,v in row.items() if k!="url"},"first":first,"second":second,"classification":status}

def self_test():
    lines,uris=parse_manifest(b"#EXTM3U\n#EXTINF:4,\na.ts\n#EXTINF:4,\nb.ts\n")
    assert uris==["a.ts","b.ts"]
    for manifest in [b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:4,\na.ts',b"#EXTM3U\n#EXT-X-BYTERANGE:100\n#EXTINF:4,\na.ts"]:
        try:
            parse_manifest(manifest)
        except SafeFetchError:
            continue
        raise AssertionError("Unsupported media accepted")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prior",type=Path)
    p.add_argument("--shard",type=int)
    p.add_argument("--merge-dir",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    self_test()
    if a.self_test:
        return
    raw,scope=load_scope(a.prior)
    if a.merge_dir:
        parts=[json.loads(p.read_text()) for p in a.merge_dir.rglob("deep-*.json")]
        if len(parts)!=SHARDS or {p["shard"] for p in parts}!=set(range(SHARDS)) or any(not p["complete"] or p["playlist_sha256"]!=CURRENT_SHA for p in parts):
            raise ValueError("Missing/stale shards")
        rows=sorted([r for p in parts for r in p["results"]],key=lambda x:x["position"])
        if [(x["position"],x["url_sha256"],x["record_sha256"]) for x in rows]!=[(x["position"],x["url_sha256"],x["record_sha256"]) for x in scope]:
            raise ValueError("Review coverage mismatch")
        counts=Counter(x["classification"] for x in rows)
        before=Counter(s for r in rows for s in r["previous_statuses"])
        after=Counter(x["status"] for r in rows for x in r["first"]+r["second"])
        report={"playlist_sha256":CURRENT_SHA,"complete":True,"total":len(rows),"counts":dict(counts),"previous_attempt_statuses":dict(before),"new_attempt_statuses":dict(after),"results":rows}
        write_json_atomic(a.output,report)
        print(json.dumps({"total":len(rows),"counts":dict(counts),"previous_attempt_statuses":dict(before),"new_attempt_statuses":dict(after),"confirmed_unavailable_positions":[r["position"] for r in rows if r["classification"]=="CONFIRMED_UNAVAILABLE"]},ensure_ascii=False))
    else:
        if a.shard not in range(SHARDS):
            raise ValueError("Invalid shard")
        exe=get_local_ffmpeg()
        if not exe:
            raise RuntimeError("Missing local decoder")
        rows=[x for i,x in enumerate(scope) if i%SHARDS==a.shard]
        report={"playlist_sha256":CURRENT_SHA,"shard":a.shard,"complete":False,"results":[]}
        write_json_atomic(a.output,report)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(review,r,exe) for r in rows]
            for f in as_completed(futures):
                report["results"].append(f.result())
                if len(report["results"])%10==0:
                    write_json_atomic(a.output,report)
        report["results"].sort(key=lambda x:x["position"])
        report["complete"]=len(report["results"])==len(rows)
        write_json_atomic(a.output,report)
        print(json.dumps({"shard":a.shard,"count":len(rows),"counts":dict(Counter(x["classification"] for x in report["results"]))}))
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Unexpected playlist mutation")
if __name__=="__main__":
    main()
