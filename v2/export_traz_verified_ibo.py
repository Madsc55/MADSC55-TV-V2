#!/usr/bin/env python3
"""Create a PRIVATE isolated IBO device-test M3U from authenticated AV evidence.

Requires user's own off-repo RSA private key. No GitHub publication, playlist
promotion, main playlist edits or fabricated test results. Ambiguous identities
are held for review. Single AV proof is NOT 24-hour uptime or device proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from stage3_sealed_export import open_rows
from traz_api_av_batch import REPORT,SEALED,validate
from traz_api_source_batch import public_stream

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/"v2/reports/private-traz-av-ibo-device-test.m3u8"
MAIN=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"

def make_entries(report,rows):
    public={x["url_sha256"]:x for x in report["streams"]}
    result=[]
    seen=set()
    ambiguous=0
    for row in rows:
        url=row.get("url")
        h=row.get("url_sha256")
        if not isinstance(url,str) or hashlib.sha256(url.encode()).hexdigest()!=h:
            raise ValueError("Private AV candidate URL identity mismatch")
        p=public.get(h)
        if p is None or p["status"]!=row.get("probe_status") or p["decoded"]!=row.get("decoded"):
            raise ValueError("Encrypted evidence and public report disagree")
        if h in seen:
            raise ValueError("Duplicate AV URL in authenticated archive")
        seen.add(h)
        if p["decoded"] is not True:
            continue
        if row.get("video") is not True or row.get("audio") is not True:
            raise ValueError("False FFmpeg dual decode evidence")
        ids=p.get("channel_ids")
        if not isinstance(ids,list) or ids!=row.get("channel_ids"):
            raise ValueError("Encrypted channel identity differs from AV report")
        if len(ids)!=1:
            ambiguous+=1
            continue
        if not public_stream(url):
            raise ValueError("Unsafe verified URL")
        safe_name=" ".join(ids[0].replace("\r"," ").replace("\n"," ").replace('"',"'").split())
        if not safe_name:
            raise ValueError("Missing actual channel identity")
        result.append((safe_name,url))
    if seen!=set(public):
        raise ValueError("Encrypted stream evidence incomplete")
    return result,ambiguous

def export(private_key,output=DEFAULT,report_file=REPORT,sealed_file=SEALED):
    output=Path(output)
    if output.resolve()==MAIN.resolve():
        raise ValueError("Refuse writing production IBO playlist")
    if output.exists() or output.is_symlink():
        raise ValueError("Refuse to replace any existing playlist")
    if Path(report_file).resolve()!=REPORT.resolve() or Path(sealed_file).resolve()!=SEALED.resolve():
        raise ValueError("Only approved authenticated acceptance report allowed")
    d=validate()
    if d["unprobed"]:
        raise ValueError("Refuse partial AV evidence export")
    rows=open_rows(sealed_file,private_key)
    selected,ambiguous=make_entries(d,rows)
    lines=["#EXTM3U"]
    for name,url in selected:
        lines.extend(['#EXTINF:-1 group-title="TEST - GERCEK AV, IBO CIHAZ ONAYI BEKLIYOR",'+name,url])
    output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as out:
        out.write("\n".join(lines)+"\n")
    return {"private_test_entries":len(selected),
            "ambiguous_channel_identities_not_exported":ambiguous,
            "ibo_device_verified":False,"main_playlist_modified":False,
            "long_term_stability_unverified":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--private-key",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=DEFAULT)
    a=parser.parse_args()
    print(json.dumps(export(a.private_key,a.output),sort_keys=True))

if __name__=="__main__":
    main()
