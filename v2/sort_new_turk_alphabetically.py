#!/usr/bin/env python3
"""Sort only YENI TURK entries alphabetically, preserving every other entry."""
import re, unicodedata
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
s=p.read_text(encoding="utf-8-sig")
lines=s.splitlines(keepends=True)
blocks=[];prefix=[];i=0
while i<len(lines):
 if not lines[i].startswith("#EXTINF:"):
  prefix.append(lines[i]);i+=1;continue
 j=i+1
 while j<len(lines) and not lines[j].startswith("#EXTINF:"):j+=1
 blocks.append(lines[i:j]);i=j
def is_turk(b):return 'group-title="🇹🇷 YENİ TÜRK (' in b[0]
positions=[i for i,b in enumerate(blocks) if is_turk(b)]
if len(positions)<400:raise SystemExit(f"Unexpected Turkish entries: {len(positions)}")
def key(b):
 line=b[0];m=re.search(r'tvg-name="([^"]*)"',line)
 name=(m.group(1) if m else line.split(",")[-1]).strip()
 name=name.upper().replace("İ","I").replace("İ","I").replace("Ş","S").replace("Ğ","G").replace("Ü","U").replace("Ö","O").replace("Ç","C")
 return (unicodedata.normalize("NFKD",name),line)
sorted_blocks=sorted((blocks[i] for i in positions),key=key)
for i,b in zip(positions,sorted_blocks):blocks[i]=b
out="".join(prefix)+"".join("".join(b) for b in blocks)
if out.count("#EXTINF:")!=s.count("#EXTINF:"):raise SystemExit("Count changed")
if sorted("".join(b) for b in blocks)!=sorted("".join(b) for b in [lines[k:next((q for q in range(k+1,len(lines)) if lines[q].startswith("#EXTINF:")),len(lines))] for k in range(len(lines)) if lines[k].startswith("#EXTINF:")]):raise SystemExit("Content changed")
p.write_text(out,encoding="utf-8")
print(f"Sorted {len(positions)} Turkish channels alphabetically; total {len(blocks)} unchanged")
