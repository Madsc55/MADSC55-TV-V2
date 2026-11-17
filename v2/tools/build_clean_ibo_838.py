#!/usr/bin/env python3
"""Produce an independent 838-channel IBO playlist; never edit the source."""
from pathlib import Path
import re
src=Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
dst=Path("MADSC55_TV_IBO_TEMIZ_838.m3u8")
lines=src.read_text(encoding="utf-8-sig",errors="replace").splitlines()
assert lines and lines[0].startswith("#EXTM3U"),"Invalid playlist header"
groups=re.compile(r'group-title\s*=\s*(?:"([^"]*)"|\x27([^\x27]*)\x27|([^,\s]*))',re.I)
blocks=[];current=[]
for line in lines[1:]:
    if line.startswith("#EXTINF"):
        current=[line]
    elif line.startswith("#") or not line.strip():
        if current: current.append(line)
    elif current:
        blocks.append(current+[line]);current=[]
assert len(blocks)==18960,f"Unexpected source count: {len(blocks)}; refusing unsafe output"
keep=[];excluded=[]
for block in blocks:
    m=groups.search(block[0])
    group=next((x for x in m.groups() if x is not None),"") if m else ""
    if "YEDEKLER" in group.upper() or "YEDEK" in group.upper() or "TEST_001" in group.upper():
        excluded.append(block)
    else: keep.append(block)
assert len(keep)==838 and len(excluded)==18122, f"Unexpected split: {len(keep)} kept, {len(excluded)} excluded"
out=[lines[0]]
for block in keep: out.extend(block)
dst.write_text("\n".join(out)+"\n",encoding="utf-8")
print(f"CREATED {dst}: {len(keep)} channels; {len(excluded)} excluded; original untouched")
