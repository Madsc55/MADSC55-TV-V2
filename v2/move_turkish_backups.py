#!/usr/bin/env python3
"""Move Turkish-labelled candidates from existing YEDEKLER into YENİ TÜRK."""
import re
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
s=P.read_text(encoding="utf-8-sig")
lines=s.splitlines(keepends=True)
backup="🗂️ YEDEKLER"
newgroup="🇹🇷 YENİ TÜRK"
known=re.compile(r"\b(?:TRT(?:\s|$)|ATV(?:\s|$)|SHOW TV|STAR TV|KANAL [0-9D]|TV8|HABER(?:\s|[0-9])|HABERTÜRK|HABERTURK|CNN TÜRK|CNN TURK|NTV(?:\s|$)|MİNİKA|MINIKA|DHA CANLI|BLOOMBERG HT|TEVE2|BEYAZ TV|HALK TV|TELE1|SÖZCÜ|SOZCU|ÜLKE TV|ULKE TV|AKİT TV|AKIT TV|TGRT|A HABER|A SPOR|TRT|TÜRK|TURK|KRT TV|EKOTÜRK|EKOTURK|KANAL 7|360 TV|24 TV|DOST TV|MELTEM TV|LALEGÜL|LALEGUL|BRTV|AS TV BURSA|LINE TV BURSA|ER TV|EUROSTAR TR|SHOW MAX TR)\b",re.I)
negative=re.compile(r"\b(?:TURKMENISTAN|TÜRKMENISTAN|TURKMEN|TÜRKMEN|TURKISH CYPRUS)\b",re.I)
moved=0
out=[]
for line in lines:
    if not line.startswith("#EXTINF:") or not re.search(r'group-title="[^"]*YEDEKLER[^"]*"',line):
        out.append(line);continue
    title=line.rsplit(",",1)[-1].strip()
    name=re.search(r'tvg-name="([^"]*)"',line)
    label=(name.group(1) if name else title).upper()
    label=label.replace("İ","I").replace("Ü","U").replace("Ö","O").replace("Ş","S").replace("Ç","C").replace("Ğ","G")
    original=(name.group(1) if name else title).upper()
    tr_marker=bool(re.search(r"(?:^|[\s\[(])TR(?:\b|\])|TURKEY|TÜRKİYE|TURKIYE",original))
    is_turkish=tr_marker or bool(known.search(original))
    if negative.search(original):is_turkish=False
    if is_turkish:
        line=re.sub(r'group-title="[^"]*YEDEKLER[^"]*"',f'group-title="{newgroup}"',line,count=1)
        moved+=1
    out.append(line)
if moved<50:raise SystemExit(f"Too few Turkish matches: {moved}")
result="".join(out)
counts={}
for m in re.finditer(r'group-title="([^"]+)"',result):
    counts[m.group(1)]=counts.get(m.group(1),0)+1
if len(counts)!=14:raise SystemExit(f"Expected 14 categories, found {len(counts)}")
for old,count in counts.items():
    updated=re.sub(r"\s*\(\d+\)$","",old)+f" ({count})"
    result=result.replace(f'group-title="{old}"',f'group-title="{updated}"')
if result.count("#EXTINF:")!=s.count("#EXTINF:"):raise SystemExit("Channel count changed")
P.write_text(result,encoding="utf-8")
print(f"MOVED={moved} YEDEKLER={next(v for k,v in counts.items() if 'YEDEKLER' in k)} CATEGORIES={len(counts)}")
