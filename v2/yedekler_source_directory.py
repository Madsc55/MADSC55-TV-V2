"""Read-only exact-ID official broadcaster directory research for YEDEKLER."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
from yedekler_deep_review import PLAYLIST, ROOT, sha, yedekler_records
from yedekler_fresh_full import inventory
from yedekler_quality_review import safe_sample
from full_playlist_url_audit import write_json_atomic

EXPECTED_SHA="265f368758e75c5b18bc1b936a9792fef36528ba486288ddb35e4e7e23775ecf"
CATALOG="https://iptv-org.github.io/api/channels.json"
KEY=lambda r:(r["position"],r["record_sha256"],r["url_sha256"])

def lookup(record, by_id, by_name):
    head=record.splitlines()[0].decode("utf-8")
    match=re.search(r'tvg-id="([^"]*)"',head)
    ident=match.group(1) if match else ""
    name=head.rsplit(",",1)[-1].strip()
    name=re.sub(r"^(?:❌|🟠|🔵|🟢|🔴|🟡|🔒)\s*","",name).strip()
    if ident and len(by_id.get(ident,[]))==1:
        return "EXACT_CATALOG_ID",by_id[ident][0]
    candidates=by_name.get(name.casefold(),[])
    if len(candidates)==1:
        return "NAME_ONLY_UNVERIFIED",candidates[0]
    return "NO_UNAMBIGUOUS_MATCH",None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prior",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    raw=PLAYLIST.read_bytes()
    historical=subprocess.check_output(["git","show","a8f4546b16a85ed50aed777add3767003d6303d5:"+PLAYLIST.name],cwd=ROOT)
    prior=json.loads(a.prior.read_bytes())
    current=inventory(raw)
    if sha(historical)!=EXPECTED_SHA or prior.get("playlist_sha256")!=EXPECTED_SHA or prior.get("complete") is not True or prior.get("total")!=1562:
        raise ValueError("Invalid evidence snapshot")
    if list(map(KEY,current))!=list(map(KEY,inventory(historical))) or list(map(KEY,current))!=list(map(KEY,prior["results"])):
        raise ValueError("Scope mismatch")
    data,_=safe_sample(CATALOG,limit=24*1024*1024,timeout=12)
    catalog=json.loads(data)
    if not isinstance(catalog,list) or not catalog:
        raise ValueError("Invalid catalog")
    by_id,by_name=defaultdict(list),defaultdict(list)
    for item in catalog:
        if not isinstance(item,dict) or item.get("closed") or item.get("is_nsfw"):
            continue
        site=item.get("website") or ""
        try:
            parsed=urlsplit(site)
            if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
                continue
        except ValueError:
            continue
        # Directory evidence only; never request these untrusted sites here.
        safe={"catalog_id":item.get("id"),"catalog_name":item.get("name"),"country":item.get("country"),"website_host":parsed.hostname}
        by_id[item.get("id")].append(safe)
        by_name[str(item.get("name") or "").casefold()].append(safe)
    rows=[]
    for record,old in zip(yedekler_records(raw),prior["results"]):
        status,lead=lookup(record,by_id,by_name)
        rows.append({"position":old["position"],"record_sha256":old["record_sha256"],"url_sha256":old["url_sha256"],
                     "prior_classification":old["classification"],"source_research_required":old["official_source_research_required"],
                     "directory_match":status,"directory_lead":lead,"publisher_verified":False,"replacement_stream_verified":False})
    target=[r for r in rows if r["source_research_required"]]
    if len(rows)!=1562 or len(target)!=275 or PLAYLIST.read_bytes()!=raw:
        raise ValueError("Coverage mismatch")
    report={"complete":True,"total":len(rows),"target_total":len(target),"catalog_sha256":sha(data),
            "all_matches":dict(Counter(r["directory_match"] for r in rows)),
            "target_matches":dict(Counter(r["directory_match"] for r in target)),
            "results":rows}
    write_json_atomic(a.output,report)
    print(json.dumps({k:v for k,v in report.items() if k!="results"}))
if __name__=="__main__":
    main()
