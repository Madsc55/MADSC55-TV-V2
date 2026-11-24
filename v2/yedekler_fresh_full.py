"""Owner-authorized fresh, read-only full YEDEKLER quality audit."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
from yedekler_quality_review import inspect, classify, get_quality_decoder
from yedekler_deep_review import PLAYLIST, sha, yedekler_records
from full_playlist_url_audit import write_json_atomic

SHARDS=16
def inventory(raw):
    rows=[]
    for pos, record in enumerate(yedekler_records(raw),1):
        urls=[u for u in record.splitlines()[1:] if u.startswith((b"http://",b"https://"))]
        rows.append({"position":pos,"record_sha256":sha(record),
                     "url_sha256":sha(urls[0]) if len(urls)==1 else None,
                     "url":urls[0].decode("utf-8") if len(urls)==1 else None})
    if len(rows)!=1562:
        raise ValueError("Unexpected YEDEKLER count")
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

def review(row,exe):
    out={k:v for k,v in row.items() if k!="url"}
    if row["url"] is None:
        return {**out,"classification":"INVALID_URL","first":[],"second":[]}
    first=inspect(row["url"],exe,variant_index=0,timeout=12)
    second=[] if classify(first,[])=="AV_20S_VERIFIED" else inspect(row["url"],exe,variant_index=2,timeout=12)
    return {**out,"classification":outcome(first,second),"first":first,"second":second}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",type=int)
    p.add_argument("--merge-dir",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    raw=PLAYLIST.read_bytes()
    rows=inventory(raw)
    keys=lambda rs:[(r["position"],r["record_sha256"],r["url_sha256"]) for r in rs]
    if a.merge_dir:
        parts=[json.loads(x.read_text()) for x in a.merge_dir.rglob("fresh-*.json")]
        if len(parts)!=SHARDS or {x["shard"] for x in parts}!=set(range(SHARDS)) or any(not x["complete"] or x["playlist_sha256"]!=sha(raw) for x in parts):
            raise ValueError("Missing or stale shards")
        result=sorted([r for part in parts for r in part["results"]],key=lambda r:r["position"])
        if keys(result)!=keys(rows):
            raise ValueError("Coverage mismatch")
        counts=dict(Counter(r["classification"] for r in result))
        statuses=dict(Counter(x["status"] for r in result for x in r["first"]+r["second"]))
        report={"complete":True,"total":len(result),"playlist_sha256":sha(raw),"counts":counts,"attempt_statuses":statuses,"results":result}
        write_json_atomic(a.output,report)
        print(json.dumps({"total":len(result),"counts":counts,"attempt_statuses":statuses}))
    else:
        if a.shard not in range(SHARDS):
            raise ValueError("Invalid shard")
        exe=get_quality_decoder()
        if not exe:
            raise RuntimeError("System FFmpeg required")
        subset=rows[a.shard::SHARDS]
        report={"shard":a.shard,"playlist_sha256":sha(raw),"complete":False,"results":[]}
        write_json_atomic(a.output,report)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(lambda r:review(r,exe),subset):
                report["results"].append(row)
                if len(report["results"])%10==0:
                    write_json_atomic(a.output,report)
        report["complete"]=keys(report["results"])==keys(subset)
        write_json_atomic(a.output,report)
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Playlist changed")
if __name__=="__main__":
    main()
