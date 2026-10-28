#!/usr/bin/env python3
"""Audit Turkish channels by verified stream identities; preserve all entries."""
import re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
s=p.read_text(encoding="utf-8-sig");lines=s.splitlines(keepends=True)
exact={"CNBC-E","TBMM TV","KANAL 53","EKOL TV","NOW (720P)"}
found={};moved=0
for i,line in enumerate(lines):
 if not line.startswith("#EXTINF:") or "YEDEKLER (" not in line:continue
 m=re.search(r'tvg-name="([^"]*)"',line)
 if not m or m.group(1) not in exact:continue
 lines[i]=re.sub(r'group-title="[^"]*YEDEKLER \(\d+\)"','group-title="🇹🇷 YENİ TÜRK (487)"',line,count=1)
 moved+=1;found[m.group(1)]=found.get(m.group(1),0)+1
if moved!=6:raise SystemExit(f"Expected six entries, found {moved}")
out="".join(lines);groups={}
for m in re.finditer(r'group-title="([^"]+)"',out):groups[m.group(1)]=groups.get(m.group(1),0)+1
if len(groups)!=14:raise SystemExit("Category count changed")
for group,n in groups.items():
 out=out.replace('group-title="'+group+'"','group-title="'+re.sub(r'\s*\(\d+\)$','',group)+f' ({n})"')
if out.count("#EXTINF:")!=s.count("#EXTINF:"):raise SystemExit("Channel count changed")
p.write_text(out,encoding="utf-8")
print(f"MOVED={moved} FOUND={found} TURK={next(n for k,n in groups.items() if 'YENİ TÜRK' in k)} BACKUPS={next(n for k,n in groups.items() if 'YEDEKLER' in k)}")
