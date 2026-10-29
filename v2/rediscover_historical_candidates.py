#!/usr/bin/env python3
"""Match historical decoded SHA256 identities against newly fetched source URLs.
Private URLs are never exported; matching is discovery only, not playback verification.
"""
import argparse
import hashlib
import json
from pathlib import Path
from discover import entries, fetch, turkish_candidate

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--old",required=True)
    p.add_argument("--new",required=True)
    p.add_argument("--sources",required=True)
    p.add_argument("--dynamic-sources",default="")
    p.add_argument("--output",required=True)
    a=p.parse_args()
    old=json.loads(Path(a.old).read_text())
    new=json.loads(Path(a.new).read_text())
    old_decoded={x["url_sha256"]:x for x in old["channel_results"] if x.get("playback")=="VIDEO_DECODED"}
    new_hashes={x["url_sha256"] for x in new["channel_results"]}
    missing=set(old_decoded)-new_hashes
    sources=json.loads(Path(a.sources).read_text())["sources"]
    dynamic_status="NOT_PROVIDED"
    if a.dynamic_sources:
        dynamic=Path(a.dynamic_sources)
        if dynamic.is_file():
            try:
                catalog=json.loads(dynamic.read_text())
                seen={s["url"] for s in sources}
                added=0
                for item in catalog.get("sources",[])[:80]:
                    url=item.get("url","")
                    if url.startswith("https://") and url not in seen:
                        sources.append({"id":"github-recovered-"+str(added),"url":url,"scope":"candidate"})
                        seen.add(url)
                        added+=1
                dynamic_status="LOADED_"+str(added)
            except (OSError,ValueError,TypeError,KeyError):
                dynamic_status="INVALID_CATALOG"
        else:
            dynamic_status="CATALOG_UNAVAILABLE"
    matched={}
    audit=[]
    for s in sources:
        try:
            parsed=list(entries(fetch(s["url"])))
            count=0
            for item in parsed:
                if not turkish_candidate(item,s.get("scope","candidate")):
                    continue
                digest=hashlib.sha256(item["url"].encode()).hexdigest()
                if digest in missing:
                    count+=1
                    matched.setdefault(digest,{"url_sha256":digest,"historical_source":old_decoded[digest].get("source",""),"rediscovered_source":s["id"],"name":old_decoded[digest].get("name",""),"status":"HISTORICAL_DECODED_URL_REDISCOVERED_NOT_RETESTED"})
            audit.append({"source":s["id"],"parsed":len(parsed),"matched":count,"status":"OK"})
        except Exception as e:
            audit.append({"source":s["id"],"status":"FETCH_FAILED","error":type(e).__name__})
    out={"policy":"READ_ONLY_NO_STREAM_URLS_NO_AUTOPUBLISH","old_decoded_missing_from_new":len(missing),"rediscovered_count":len(matched),"still_unmatched":len(missing)-len(matched),"dynamic_catalog_status":dynamic_status,"sources":audit,"rediscovered":list(matched.values())}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print("Historical decoded missing:",len(missing),"rediscovered:",len(matched),"still unmatched:",len(missing)-len(matched))
    if any(x["status"]=="FETCH_FAILED" for x in audit):
        print("WARNING: Some source fetches failed; recovery coverage is incomplete")
if __name__=="__main__":
    main()
