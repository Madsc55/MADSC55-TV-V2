#!/usr/bin/env python3
"""Fail closed if a quarantined test_001 backup record is reintroduced."""
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
QUARANTINE=ROOT/"v2/archives/test001_quarantined_48.json"
PLAYLIST=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"

def entries(path):
    result=[]
    current=None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("#EXTINF:"):
            current={"name":line.rsplit(",",1)[-1].strip(),"url":""}
            result.append(current)
        elif current is not None and line.strip() and not line.startswith("#") and not current["url"]:
            current["url"]=line.strip()
    return result

def identity(record):
    return (record["name"].casefold().strip(),record["url"].strip())

def main():
    data=json.loads(QUARANTINE.read_text(encoding="utf-8"))
    banned={identity(r) for r in data["entries"]}
    assert len(data["entries"])==48 and len(banned)==48,"Quarantine inventory invalid"
    playlist=entries(PLAYLIST)
    assert len(playlist)>=838,"Main channel count below protected baseline"
    found=[(i+1,r["name"]) for i,r in enumerate(playlist) if identity(r) in banned]
    if found:
        print("FAIL: quarantined test_001 records reintroduced:",found,file=sys.stderr)
        return 1
    print(f"PASS: {len(playlist)} channels; 48 quarantined identities absent")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
