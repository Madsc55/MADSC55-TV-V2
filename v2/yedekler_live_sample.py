#!/usr/bin/env python3
"""Read-only bounded live evidence for the SEPARATE YEDEKLER playlist."""
import argparse, hashlib, json, os, pathlib, re
from single_channel_evidence_review import review_one

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--playlist",default="YEDEKLER_PLAYLISTESI.m3u8")
    p.add_argument("--output",required=True)
    p.add_argument("--limit",type=int,default=10)
    p.add_argument("--model-dir")
    a=p.parse_args()
    if not 1<=a.limit<=100:
        p.error("Limit must be 1..100 per run")
    if os.environ.get("MADSC55_SECURE_EGRESS_CONFIRMED")!="1":
        p.error("Secure egress must be independently verified")
    source=pathlib.Path(a.playlist)
    out=pathlib.Path(a.output)
    if out.exists() or source.resolve()==out.resolve():
        p.error("Output exists or overwrites playlist")
    out.parent.mkdir(parents=True,exist_ok=True)
    if a.model_dir and not pathlib.Path(a.model_dir).is_dir():
        p.error("ASR model directory not found")
    entries=[]; pending=None
    for line in source.open(encoding="utf-8-sig",errors="replace"):
        line=line.strip()
        if line.startswith("#EXTINF:"):
            pending=line
        elif line and not line.startswith("#") and pending:
            entries.append((pending,line));pending=None
    seen=set(); attempted=0
    with out.open("x",encoding="utf-8") as f:
        for i,(metadata,url) in enumerate(entries,1):
            digest=hashlib.sha256(url.encode()).hexdigest()
            if digest in seen: continue
            seen.add(digest)
            if attempted>=a.limit: break
            attempted+=1
            name=metadata.rsplit(",",1)[-1][:120]
            result={"ordinal":i,"name":name,"url_sha256":digest,"playlist_modified":False}
            try:
                evidence=review_one(url,out.parent/("sample-"+digest+".json"),seconds=8,source_authorized=True,model_dir=a.model_dir)
                result["evidence"]=evidence
            except Exception as exc:
                result["status"]="INCONCLUSIVE"
                result["reason_code"]=type(exc).__name__
            f.write(json.dumps(result,ensure_ascii=False)+"\n")
            f.flush()
    print(json.dumps({"records":len(entries),"unique_seen":len(seen),"attempted":attempted,"output":str(out),"playlist_modified":False}))
if __name__=="__main__": main()
