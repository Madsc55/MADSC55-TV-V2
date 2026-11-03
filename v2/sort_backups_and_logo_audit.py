#!/usr/bin/env python3
"""Sort backup channels and fill only high-confidence missing logos.
Never invent or assign unrelated logos. Write a report of unresolved channels.
"""
import json,re,unicodedata,urllib.request
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
s=p.read_text(encoding="utf-8-sig");lines=s.splitlines(keepends=True)
first=next(i for i,x in enumerate(lines) if x.startswith("#EXTINF:"))
header=lines[:first];blocks=[];i=first
while i<len(lines):
 if not lines[i].startswith("#EXTINF:"):raise SystemExit("Unexpected playlist layout")
 j=i+1
 while j<len(lines) and not lines[j].startswith("#EXTINF:"):j+=1
 blocks.append(lines[i:j]);i=j
def group(b):return re.search(r'group-title="([^"]+)"',b[0]).group(1)
def name(b):
 m=re.search(r'tvg-name="([^"]*)"',b[0])
 return m.group(1) if m else b[0].split(",")[-1].strip()
def norm(x):
 x=x.upper().translate(str.maketrans("ÇĞİÖŞÜ","CGIOSU"))
 x=unicodedata.normalize("NFKD",x)
 x="".join(c for c in x if not unicodedata.combining(c))
 x=re.sub(r"\s*\((?:\d+[PI]|NOT 24/7|GEO-BLOCKED)\)","",x)
 return re.sub(r"[^A-Z0-9]+","",x)
def haslogo(b):return bool(re.search(r'tvg-logo="https?://[^"]+"',b[0]))
def putlogo(b,url):
 if 'tvg-logo="' in b[0]:b[0]=re.sub(r'tvg-logo="[^"]*"',lambda m:'tvg-logo="'+url+'"',b[0],count=1)
 else:b[0]=b[0].replace(' group-title=', ' tvg-logo="'+url+'" group-title=',1)
# Existing same-name channel logos are reliable when all occurrences agree.
existing={}
for b in blocks:
 if haslogo(b):
  logo=re.search(r'tvg-logo="([^"]+)"',b[0]).group(1)
  existing.setdefault(norm(name(b)),set()).add(logo)
verified={k:next(iter(v)) for k,v in existing.items() if k and len(v)==1}
external={}
try:
 req=urllib.request.Request("https://iptv-org.github.io/api/logos.json",headers={"User-Agent":"MADSC55-TV-logo-audit"})
 with urllib.request.urlopen(req,timeout=30) as response: logos=json.load(response)
 for row in logos:
  channel=row.get("channel","");url=row.get("url","")
  if channel and isinstance(url,str) and url.startswith("https://"):
   external.setdefault(channel, set()).add(url)
 external={k:next(iter(v)) for k,v in external.items() if len(v)==1}
except Exception as e:print("External catalog unavailable:",str(e))
filled_existing=filled_external=0
unresolved={"YENI_TURK":[],"YEDEKLER":[]}
for b in blocks:
 g=group(b)
 if "YENİ TÜRK" not in g and "YEDEKLER" not in g:continue
 if haslogo(b):continue
 n=name(b);k=norm(n);url=verified.get(k)
 if url:
  putlogo(b,url);filled_existing+=1;continue
 tvgid=re.search(r'tvg-id="([^"]+)"',b[0])
 if tvgid and tvgid.group(1) in external:
  putlogo(b,external[tvgid.group(1)]);filled_external+=1;continue
 unresolved["YENI_TURK" if "YENİ TÜRK" in g else "YEDEKLER"].append({"name":n,"tvg_id":tvgid.group(1) if tvgid else ""})
# Preserve category sequence and sort backup/Turkish groups alphabetically.
groups={};order=[]
for b in blocks:
 g=group(b)
 if g not in groups:groups[g]=[];order.append(g)
 groups[g].append(b)
for g in order:
 if "YEDEKLER" in g or "YENİ TÜRK" in g:groups[g].sort(key=lambda b:(norm(name(b)),name(b).casefold()))
out="".join(header)+"".join("".join(b) for g in order for b in groups[g])
if out.count("#EXTINF:")!=len(blocks):raise SystemExit("Channel count changed")
if len(order)!=14:raise SystemExit("Category count changed")
p.write_text(out,encoding="utf-8")
report={"total":len(blocks),"filled_from_existing":filled_existing,"filled_from_iptv_org":filled_external,"unresolved_counts":{k:len(v) for k,v in unresolved.items()},"unresolved":unresolved}
dest=Path(__file__).resolve().parent/"reports"/"logo-audit.json";dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k!="unresolved"},ensure_ascii=False))
