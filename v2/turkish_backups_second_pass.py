#!/usr/bin/env python3
"""Second pass: identify Turkish LIVE channel names missed in YEDEKLER; exclude VOD."""
import re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
raw=p.read_text(encoding="utf-8-sig")
patterns=r"(?:ULUSAL TV|ANADOLU NET TV|BENGÜTÜRK|BENGUTURK|Bİ KANAL|BI KANAL|DİYANET TV|DIYANET TV|ETV KAYSER|ERZURUM WEB TV|FB TV|KANAL (?:12|15|19|23|26|32|34|58|B|FIRAT|FIRAT|URFA|V)|KARADEN[Iİ]Z TV|KONYA OLAY TV|LINE TV|MED M[UÜ]Z[Iİ]K|POWER TV|SHOW MAX|ZAROK TV|AS TV.*BURSA|NTV.*HABER|\b360\b|\bA2\b|24 KANAL|KANAL 7|HABER 61|HABER61|TRT|T[UÜ]RK|MINIKA|MİNİKA|DHA CANLI|BLOOMBERG HT|MELTEM TV|LALEG[UÜ]L|BRTV|EUROSTAR TR|ULKE TV|ÜLKE TV|TGRT|A HABER|A SPOR|BEYAZ TV|HALK TV|TELE1|S[OÖ]ZC[UÜ] TV|KRT TV|EKOT[UÜ]RK|STAR TV|SHOW TV|KANAL D|TV8|ATV)"
rx=re.compile(patterns,re.I)
vod=re.compile(r"(?:S\d{1,3}E\d{1,3}|\bS\d{1,3}\b.*\bE\d{1,3}\b|\.(?:MKV|MP4|AVI)\b|EPISODE|B[OÖ]L[UÜ]M\s*\d+)",re.I)
lines=raw.splitlines(keepends=True);moved=0;sample=[]
for i,line in enumerate(lines):
 if not line.startswith("#EXTINF:") or "YEDEKLER (" not in line:continue
 name=line.rsplit(",",1)[-1].strip()
 if vod.search(name):continue
 if rx.search(name):
  lines[i]=re.sub(r'group-title="[^"]*YEDEKLER \(\d+\)"','group-title="🇹🇷 YENİ TÜRK"',line,count=1)
  moved+=1
  if len(sample)<15:sample.append(name)
if moved<20:raise SystemExit(f"Unexpectedly few: {moved}")
result="".join(lines);counts={}
for m in re.finditer(r'group-title="([^"]+)"',result):counts[m.group(1)]=counts.get(m.group(1),0)+1
if len(counts)!=14:raise SystemExit(f"Category count {len(counts)}")
for old,n in counts.items():
 new=re.sub(r'\s*\(\d+\)$','',old)+f" ({n})"
 result=result.replace('group-title="'+old+'"','group-title="'+new+'"')
if result.count("#EXTINF:")!=raw.count("#EXTINF:"):raise SystemExit("Entry count changed")
p.write_text(result,encoding="utf-8")
print(f"SECOND_PASS_MOVED={moved} YENI_TURK={next(n for k,n in counts.items() if 'YENİ TÜRK' in k)} YEDEKLER={next(n for k,n in counts.items() if 'YEDEKLER' in k)} SAMPLE={sample}")
