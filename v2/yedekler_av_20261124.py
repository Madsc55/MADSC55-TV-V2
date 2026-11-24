#!/usr/bin/env python3
"""Owner-requested, SHA-pinned read-only YEDEKLER video/audio scan."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
from full_playlist_av_decode import decoded_frame, get_local_ffmpeg
from shared_url_safe_probe import bounded_get, sample_transport_stream, SafeFetchError, program_table
from full_playlist_url_audit import write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
EXPECTED_SHA = "527f623b6e628d4712dda9caa8f789d8234c7be8de8972b7b014348a87451e9e"
SHARDS = 8
def digest(value):
    return hashlib.sha256(value).hexdigest()

def inventory(raw):
    if digest(raw) != EXPECTED_SHA:
        raise ValueError("Stale playlist")
    rows = []
    for r in re.split(rb"(?m)(?=^#EXTINF:)", raw)[1:]:
        lines = r.splitlines()
        if not re.search(rb'group-title="[^"]*YEDEKLER', lines[0]):
            continue
        urls = [x for x in lines[1:] if x.startswith((b"http://", b"https://"))]
        if len(urls) != 1:
            raise ValueError("Unexpected URL count")
        name = lines[0].rsplit(b",", 1)[-1].decode("utf-8").strip()
        rows.append({"position":len(rows)+1,"name":name,"url":urls[0].decode("utf-8"),
                     "url_sha256":digest(urls[0]),"record_sha256":digest(r)})
    if len(rows) != 1562:
        raise ValueError("Unexpected inventory")
    return rows

def attempt(url, executable):
    try:
        def fetch(target, limit):
            # Record a definitive HTTP status only for the original URL.
            return bounded_get(target, limit, timeout=6, report_http_status=(target == url))
        data = sample_transport_stream(url, fetch)
        programs = program_table(data)
        return {"status":"SAMPLED","video":decoded_frame(data,"v",executable),
                "audio":decoded_frame(data,"a",executable),
                "video_track":any(p["video_pids"] for p in programs),
                "audio_track":any(p["audio_pids"] for p in programs),
                "programs":len(programs)}
    except SafeFetchError as exc:
        return {"status":str(exc),"video":False,"audio":False}
    except Exception:
        return {"status":"UNEXPECTED_ERROR","video":False,"audio":False}

def classify(first, second=None, radio=False):
    tests = [first] if second is None else [first,second]
    if any(t["video"] and t["audio"] for t in tests):
        return "AV_VERIFIED"
    if radio:
        return "RADIO_OR_NON_TV_REVIEW"
    if second is not None and all(t["status"] in ("HTTP_404","HTTP_410") for t in tests):
        return "CONFIRMED_UNAVAILABLE"
    # A short TS sample with no decoded frame does not prove a broken channel.
    # Even repeated missing-track evidence can be legitimate for radio or
    # event/standby feeds; retain it as review rather than permanent failure.
    if second is not None and all(t["status"] == "SAMPLED" for t in tests):
        if all(t["video"] and not t["audio"] for t in tests):
            return "VIDEO_ONLY_REVIEW"
        if all(t["audio"] and not t["video"] for t in tests):
            return "AUDIO_ONLY_REVIEW"
    return "RECHECK_REQUIRED"

def check(row, executable):
    a = attempt(row["url"],executable)
    b = None if a["video"] and a["audio"] else attempt(row["url"],executable)
    radio = bool(re.search(r"\b(?:radio|radyo|fm)\b",row["name"],re.I))
    return {**{k:v for k,v in row.items() if k != "url"},
            "attempts":[a] if b is None else [a,b],
            "classification":classify(a,b,radio)}

def self_test():
    ok={"status":"SAMPLED","video":True,"audio":True}
    bad={"status":"HTTP_404","video":False,"audio":False}
    blocked={"status":"HTTP_UNAVAILABLE","video":False,"audio":False}
    partial={"status":"SAMPLED","video":True,"audio":False}
    assert classify(ok)=="AV_VERIFIED"
    assert classify(bad,bad)=="CONFIRMED_UNAVAILABLE"
    assert classify(bad,blocked)=="RECHECK_REQUIRED"
    assert classify(bad,bad,True)=="RADIO_OR_NON_TV_REVIEW"
    assert classify(partial,partial)=="VIDEO_ONLY_REVIEW"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shard",type=int)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--merge-dir",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    self_test()
    if args.self_test:
        return
    raw=PLAYLIST.read_bytes()
    rows=inventory(raw)
    if args.merge_dir:
        reports=[json.loads(p.read_text()) for p in args.merge_dir.rglob("yedekler-*.json")]
        if len(reports)!=SHARDS or {r["shard"] for r in reports}!=set(range(SHARDS)):
            raise ValueError("Missing or duplicate shards")
        results=[]
        for report in reports:
            if report["playlist_sha256"]!=EXPECTED_SHA or not report["complete"]:
                raise ValueError("Stale or incomplete report")
            results.extend(report["results"])
        results.sort(key=lambda r:r["position"])
        if [(r["position"],r["record_sha256"],r["url_sha256"]) for r in results]!=[(r["position"],r["record_sha256"],r["url_sha256"]) for r in rows]:
            raise ValueError("Coverage mismatch")
        counts=dict(Counter(r["classification"] for r in results))
        result={"playlist_sha256":EXPECTED_SHA,"complete":True,"total":len(rows),"counts":counts,"results":results}
        write_json_atomic(args.output,result)
        print(json.dumps({"total":len(rows),"counts":counts,"confirmed_unavailable_positions":[r["position"] for r in results if r["classification"]=="CONFIRMED_UNAVAILABLE"]},ensure_ascii=False))
    else:
        if args.shard not in range(SHARDS):
            raise ValueError("Invalid shard")
        executable=get_local_ffmpeg()
        if not executable:
            raise RuntimeError("FFmpeg unavailable")
        target=[r for r in rows if (r["position"]-1)%SHARDS==args.shard]
        # Decode each exact URL once per shard; all original record IDs retained.
        by_url={}
        for row in target:
            by_url.setdefault(row["url"],[]).append(row)
        report={"playlist_sha256":EXPECTED_SHA,"shard":args.shard,"complete":False,"results":[]}
        write_json_atomic(args.output,report)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(check,rs[0],executable):rs for rs in by_url.values()}
            for future in as_completed(futures):
                outcome=future.result()
                for row in futures[future]:
                    radio=bool(re.search(r"\b(?:radio|radyo|fm)\b",row["name"],re.I))
                    tests=outcome["attempts"]
                    report["results"].append({**{k:v for k,v in row.items() if k!="url"},"attempts":tests,
                        "classification":classify(tests[0],tests[1] if len(tests)>1 else None,radio)})
                if len(report["results"])%10==0:
                    write_json_atomic(args.output,report)
        report["results"].sort(key=lambda r:r["position"])
        report["complete"]=len(report["results"])==len(target)
        write_json_atomic(args.output,report)
        print(json.dumps({"shard":args.shard,"complete":report["complete"],"counts":dict(Counter(r["classification"] for r in report["results"]))}))
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Playlist mutated")
if __name__=="__main__":
    main()
