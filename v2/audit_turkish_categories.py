#!/usr/bin/env python3
"""Safely reverse previously misclassified channels; do not guess channel nationality."""
import re,collections,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'MADSC55_TV_IBO_CALISANLAR_TEST.m3u8'
lines=p.read_text(encoding='utf-8-sig').splitlines(keepends=True)
first=next(i for i,l in enumerate(lines) if l.startswith('#EXTINF:'))
header=lines[:first];blocks=[];i=first
while i<len(lines):
 if not lines[i].startswith('#EXTINF:'):raise ValueError('Malformed M3U')
 j=i+1
 while j<len(lines) and not lines[j].startswith('#EXTINF:'):j+=1
 blocks.append(lines[i:j]);i=j
def attr(b,k):
 m=re.search(r'(?<!\w)'+re.escape(k)+r'="([^"]*)"',b[0]);return m.group(1) if m else ''
def name(b):return attr(b,'tvg-name') or b[0].rstrip().split(',')[-1]
def group(b):return attr(b,'group-title')
groups=collections.OrderedDict()
for b in blocks:groups.setdefault(group(b),[]).append(b)
tr=next(g for g in groups if 'YENİ TÜRK' in g);backup=next(g for g in groups if 'YEDEKLER' in g)
assert len(groups)==14 and len(blocks)==12648
prior=root/'v2/reports/turkish-category-audit.json'
old=json.loads(prior.read_text(encoding='utf-8'))
counts=collections.Counter(old['moved_names']);reverted=[]
for b in list(groups[tr]):
 n=name(b)
 if counts[n]:
  counts[n]-=1;groups[tr].remove(b)
  b[0]=re.sub(r'group-title="[^"]*"',lambda m:'group-title="'+backup+'"',b[0],count=1)
  groups[backup].append(b);reverted.append(n)
if any(counts.values()):raise ValueError('Prior moved entries not fully found; refusing write')
cleaned=0
for g in (tr,backup):
 for b in groups[g]:
  if '🧪' in b[0]:b[0]=b[0].replace('🧪','');cleaned+=1
for g in (tr,backup):groups[g].sort(key=lambda b:name(b).casefold())
out=''.join(header)+''.join(''.join(b) for seq in groups.values() for b in seq)
assert out.count('#EXTINF:')==12648
assert len(groups[tr])==494 and len(groups[backup])==11316
assert sorted(l for b in blocks for l in b[1:] if l.strip() and not l.startswith('#'))==sorted(l for seq in groups.values() for b in seq for l in b[1:] if l.strip() and not l.startswith('#'))
p.write_text(out,encoding='utf-8')
report={'total':12648,'categories':14,'reverted_unsafe_moves':len(reverted),'test_symbols_cleaned':cleaned,'turkish':len(groups[tr]),'backups':len(groups[backup]),'pending':'Independent catalog-based Turkish channel and YouTube live validation'}
dest=root/'v2/reports/turkish-category-safe-recovery.json';dest.parent.mkdir(exist_ok=True,parents=True);dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
