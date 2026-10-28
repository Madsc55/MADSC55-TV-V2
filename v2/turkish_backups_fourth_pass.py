#!/usr/bin/env python3
"""Fourth audit: exact curated Turkish stations and location-specific channels, not VOD."""
import re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
old=p.read_text(encoding="utf-8-sig")
station_names={"ADA TV","KIBRIS TV","DIYAR TV","KOCAELI TV","HRT AKDENIZ","GRT TV  GAZİANTEP","TV 264  SAKARYA","URFANATİK TV  ŞANLIUFRA","TRABZON BUYUKSEHIR BELEDIYESI TV","BEGEN TV","CINE 1 TV","SDM TV","STAR-TV"}
lines=old.splitlines(keepends=True);count=0;matched={}
for i,line in enumerate(lines):
 if not line.startswith("#EXTINF:") or "YEDEKLER (" not in line:continue
 m=re.search(r'tvg-name="([^"]*)"',line)
 if not m:continue
 name=re.sub(r'\s*\(\d+[PI]\)$','',m.group(1),flags=re.I).strip().upper()
 if name not in station_names:continue
 lines[i]=re.sub(r'group-title="[^"]*YEDEKLER \(\d+\)"','group-title="🇹🇷 YENİ TÜRK (418)"',line,count=1)
 count+=1;matched[name]=matched.get(name,0)+1
if count<10:raise SystemExit(f"Too few matches: {count}")
result="".join(lines);groups={}
for m in re.finditer(r'group-title="([^"]+)"',result):groups[m.group(1)]=groups.get(m.group(1),0)+1
if len(groups)!=14:raise SystemExit(f"Categories changed: {len(groups)}")
for group,n in groups.items():
 result=result.replace('group-title="'+group+'"','group-title="'+re.sub(r'\s*\(\d+\)$','',group)+f' ({n})"')
if result.count("#EXTINF:")!=old.count("#EXTINF:"):raise SystemExit("Lost channel")
p.write_text(result,encoding="utf-8")
print("FOURTH_PASS",count,matched)
