#!/usr/bin/env python3
"""One owner-authorized, read-only follow-up on exactly 1057 unresolved records."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

from yedekler_deep_review import ROOT, PLAYLIST, yedekler_records
from yedekler_quality_review import inspect, classify, get_quality_decoder
from full_playlist_url_audit import write_json_atomic

SOURCE_COMMIT = "0fad90b8bdc88e0efc35c16b99007275f742d55b"
SOURCE_SHA = "181f4e042142d0d04b82b473b760c1130b260e0c40b43d6d4746b47fc809a298"
REPORT_SHA = "33d4c7d1ea09aa1dd31a869b2e423e8a9d8f4701ae36625d562ac46d199df13d"
SHARDS = 8
AUTH = {"HTTP_401", "HTTP_403"}
BLOCK = {"INVALID_URL", "UNSUPPORTED_PORT", "PRIVATE_HOST", "PRIVATE_IP"}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def route(statuses):
    statuses = set(statuses)
    if not statuses:
        raise ValueError("Missing status evidence")
    if statuses <= AUTH:
        return "ACCESS_RESTRICTED"
    if statuses <= BLOCK:
        return "INVALID_OR_POLICY_BLOCKED"
    return "SAFE_RETRY"

def targets(path):
    report_bytes = path.read_bytes()
    if sha(report_bytes) != REPORT_SHA:
        raise ValueError("Prior report digest mismatch")
    report = json.loads(report_bytes)
    if report.get("complete") is not True or report.get("total") != 1209 or report.get("current_playlist_sha256") != SOURCE_SHA:
        raise ValueError("Wrong prior report")
    previous = subprocess.check_output(["git","show",SOURCE_COMMIT+":"+PLAYLIST.name],cwd=ROOT)
    if sha(previous) != SOURCE_SHA:
        raise ValueError("Wrong historical playlist")
    raw = PLAYLIST.read_bytes()
    old, current = yedekler_records(previous), yedekler_records(raw)
    if len(old) != 1562 or len(current) != len(old):
        raise ValueError("Unexpected scope size")
    rows = []
    for row in report["results"]:
        if row["classification"] != "RECHECK_REQUIRED":
            continue
        pos = row["position"]
        record = old[pos-1]
        if current[pos-1] != record or sha(record) != row["record_sha256"]:
            raise ValueError("Changed unresolved record")
        urls = [x for x in record.splitlines()[1:] if x.startswith((b"http://",b"https://"))]
        if len(urls)!=1 or sha(urls[0])!=row["url_sha256"]:
            raise ValueError("URL identity mismatch")
        statuses = sorted({x["status"] for x in row["first"]+row["second"]})
        rows.append({"position":pos,"name":row["name"],"url_sha256":row["url_sha256"],
                     "record_sha256":row["record_sha256"],"prior_statuses":statuses,
                     "route":route(statuses),"url":urls[0].decode("utf-8")})
    if len(rows)!=1057 or len({x["position"] for x in rows})!=1057:
        raise ValueError("Incomplete target coverage")
    if Counter(x["route"] for x in rows)!={"ACCESS_RESTRICTED":375,"INVALID_OR_POLICY_BLOCKED":213,"SAFE_RETRY":469}:
        raise ValueError("Unexpected route totals")
    return raw, rows

def followup_targets(rows, path):
    doc = json.loads(path.read_bytes())
    previous = subprocess.check_output(["git","show","60e0a90d4272dcab8706e797001c745de43dc99a:"+PLAYLIST.name],cwd=ROOT)
    if doc.get("complete") is not True or doc.get("total") != 1057 or doc.get("playlist_sha256") != sha(previous):
        raise ValueError("Invalid targeted report")
    keys = lambda r: (r["position"],r["record_sha256"],r["url_sha256"])
    prior = doc["results"]
    if len(prior)!=1057 or sorted(map(keys,prior))!=sorted(map(keys,rows)):
        raise ValueError("Prior coverage mismatch")
    if Counter(r["classification"] for r in prior)!={"ACCESS_RESTRICTED":375,"INVALID_OR_POLICY_BLOCKED":213,"RECHECK_REQUIRED":448,"AV_20S_VERIFIED":21}:
        raise ValueError("Unexpected prior outcomes")
    selected={keys(r) for r in prior if r["classification"]=="RECHECK_REQUIRED" and r["route"]=="SAFE_RETRY"}
    result=[r for r in rows if keys(r) in selected and r["route"]=="SAFE_RETRY"]
    if len(result)!=448:
        raise ValueError("Invalid retry scope")
    return result

def review(row, exe, followup=False):
    out = {k:v for k,v in row.items() if k!="url"}
    if row["route"] != "SAFE_RETRY":
        return {**out,"classification":row["route"],"attempts":[]}
    # A different advertised public HLS variant, longer bounded timeout;
    # no cookies, credentials, header spoofing, access bypass or private egress.
    first = inspect(row["url"],exe,variant_index=2 if followup else 1,timeout=12)
    second = []
    if (followup and classify(first,[])=="RECHECK_REQUIRED") or (len(first)==1 and first[0]["status"] in {"ORIGINAL_HTTP_404","ORIGINAL_HTTP_410"}):
        second = inspect(row["url"],exe,variant_index=1,timeout=12)
    return {**out,"classification":classify(first,second),"attempts":first+second}

def self_test():
    assert route(["HTTP_401","HTTP_403"])=="ACCESS_RESTRICTED"
    assert route(["INVALID_URL","UNSUPPORTED_PORT"])=="INVALID_OR_POLICY_BLOCKED"
    assert route(["DNS_UNVERIFIED"])=="SAFE_RETRY"
    assert route(["FETCH_FAILED","HTTP_403"])=="SAFE_RETRY"
    from unittest.mock import patch
    with patch(__name__+".inspect") as mock:
        for name in ("ACCESS_RESTRICTED","INVALID_OR_POLICY_BLOCKED"):
            assert review({"route":name,"url":"unused"},None)["classification"]==name
        mock.assert_not_called()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prior",type=Path)
    p.add_argument("--followup",type=Path)
    p.add_argument("--shard",type=int)
    p.add_argument("--merge-dir",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:
        self_test()
        return
    raw, rows=targets(args.prior)
    if args.followup:
        rows=followup_targets(rows,args.followup)
    keys=lambda rs:[(r["position"],r["record_sha256"],r["url_sha256"]) for r in rs]
    if args.merge_dir:
        parts=[json.loads(x.read_text()) for x in args.merge_dir.rglob("targeted-*.json")]
        if len(parts)!=SHARDS or {x["shard"] for x in parts}!=set(range(SHARDS)) or any(not x["complete"] or x["playlist_sha256"]!=sha(raw) for x in parts):
            raise ValueError("Missing or stale shards")
        results=sorted([r for x in parts for r in x["results"]],key=lambda r:r["position"])
        if keys(results)!=keys(sorted(rows,key=lambda r:r["position"])):
            raise ValueError("Coverage mismatch")
        counts=dict(Counter(r["classification"] for r in results))
        report={"complete":True,"playlist_sha256":sha(raw),"total":len(results),"counts":counts,"results":results}
        write_json_atomic(args.output,report)
        print(json.dumps({"total":len(results),"counts":counts}))
    else:
        if args.shard not in range(SHARDS):
            raise ValueError("Invalid shard")
        exe=get_quality_decoder()
        if not exe:
            raise RuntimeError("System FFmpeg required")
        subset=rows[args.shard::SHARDS]
        result={"shard":args.shard,"playlist_sha256":sha(raw),"complete":False,"results":[]}
        write_json_atomic(args.output,result)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(lambda r:review(r,exe,bool(args.followup)),subset):
                result["results"].append(row)
                if len(result["results"])%10==0:
                    write_json_atomic(args.output,result)
        result["complete"]=keys(result["results"])==keys(subset)
        write_json_atomic(args.output,result)
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Playlist changed")

if __name__=="__main__":
    main()
