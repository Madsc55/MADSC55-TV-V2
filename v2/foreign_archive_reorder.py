"""Lossless stable partition of the foreign archive, with independently reviewed evidence."""
from hashlib import sha256
from collections import Counter
import re
from playlist_parts_manager import split_records, category

def digest(data):
    return sha256(data).hexdigest()

def prepare(raw, report, reviewed, request):
    if report.get("complete") is not True or report.get("playlist_sha256") != digest(raw):
        raise ValueError("Incomplete or stale audit")
    if not isinstance(request,str) or len(request.strip())<12:
        raise ValueError("Missing owner authorization")
    header,records=split_records(raw)
    foreign=[i for i,r in enumerate(records) if re.fullmatch(r"YABANCI ARŞİVİ(?: \(\d+\))?",category(r))]
    if not foreign or foreign != list(range(foreign[0],foreign[-1]+1)):
        raise ValueError("Noncontiguous foreign archive")
    rows=report["results"]
    if [r.get("position") for r in rows]!=[i+1 for i in foreign]:
        raise ValueError("Missing or duplicate coverage")
    evidence={}
    for e in reviewed:
        key=(e["position"],e["record_sha256"],e["url_sha256"])
        if key in evidence:
            raise ValueError("Duplicate independent evidence")
        evidence[key]=e
    selected=[]
    for i,row in zip(foreign,rows):
        rec=records[i]
        urls=[u for u in rec.splitlines()[1:] if u.startswith((b"http://",b"https://"))]
        url_hash=digest(urls[0]) if len(urls)==1 else None
        if row.get("record_sha256")!=digest(rec) or row.get("url_sha256")!=url_hash:
            raise ValueError("Evidence identity mismatch")
        e=evidence.get((i+1,digest(rec),url_hash),{})
        rounds=row.get("rounds",[])
        green=(row.get("classification") in ("AV_60S_VERIFIED","AV_60S_LATE_START_VERIFIED")
               and len(rounds)==3 and row.get("healthy_rounds")==3
               and all(r.get("healthy_60s") is True and any(
                   x.get("full_sample") is True and x.get("video") is True and x.get("audio") is True
                   and not x.get("quality_flags") for x in r.get("evidence",[])) for r in rounds))
        verified=(e.get("identity_evidence_verified") is True and bool(e.get("observed_channel_id"))
                  and e.get("observed_channel_id")==e.get("channel_id")
                  and ((e.get("speech_review_verified") is True and e.get("speech_language") in ("tr","tur"))
                       or (e.get("origin_review_verified") is True and e.get("broadcast_origin") in
                           ("TR","CY-NORTH","AZ","TM","KZ","KG","UZ"))))
        if green and verified and url_hash:
            selected.append(i)
    chosen=set(selected)
    order=selected+[i for i in foreign if i not in chosen]
    result=header+b"".join(records[:foreign[0]]+[records[i] for i in order]+records[foreign[-1]+1:])
    if Counter(split_records(result)[1])!=Counter(records):
        raise ValueError("Record conservation failed")
    manifest=None
    if result!=raw:
        if len(selected)>2500:
            raise ValueError("Authorization manifest capacity exceeded")
        manifest={"base_sha256":digest(raw),"result_sha256":digest(result),"operation":"reorder",
                  "request":request,"channels":[records[i].splitlines()[0].decode().rsplit(",",1)[-1] for i in selected]}
    return result,manifest
