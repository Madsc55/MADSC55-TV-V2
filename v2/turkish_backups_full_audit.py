#!/usr/bin/env python3
"""Full remaining-backups audit using Turkish regional station names AND Turkish stream hosts.
Never classify VOD episodes or foreign channels by generic words alone.
"""
import re
from pathlib import Path
from urllib.parse import urlsplit
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
old=p.read_text(encoding="utf-8-sig")
station_names={
"ALANYA POSTA TV","ARAS TV","EDESSA TV","ILKE TV","KN MUSIC TV","POWER DANCE","POWER LOVE","RUHA TV","SERCEM TV","SONMEZ TV","TV 4","TV4","TV DEN","POWER HD","DERIN TV","KANAL AVRUPA","TOKAT TV","İZMİR TIME 35 TV","IZMIR TIME 35 TV",
"AKSU TV","CAY TV","ÇAY TV","CINE 1","ES TV","HUNAT TV","KAY TV","MERCAN TV","VAN 65 TV","TATLISES","BEIN IZ TV HD","D�ZG�N TV","EDIRNE TV","ESENLER SEHIR EKRANI","VIYANA TV HD","AKSU TV  KAHRAMANMARAŞ","ERCİŞ TV  VAN","ES TV  ESKİŞEHİR","ETV  KAYSERİ","HUNAT TV  KAYSERİ","KAY TV  KAYSERİ","MERCAN TV  ADIYAMAN","TV 1  KAYSERİ","TV 8  ULUSAL","GRT GAZİANTEP TV"
}
regional=re.compile(r"\b(?:ALANYA|TOKAT|URFA|ŞANLIURFA|SANLIURFA|GAZİANTEP|GAZIANTEP|KAHRAMANMARAŞ|KAHRAMANMARAS|KAYSERİ|KAYSERI|ESKİŞEHİR|ESKISEHIR|ADIYAMAN|ERZURUM|ELAZIĞ|ELAZIG|TRABZON|RİZE|RIZE|GİRESUN|GIRESUN|SAMSUN|ORDU|SİVAS|SIVAS|KONYA|ANKARA|İZMİR|IZMIR|EDİRNE|EDIRNE|İSTANBUL|ISTANBUL|KOCAELİ|KOCAELI|SAKARYA|ANTALYA|MERSİN|MERSIN|HATAY|DİYARBAKIR|DIYARBAKIR|KIBRIS|KIBRIS|TÜRKİYE|TURKIYE)\b",re.I)
vod=re.compile(r"\bS\d{1,3}E\d{1,3}\b|\bS\d{1,3}\b.*\bE\d{1,3}\b|\.(?:MKV|MP4|AVI)\b|\bEPISODE\b",re.I)
lines=old.splitlines(keepends=True);moved=0;reason={}
for i,line in enumerate(lines):
 if not line.startswith("#EXTINF:") or "YEDEKLER (" not in line:continue
 m=re.search(r'tvg-name="([^"]*)"',line)
 if not m:continue
 name=re.sub(r"\s*\(\d+[PI]\)$","",m.group(1),flags=re.I).strip().upper()
 if vod.search(name):continue
 url=lines[i+1].strip() if i+1<len(lines) else ""
 host=urlsplit(url).hostname or ""
 host=host.lower()
 exact=name in station_names
 turkish_host=host.endswith(".com.tr") or host.endswith(".gov.tr") or host.endswith(".org.tr") or host.endswith(".net.tr") or "turkmedya-live.ercdn.net" in host or host.endswith("yayin.com.tr") or host.endswith("powerapp.com.tr")
 regional_name=bool(regional.search(name)) and not re.search(r"\b(?:TRAVEL|TOURISM|MOVIE|FILM|SERIES|VOD)\b",name)
 if not (exact or (turkish_host and regional_name)):continue
 lines[i]=re.sub(r'group-title="[^"]*YEDEKLER \(\d+\)"','group-title="🇹🇷 YENİ TÜRK (463)"',line,count=1)
 moved+=1;reason[name]=reason.get(name,0)+1
if moved<15:raise SystemExit(f"Too few confirmed matches: {moved}")
out="".join(lines);groups={}
for m in re.finditer(r'group-title="([^"]+)"',out):groups[m.group(1)]=groups.get(m.group(1),0)+1
if len(groups)!=14:raise SystemExit("Category count changed")
for group,n in groups.items():
 out=out.replace('group-title="'+group+'"','group-title="'+re.sub(r'\s*\(\d+\)$','',group)+f' ({n})"')
if out.count("#EXTINF:")!=old.count("#EXTINF:"):raise SystemExit("Channel count changed")
p.write_text(out,encoding="utf-8")
print("FULL_AUDIT_MOVED",moved,"MATCHES",reason,"TURK",next(n for k,n in groups.items() if 'YENİ TÜRK' in k),"BACKUPS",next(n for k,n in groups.items() if 'YEDEKLER' in k))
