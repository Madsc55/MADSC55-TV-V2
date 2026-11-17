#!/usr/bin/env python3
"""Bounded, explicit opt-in batch OCR/subtitle sampling of a local snapshot.

Never writes playlists or input files; output contains hashes and review hints only.
"""
import argparse
import hashlib
import json
from pathlib import Path
try:
    from .backup_text_sampler import sample, valid_url
except ImportError:
    from backup_text_sampler import sample, valid_url

def run(snapshot_path, output_path, limit=8, seconds=8, allow_network=False):
    if allow_network is not True:
        raise ValueError("Network sampling requires explicit opt-in")
    if not isinstance(limit,int) or not 1 <= limit <= 16:
        raise ValueError("limit must be 1..16")
    if not isinstance(seconds,int) or not 2 <= seconds <= 15:
        raise ValueError("seconds must be 2..15")
    if snapshot_path.resolve() == output_path.resolve() or output_path.exists():
        raise ValueError("Refusing to overwrite source or existing report")
    data=json.loads(snapshot_path.read_text(encoding="utf-8"))
    candidates=data.get("candidates") if isinstance(data,dict) else None
    if not isinstance(candidates,list):
        raise ValueError("Expected candidates list")
    seen=set()
    results=[]
    for item in candidates:
        if not isinstance(item,dict):
            raise ValueError("Invalid candidate")
        url=item.get("url")
        if not valid_url(url):
            continue
        digest=hashlib.sha256(url.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        try:
            result=sample(url,seconds)
            if not isinstance(result,dict):
                raise ValueError("Invalid sampler result")
        except (ValueError, RuntimeError, OSError) as exc:
            result={"status":"SAMPLE_ERROR","error_type":type(exc).__name__,
                    "language_evidence_verified":False,"review_approved":False}
        # Never let an unexpected sampler field leak raw text or stream URLs.
        safe={k:result[k] for k in ("status","observation_count","ocr_hint",
              "subtitle_hint","language_evidence_verified","review_approved","error_type")
              if k in result}
        safe["language_evidence_verified"]=False
        safe["review_approved"]=False
        results.append({"url_sha256":digest,**safe})
        if len(results)>=limit:
            break
    # sampled is a historical count of selected candidates, NOT proof that
    # FFmpeg ran, media decoded or language was verified.
    report={"policy":"READ_ONLY_HINTS_ONLY_NO_AUTO_APPROVAL",
            "sampled":len(results),"limit":limit,
            "blocked_count":sum(x.get("status") == "SECURE_EGRESS_NOT_CONFIRMED" for x in results),
            "error_count":sum(x.get("status") == "SAMPLE_ERROR" for x in results),
            "text_hint_count":sum(x.get("status") == "HINTS_ONLY" for x in results),
            "verified_language_count":0,
            "results":results}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    with output_path.open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    return {"sampled":len(results)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--limit",type=int,default=8)
    parser.add_argument("--seconds",type=int,default=8)
    parser.add_argument("--allow-network",action="store_true",help="Explicitly permit bounded stream requests")
    args=parser.parse_args()
    print(json.dumps(run(args.snapshot,args.output,args.limit,args.seconds,args.allow_network)))

if __name__=="__main__":
    main()
