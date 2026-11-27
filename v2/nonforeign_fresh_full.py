"""Owner-authorized fresh, read-only full YEDEKLER quality audit."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import time
from yedekler_quality_review import inspect, classify, get_quality_decoder
from yedekler_deep_review import PLAYLIST, sha, yedekler_records
from full_playlist_url_audit import write_json_atomic

from playlist_parts_manager import split_records, category

SHARDS=32
def turkic_hint(record):
    # Metadata-only hints, not a country/language verification or playback claim.
    head=record.splitlines()[0].decode("utf-8",errors="replace")
    name=head.rsplit(",",1)[-1].casefold()
    meta=" ".join(re.findall(r'(?:tvg-id|tvg-name|tvg-country|tvg-language)="([^"]*)"',head,re.I)).casefold()
    text=name+" "+meta
    patterns=[
        ("KKTC",r"\b(?:kktc|trnc|kıbrıs|kibris|kuzey kıbrıs|bayrak radyo televizyon)\b"),
        ("Azerbaycan",r"\b(?:azerbaycan|azerbaijan|azərbaycan|aztv|idman az|xezer|xəzər)\b|\.az\b"),
        ("Diğer Türkî",r"\b(?:türkmenistan|turkmenistan|özbekistan|uzbekistan|kazakistan|kazakhstan|kırgızistan|kyrgyzstan|tatarstan|uyghur)\b|\.(?:tm|uz|kz|kg)\b"),
        ("Türkiye/Türkçe",r"\b(?:türkiye|turkiye|turkey|türkçe|turkish|trt|türk|turk|kanal 7|show tv|star tv|atv|haber türk|habertürk)\b|\.tr\b|(?:^|[\s|])tr(?:$|[\s|])")
    ]
    return next((label for label,pattern in patterns if re.search(pattern,text)), "Belirsiz/diğer")

def inventory(raw, scope="nonforeign"):
    if scope not in ("nonforeign","yedekler","foreign"):
        raise ValueError("Unknown audit scope")
    rows=[]
    for pos, record in enumerate(split_records(raw)[1],1):
        group=category(record)
        is_foreign = bool(re.fullmatch(r"YABANCI ARŞİVİ(?: \(\d+\))?", group))
        if (scope == "foreign") != is_foreign:
            continue
        if scope=="yedekler" and not re.fullmatch(r"(?:🗂️?\s*)?YEDEKLER(?: \(\d+\))?",group):
            continue
        urls=[u for u in record.splitlines()[1:] if u.startswith((b"http://",b"https://"))]
        rows.append({"position":pos,"category":group,"record_sha256":sha(record),
                     "url_sha256":sha(urls[0]) if len(urls)==1 else None,
                     "url":urls[0].decode("utf-8") if len(urls)==1 else None,
                     **({"turkic_metadata_hint":turkic_hint(record)} if scope in ("yedekler","foreign") else {})})
    if not rows:
        raise ValueError("Empty audit scope")
    return rows

def outcome(first,second):
    result=classify(first,second)
    if result!="RECHECK_REQUIRED":
        return result
    statuses={x["status"] for x in first+second}
    if statuses and statuses<={"HTTP_401","HTTP_403"}:
        return "ACCESS_RESTRICTED"
    if statuses=={"INVALID_URL"}:
        return "INVALID_URL"
    if statuses and statuses<={"UNSUPPORTED_PORT","PRIVATE_HOST","PRIVATE_IP","HTTPS_DOWNGRADE_BLOCKED","REDIRECT_LIMIT","ENCODING_BLOCKED"}:
        return "SECURITY_POLICY_BLOCKED"
    return result

RETRY_GAP=120
STARTUP_TIMEOUT=180
LATE_START_SECONDS=15
REQUIRED_ROUNDS=3
HARD_FAILURE={"ORIGINAL_HTTP_404","ORIGINAL_HTTP_410"}

def red_eligible(rounds, historical_playable):
    # Only independently timed original-endpoint 404/410 are accepted.
    # Malformed streams, unsupported formats and decoder errors remain uncertain.
    if historical_playable or len(rounds)!=3:
        return False
    return all(b["started"]-a["finished"]>=RETRY_GAP for a,b in zip(rounds,rounds[1:])) and all(
        len(r["evidence"])==1 and r["evidence"][0]["status"] in HARD_FAILURE
        and not r["evidence"][0].get("video") and not r["evidence"][0].get("audio")
        for r in rounds)

def history_index(paths):
    playable=set()
    for path in paths:
        doc=json.loads(path.read_text())
        if doc.get("complete") is not True:
            raise ValueError("Incomplete history")
        for row in doc["results"]:
            if any(e.get("video") or e.get("audio") for e in row.get("first",[])+row.get("second",[])) or row.get("historical_playable"):
                if row.get("url_sha256"):
                    playable.add(row["url_sha256"])
    return playable

def review(row,exe,history):
    out={k:v for k,v in row.items() if k!="url"}
    historical=row["url_sha256"] in history
    rounds=[]
    for i in range(REQUIRED_ROUNDS):
        if i:
            time.sleep(RETRY_GAP)
        started=time.time()
        evidence=(inspect(row["url"],exe,variant_index=i,timeout=STARTUP_TIMEOUT,seconds=60,profile=i)
                  if row["url"] is not None else
                  [{"status":"INVALID_URL","video":False,"audio":False,"startup_seconds":None}])
        startup=next((e["startup_seconds"] for e in evidence if e.get("startup_seconds") is not None),None)
        healthy=any(e.get("full_sample") and not e.get("quality_flags") and
                    e.get("video") and e.get("audio") and e.get("startup_seconds") is not None
                    for e in evidence)
        rounds.append({"started":started,"finished":time.time(),"evidence":evidence,
                       "startup_seconds":startup,"healthy_60s":healthy})
    first=rounds[0]["evidence"] if rounds else []
    second=[e for r in rounds[1:] for e in r["evidence"]]
    classification=outcome(first,second) if rounds else "INVALID_URL"
    eligible=red_eligible(rounds,historical)
    if classification=="CONFIRMED_UNAVAILABLE" and not eligible:
        classification="RECHECK_REQUIRED"
    classification=classification.replace("AV_20S_","AV_60S_")
    passed=sum(r["healthy_60s"] for r in rounds)
    late=any(r["healthy_60s"] and r["startup_seconds"]>LATE_START_SECONDS for r in rounds)
    if classification=="AV_60S_VERIFIED":
        if passed==REQUIRED_ROUNDS:
            classification="AV_60S_LATE_START_VERIFIED" if late else "AV_60S_VERIFIED"
        else:
            classification="AV_60S_INCONSISTENT_REVIEW"
    return {**out,"classification":classification,"first":first,"second":second,
            "rounds":rounds,"startup_seconds":[r["startup_seconds"] for r in rounds],
            "healthy_rounds":passed,"required_rounds":REQUIRED_ROUNDS,
            "consistency_score":round(passed/REQUIRED_ROUNDS,4),
            "late_start_observed":late,"historical_playable":historical,"red_eligible":eligible}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",type=int)
    p.add_argument("--merge-dir",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--history",type=Path,action="append",default=[])
    p.add_argument("--scope",choices=["nonforeign","yedekler"],default="nonforeign")
    a=p.parse_args()
    raw=PLAYLIST.read_bytes()
    rows=inventory(raw,a.scope)
    keys=lambda rs:[(r["position"],r["category"],r["record_sha256"],r["url_sha256"]) for r in rs]
    if a.merge_dir:
        parts=[json.loads(x.read_text()) for x in a.merge_dir.rglob("fresh-*.json")]
        if len(parts)!=SHARDS or {x["shard"] for x in parts}!=set(range(SHARDS)) or any(not x["complete"] or x["playlist_sha256"]!=sha(raw) or x.get("scope","nonforeign")!=a.scope for x in parts):
            raise ValueError("Missing or stale shards")
        result=sorted([r for part in parts for r in part["results"]],key=lambda r:r["position"])
        if keys(result)!=keys(rows):
            raise ValueError("Coverage mismatch")
        if any(len(r["rounds"])!=REQUIRED_ROUNDS or r.get("required_rounds")!=REQUIRED_ROUNDS for r in result):
            raise ValueError("Incomplete independent rounds")
        counts=dict(Counter(r["classification"] for r in result))
        buckets={"AV_60S_VERIFIED":"green","AV_60S_LATE_START_VERIFIED":"green","AV_60S_INCONSISTENT_REVIEW":"orange","VIDEO_ONLY_REVIEW":"yellow","AUDIO_ONLY_REVIEW":"blue","AV_60S_QUALITY_REVIEW":"orange","AV_SHORT_VERIFIED":"orange"}
        by_category={}
        for r in result:
            r["red_eligible"]=red_eligible(r["rounds"],r["historical_playable"])
            r["bucket"]=buckets.get(r["classification"],"white")
            by_category.setdefault(r["category"],Counter())[r["bucket"]]+=1
        statuses=dict(Counter(x["status"] for r in result for x in r["first"]+r["second"]))
        if a.scope=="yedekler" and any(r.get("turkic_metadata_hint")!=source.get("turkic_metadata_hint") for r,source in zip(result,rows)):
            raise ValueError("Metadata hint mismatch")
        green_summary={c:dict(Counter(r.get("turkic_metadata_hint","Belirsiz/diğer") for r in result if r["classification"]==c)) for c in ("AV_60S_VERIFIED","AV_60S_LATE_START_VERIFIED")}
        report={"scope":a.scope,"green_metadata_candidates":green_summary,"complete":True,"total":len(result),"playlist_sha256":sha(raw),"counts":counts,"by_category":by_category,"attempt_statuses":statuses,"results":result}
        write_json_atomic(a.output,report)
        print(json.dumps({"scope":a.scope,"total":len(result),"counts":counts,"green_metadata_candidates":green_summary,"attempt_statuses":statuses},ensure_ascii=False))
    else:
        if a.shard not in range(SHARDS):
            raise ValueError("Invalid shard")
        exe=get_quality_decoder()
        if not exe:
            raise RuntimeError("System FFmpeg required")
        if not a.history:
            raise ValueError("Historical evidence required")
        history=history_index(a.history)
        subset=rows[a.shard::SHARDS]
        report={"scope":a.scope,"shard":a.shard,"playlist_sha256":sha(raw),"complete":False,"results":[]}
        write_json_atomic(a.output,report)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(lambda r:review(r,exe,history),subset):
                report["results"].append(row)
                if len(report["results"])%10==0:
                    write_json_atomic(a.output,report)
        report["complete"]=keys(report["results"])==keys(subset)
        write_json_atomic(a.output,report)
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Playlist changed")
if __name__=="__main__":
    main()
