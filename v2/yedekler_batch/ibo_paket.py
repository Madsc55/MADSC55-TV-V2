#!/usr/bin/env python3
"""Render 2500-channel IBO YEDEKLER window without touching unrelated groups."""
import argparse, hashlib, json, os, re, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ARCHIVE=HERE/"YEDEKLER_ARCHIVE.m3u8"
STATE=HERE/"state.json"
GROUP=re.compile(r'group-title=["\']([^"\']*)["\']',re.I)

def parse(data):
    lines=data.splitlines(keepends=True)
    prefix=[]; blocks=[]; i=0
    while i<len(lines) and not lines[i].startswith("#EXTINF"):
        prefix.append(lines[i]); i+=1
    while i<len(lines):
        if not lines[i].startswith("#EXTINF"):
            raise ValueError("Unexpected content outside EXTINF blocks")
        block=[lines[i]]; i+=1
        while i<len(lines) and not lines[i].startswith("#EXTINF"):
            block.append(lines[i]);i+=1
        blocks.append(block)
    return prefix,blocks

def write_atomic(path,data):
    fd,name=tempfile.mkstemp(prefix=path.name+".",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--playlist",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--apply",action="store_true",help="write output; default is preview only")
    p.add_argument("--first-batch",action="store_true",help="preview first 2500 without changing state")
    a=p.parse_args()
    if a.playlist.resolve()==a.output.resolve():raise SystemExit("REFUSED: output must be separate from source playlist")
    s=json.loads(STATE.read_text(encoding="utf-8"))
    raw=ARCHIVE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=s["source_sha256"]:raise SystemExit("REFUSED: archive SHA mismatch")
    _,ab=parse(raw)
    if len(ab)!=s["total"]:raise SystemExit("REFUSED: archive count mismatch")
    prefix,blocks=parse(a.playlist.read_bytes())
    positions=[i for i,b in enumerate(blocks) if (m:=GROUP.search(b[0])) and "YEDEKLER" in m.group(1).upper()]
    if len(positions)!=s["total"]:raise SystemExit(f"REFUSED: expected {s['total']} source YEDEKLER channels; got {len(positions)}")
    if [blocks[i] for i in positions]!=ab:raise SystemExit("REFUSED: source YEDEKLER blocks differ from pinned archive")
    if a.first_batch:
        if s["status"] or s["history"]:raise SystemExit("REFUSED: first batch only for untouched state")
        selected=list(range(2500))
    else:
        selected=[i for i in range(s["total"]) if s["status"].get(str(i+1),"ANA_ARSIV")=="TEST"]
        if len(selected)>2500:raise SystemExit("REFUSED: more than 2500 in TEST")
    chosen=[ab[i] for i in selected]
    retained=[b for i,b in enumerate(blocks) if i not in set(positions)]
    insert_at=positions[0]
    # Preserve every unrelated channel in its original relative order.
    non_y_before=sum(i<insert_at for i in range(len(blocks)) if i not in set(positions))
    result=retained[:non_y_before]+chosen+retained[non_y_before:]
    rendered="".join(prefix+"".join(sum(result,[])).splitlines(keepends=True)) if False else "".join(prefix+sum(result,[])).encode("utf-8")
    print(json.dumps({"ibo_yedekler":len(chosen),"ana_arsiv":s["total"]-len(chosen)-sum(s["status"].get(str(i),"ANA_ARSIV") in ("TURK","YABANCI") for i in range(1,s["total"]+1)),"output":str(a.output),"preview":not a.apply},ensure_ascii=False))
    if a.apply:
        if a.output.exists():raise SystemExit("REFUSED: output exists; no overwrite")
        write_atomic(a.output,rendered)
if __name__=="__main__":main()
