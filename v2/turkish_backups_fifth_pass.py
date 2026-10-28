#!/usr/bin/env python3
"""Fifth audit: Turkish local TV identities, excluding VOD and ambiguous foreign channels."""
import re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
old=p.read_text(encoding="utf-8-sig")
names={"AKSU TV","CAY TV","ÇAY TV","CINE 1","ES TV","HUNAT TV","KAY TV","MERCAN TV","VAN 65 TV","TATLISES","BEIN IZ TV HD","D�ZG�N TV","EDIRNE TV","ESENLER SEHIR EKRANI","VIYANA TV HD","AKSU TV  KAHRAMANMARAŞ","ERCİŞ TV  VAN","ES TV  ESKİŞEHİR","ETV  KAYSERİ","HUNAT TV  KAYSERİ","KAY TV  KAYSERİ","MERCAN TV  ADIYAMAN","TV 1  KAYSERİ","TV 8  ULUSAL","GRT GAZİANTEP TV"}
lines=old.splitlines(keepends=True);moved=0;found={}
for i,line in enumerate(lines):
 if not line.startswith("#EXTINF:") or "YEDEKLER (" not in line:continue
 m=re.search(r'tvg-name="([^"]*)"',line)
 if not m:continue
 name=re.sub(r'\s*\(\d+[PI]\)$','',m.group(1),flags=re.I).strip().upper()
 if name not in names:continue
 lines[i]=re.sub(r'group-title="[^"]*YEDEKLER \(\d+\)"','group-title="🇹🇷 YENİ TÜRK (434)"',line,count=1)
 moved+=1;found[name]=found.get(name,0)+1
if moved<10:raise SystemExit(f"Unexpectedly few Turkish stations: {moved}")
out="".join(lines);groups={}
for m in re.finditer(r'group-title="([^"]+)"',out):groups[m.group(1)]=groups.get(m.group(1),0)+1
if len(groups)!=14:raise SystemExit("Category count changed")
for group,n in groups.items():
 out=out.replace('group-title="'+group+'"','group-title="'+re.sub(r'\s*\(\d+\)$','',group)+f' ({n})"')
if out.count("#EXTINF:")!=old.count("#EXTINF:"):raise SystemExit("Channel count changed")
p.write_text(out,encoding="utf-8")
print(f"MOVED={moved} MATCHES={found} TURK={next(n for k,n in groups.items() if 'YENİ TÜRK' in k)} BACKUPS={next(n for k,n in groups.items() if 'YEDEKLER' in k)}")
