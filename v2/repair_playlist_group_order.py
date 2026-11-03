#!/usr/bin/env python3
"""Repair playlist: contiguous categories, real counts, Turkish alphabetical sort."""
import re,unicodedata
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
s=p.read_text(encoding="utf-8-sig");lines=s.splitlines(keepends=True)
start=next(i for i,x in enumerate(lines) if x.startswith("#EXTINF:"))
header=lines[:start];blocks=[];i=start
while i<len(lines):
 if not lines[i].startswith("#EXTINF:"):raise SystemExit(f"Unexpected line {i}: {lines[i][:50]}")
 j=i+1
 while j<len(lines) and not lines[j].startswith("#EXTINF:"):j+=1
 blocks.append(lines[i:j]);i=j
def group(b):
 m=re.search(r'group-title="([^"]+)"',b[0])
 if not m:raise SystemExit("Missing category")
 return re.sub(r'\s*\(\d+\)$','',m.group(1))
def name(b):
 m=re.search(r'tvg-name="([^"]*)"',b[0])
 return m.group(1) if m else b[0].split(",")[-1].strip()
def sortkey(b):
 t=name(b).upper().translate(str.maketrans("ÇĞİÖŞÜ","CGIOSU"))
 return unicodedata.normalize("NFKD",t).casefold()
groups={};order=[]
for b in blocks:
 g=group(b)
 if g not in groups:groups[g]=[];order.append(g)
 groups[g].append(b)
turk="🇹🇷 YENİ TÜRK";backup="🗂️ YEDEKLER"
assert turk in groups and backup in groups
# Known Turkish-language Yesilcam station was still in backups.
moved=[]
for b in list(groups[backup]):
 if name(b).strip().upper()=="CINE+" and "yesilcam" in "".join(b).lower():
  groups[backup].remove(b);groups[turk].append(b);moved.append(name(b))
groups[turk].sort(key=sortkey)
output=list(header)
for g in order:
 for b in groups[g]:
  b=b.copy();b[0]=re.sub(r'group-title="[^"]+"',lambda m:'group-title="'+g+f' ({len(groups[g])})"',b[0],count=1)
  output.extend(b)
out="".join(output)
if out.count("#EXTINF:")!=len(blocks):raise SystemExit("Lost channels")
if len(groups)!=14:raise SystemExit("Category count changed")
p.write_text(out,encoding="utf-8")
print("TOTAL",len(blocks),"TURK",len(groups[turk]),"BACKUPS",len(groups[backup]),"MOVED",moved,"CATEGORY_ORDER",order)
