"""Reason-specific review of every YEDEKLER record; read-only and bounded."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import socket
import ssl
import subprocess
from urllib.parse import urlsplit
from yedekler_fresh_full import inventory, outcome
from yedekler_deep_review import PLAYLIST, ROOT, sha
from yedekler_quality_review import inspect, classify, get_quality_decoder
from shared_url_safe_probe import vetted_target, PinnedHTTP, PinnedHTTPS, SafeFetchError
from full_playlist_url_audit import write_json_atomic

SHARDS=16
EXPECTED={"RECHECK_REQUIRED":459,"AV_20S_VERIFIED":390,"INVALID_URL":108,
          "ACCESS_RESTRICTED":371,"AV_SHORT_VERIFIED":42,"CONFIRMED_UNAVAILABLE":56,
          "SECURITY_POLICY_BLOCKED":111,"AV_20S_QUALITY_REVIEW":22,"VIDEO_ONLY_REVIEW":3}
KEY=lambda r:(r["position"],r["record_sha256"],r["url_sha256"])

def url_reason(url):
    if not url:
        return "MISSING_OR_AMBIGUOUS_HTTP_URL"
    if len(url)>4096 or any(ord(c)<=32 or ord(c)==127 or c=="\\" for c in url) or any(x in url.lower() for x in ("%0a","%0d","%00")):
        return "INVALID_URL_CHARACTERS_OR_LENGTH"
    try:
        p=urlsplit(url)
        if p.username is not None or p.password is not None:
            return "EMBEDDED_CREDENTIALS_NOT_TESTED"
        if p.scheme not in ("http","https") or not p.hostname or p.fragment or "%" in p.netloc:
            return "INVALID_URL_STRUCTURE"
        _=p.port
    except (ValueError,UnicodeError):
        return "INVALID_URL_STRUCTURE"
    return "URL_STRUCTURE_OK"

def root_diagnostic(url):
    """No redirects, credentials, alternate ports, or response bodies."""
    try:
        scheme,host,port,ip,path=vetted_target(url)
    except SafeFetchError as e:
        return str(e)
    c=None
    try:
        c=(PinnedHTTPS if scheme=="https" else PinnedHTTP)(host,port,ip,12)
        c.request("GET",path,headers={"Accept-Encoding":"identity","User-Agent":"MADSC55-TV-V2-QualityAudit/1.0"})
        r=c.getresponse()
        if r.status in (200,206):
            return "ROOT_HTTP_OK" if r.getheader("Content-Encoding","identity").lower()=="identity" else "ENCODING_BLOCKED"
        if r.status in (301,302,303,307,308):
            return "ROOT_REDIRECT"
        return "HTTP_"+str(r.status)
    except ssl.SSLError:
        return "TLS_FAILED"
    except (socket.timeout,TimeoutError):
        return "CONNECTION_OR_RESPONSE_TIMEOUT"
    except ConnectionRefusedError:
        return "CONNECTION_REFUSED"
    except (OSError,http.client.HTTPException,ValueError):
        return "CONNECTION_OR_PROTOCOL_FAILED"
    finally:
        if c is not None:
            c.close()

def reason_set(attempts):
    return sorted({a["status"] for a in attempts})

def select_reason(prior,diag,new):
    statuses=set(prior)|set(new)|{diag}
    if "ENCRYPTED_HLS_UNSUPPORTED" in statuses:
        return "ENCRYPTED_HLS_OBSERVED"
    if diag=="HTTP_401":
        return "AUTHENTICATION_REQUIRED_OR_REJECTED"
    if diag=="HTTP_403":
        return "ACCESS_FORBIDDEN_CAUSE_UNKNOWN"
    if diag!="NOT_RETESTED":
        return diag
    return "PRIOR_EVIDENCE_ONLY"

def load_scope(raw,path):
    historical=subprocess.check_output(["git","show","bfa902093520d5f47f9368a40c8e81ff5cc3e15e:"+PLAYLIST.name],cwd=ROOT)
    doc=json.loads(path.read_bytes())
    old=inventory(historical)
    current=inventory(raw)
    prior=doc["results"]
    if doc.get("complete") is not True or doc.get("total")!=1562 or doc.get("playlist_sha256")!=sha(historical):
        raise ValueError("Invalid prior snapshot")
    if list(map(KEY,old))!=list(map(KEY,current)) or list(map(KEY,prior))!=list(map(KEY,current)):
        raise ValueError("Changed YEDEKLER scope")
    if Counter(x["classification"] for x in prior)!=EXPECTED:
        raise ValueError("Unexpected prior outcomes")
    return [(row,prev) for row,prev in zip(current,prior)]

def review(item,exe):
    row,prev=item
    category=prev["classification"]
    old=reason_set(prev["first"]+prev["second"])
    url=row["url"]
    shape=url_reason(url)
    diag="NOT_RETESTED"
    first,second=[],[]
    final=category
    if category=="INVALID_URL" or shape!="URL_STRUCTURE_OK":
        diag=shape if shape!="URL_STRUCTURE_OK" else "INVALID_URL_BY_POLICY"
    elif category=="SECURITY_POLICY_BLOCKED":
        # No network retry for known denied ports/targets. Preserve exact reasons.
        diag="POLICY_REVIEW_ONLY"
    elif category=="AV_20S_VERIFIED":
        diag="PRIOR_20S_AV_VERIFIED"
    else:
        diag=root_diagnostic(url)
        # Never retry authentication failures or unsafe endpoints with new credentials.
        if diag in {"ROOT_HTTP_OK","ROOT_REDIRECT"}:
            first=inspect(url,exe,variant_index=1,timeout=12)
            if classify(first,[])!="AV_20S_VERIFIED":
                second=inspect(url,exe,variant_index=3,timeout=12)
            final=outcome(first,second)
        elif diag in {"HTTP_401","HTTP_403"}:
            final="ACCESS_RESTRICTED"
        elif diag=="INVALID_URL":
            final="INVALID_URL"
        elif diag in {"UNSUPPORTED_PORT","PRIVATE_HOST","PRIVATE_IP","ENCODING_BLOCKED"}:
            final="SECURITY_POLICY_BLOCKED"
        elif diag in {"HTTP_404","HTTP_410"} and category=="CONFIRMED_UNAVAILABLE":
            final=category
        else:
            final="RECHECK_REQUIRED"
    new=reason_set(first+second)
    return {**{k:v for k,v in row.items() if k!="url"},"prior_classification":category,
            "classification":final,"prior_statuses":old,"diagnostic":diag,
            "reason":select_reason(old,diag,new),"url_structure":shape,
            "fresh_av_test":bool(first or second),"first":first,"second":second,
            "official_source_research_required":final in {"INVALID_URL","CONFIRMED_UNAVAILABLE","SECURITY_POLICY_BLOCKED"},
            "subscription_confirmed":False,"ibo_device_verified":False}

def self_test():
    assert url_reason("https://example.org/live")=="URL_STRUCTURE_OK"
    assert url_reason("https://user:pass@example.org/live")=="EMBEDDED_CREDENTIALS_NOT_TESTED"
    assert url_reason("https://example.org:bad/live")=="INVALID_URL_STRUCTURE"
    assert select_reason([],"HTTP_403",[])=="ACCESS_FORBIDDEN_CAUSE_UNKNOWN"
    assert select_reason(["ENCRYPTED_HLS_UNSUPPORTED"],"NOT_RETESTED",[])=="ENCRYPTED_HLS_OBSERVED"
    from unittest.mock import patch
    row={"position":1,"url":"https://example.org/live","url_sha256":"a","record_sha256":"b"}
    for cat in ("AV_20S_VERIFIED","SECURITY_POLICY_BLOCKED","INVALID_URL"):
        with patch(__name__+".root_diagnostic") as probe,patch(__name__+".inspect") as media:
            review((row,{"classification":cat,"first":[],"second":[]}),None)
            probe.assert_not_called()
            media.assert_not_called()
    with patch(__name__+".root_diagnostic",return_value="HTTP_401"),patch(__name__+".inspect") as media:
        result=review((row,{"classification":"RECHECK_REQUIRED","first":[],"second":[]}),None)
        assert result["classification"]=="ACCESS_RESTRICTED" and not result["subscription_confirmed"]
        media.assert_not_called()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prior",type=Path)
    p.add_argument("--shard",type=int)
    p.add_argument("--merge-dir",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        self_test()
        return
    raw=PLAYLIST.read_bytes()
    scope=load_scope(raw,a.prior)
    digest=sha(a.prior.read_bytes())
    if a.merge_dir:
        parts=[json.loads(x.read_text()) for x in a.merge_dir.rglob("reason-*.json")]
        if len(parts)!=SHARDS or {x["shard"] for x in parts}!=set(range(SHARDS)) or any(not x["complete"] or x["playlist_sha256"]!=sha(raw) or x["prior_sha256"]!=digest for x in parts):
            raise ValueError("Incomplete or stale shards")
        rows=sorted([r for part in parts for r in part["results"]],key=lambda r:r["position"])
        if list(map(KEY,rows))!=[KEY(r) for r,_ in scope]:
            raise ValueError("Coverage mismatch")
        report={"complete":True,"total":len(rows),"playlist_sha256":sha(raw),"prior_sha256":digest,
                "counts":dict(Counter(r["classification"] for r in rows)),
                "reasons":dict(Counter(r["reason"] for r in rows)),
                "fresh_av_tests":sum(r["fresh_av_test"] for r in rows),
                "source_research_required":sum(r["official_source_research_required"] for r in rows),"results":rows}
        write_json_atomic(a.output,report)
        print(json.dumps({k:v for k,v in report.items() if k!="results"}))
    else:
        if a.shard not in range(SHARDS):
            raise ValueError("Invalid shard")
        exe=get_quality_decoder()
        if not exe:
            raise RuntimeError("System FFmpeg required")
        subset=scope[a.shard::SHARDS]
        report={"shard":a.shard,"playlist_sha256":sha(raw),"prior_sha256":digest,"complete":False,"results":[]}
        write_json_atomic(a.output,report)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(lambda x:review(x,exe),subset):
                report["results"].append(row)
                if len(report["results"])%10==0:
                    write_json_atomic(a.output,report)
        report["complete"]=list(map(KEY,report["results"]))==[KEY(r) for r,_ in subset]
        write_json_atomic(a.output,report)
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Playlist changed")

if __name__=="__main__":
    main()
