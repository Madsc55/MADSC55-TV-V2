#!/usr/bin/env python3
"""Third pass, curated Turkish station identities only; avoid broad substring false positives."""
import re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
s=p.read_text(encoding="utf-8-sig")
names={"ARADANA TV","MEDYAHABER TV","EKOL SPORTS","HTSPOR TV","ICEL TV","İÇEL TV","URFA NATIK TV","KANAL PLUS","EL TV","24"}
lines=s.splitlines(keepends=True)
moved=0;found={}
for i,line in enumerate(lines):
 if not line.startswith("#EXTINF:") or "YEDEKLER (" not in line:continue
 m=re.search(r'tvg-name="([^"]*)"',line)
 if not m:continue
 name=re.sub(r"\s*\(\d+P\)$","",m.group(1),flags=re.I).strip().upper()
 if name not in names:continue
 # NTV, STAR, SHOW and KANAL are international names; only curated identities here.
 lines[i]=re.sub(r'group-title="[^"]*YEDEKLER \(\d+\)"','group-title="🇹🇷 YENİ TÜRK (405)"',line,count=1)
 moved+=1;found[name]=found.get(name,0)+1
if moved<5:raise SystemExit(f"Unexpectedly few Turkish entries: {moved}")
out="".join(lines)
counts={}
for m in re.finditer(r'group-title="([^"]+)"',out):counts[m.group(1)]=counts.get(m.group(1),0)+1
if len(counts)!=14:raise SystemExit("Category invariant")
for old,n in counts.items():
 new=re.sub(r"\s*\(\d+\)$","",old)+f" ({n})"
 out=out.replace('group-title="'+old+'"','group-title="'+new+'"')
if out.count("#EXTINF:")!=s.count("#EXTINF:"):raise SystemExit("Entry invariant")
p.write_text(out,encoding="utf-8")
print(f"THIRD_PASS_MOVED={moved} FOUND={found} TURK={next(n for k,n in counts.items() if 'YENİ TÜRK' in k)} BACKUPS={next(n for k,n in counts.items() if 'YEDEKLER' in k)}")
