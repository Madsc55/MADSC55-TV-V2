#!/usr/bin/env python3
"""Alphabetize backups and safely enrich missing logos from iptv-org channel/logo catalog."""
import json,re,unicodedata,urllib.request,collections
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
lines=p.read_text(encoding="utf-8-sig").splitlines(keepends=True)
start=next(i for i,x in enumerate(lines) if x.startswith("#EXTINF:"))
head=lines[:start];blocks=[];i=start
while i<len(lines):
 j=i+1
 while j<len(lines) and not lines[j].startswith("#EXTINF:"):j+=1
 blocks.append(lines[i:j]);i=j
def group(b):return re.search(r'group-title="([^"]+)"',b[0]).group(1)
def name(b):
 m=re.search(r'tvg-name="([^"]*)"',b[0])
 return m.group(1) if m else b[0].split(",")[-1].strip()
def norm(s):
 s=s.upper().translate(str.maketrans("ÇĞİÖŞÜ","CGIOSU"))
 return ''.join(c for c in unicodedata.normalize("NFKD",s) if not unicodedata.combining(c))
def clean(s):
 s=re.sub(r'\s*\((?:\d+[PI]|\d+K)\)\s*',' ',s,flags=re.I)
 s=re.sub(r'\s*\[(?:GEO-BLOCKED|NOT 24/7|NSFW)\]\s*',' ',s,flags=re.I)
 return re.sub(r'\s+',' ',norm(s)).strip()
def fetch(kind):
 req=urllib.request.Request('https://iptv-org.github.io/api/'+kind+'.json',headers={'User-Agent':'MADSC55-TV-V2-Logo-Audit/1.0'})
 with urllib.request.urlopen(req,timeout=45) as f:return json.load(f)
channels=fetch('channels');logos=fetch('logos')
byid={c['id']:c for c in channels};byname=collections.defaultdict(set)
for c in channels:
 for n in [c['name']]+(c.get('alt_names') or []):
  if n:byname[clean(n)].add(c['id'])
logo_byid=collections.defaultdict(list)
for logo in logos:
 if logo.get('in_use') and str(logo.get('url','')).startswith('https://'):logo_byid[logo['channel']].append(logo)
for k in logo_byid:logo_byid[k].sort(key=lambda x:(x.get('feed') is not None,x.get('format') not in ('PNG','JPEG','WebP'),-(x.get('width') or 0)))
count=collections.Counter();ambiguous=collections.Counter();missing=collections.Counter()
for b in blocks:
 g=group(b)
 if 'YEDEKLER' not in g and 'YENİ TÜRK' not in g:continue
 count[g+':total']+=1
 if re.search(r'tvg-logo="https?://[^"]+"',b[0]):continue
 missing[g]+=1
 idmatch=re.search(r'tvg-id="([^"]+)"',b[0]);channel_id=idmatch.group(1) if idmatch else ''
 if channel_id not in logo_byid:
  candidates=byname.get(clean(name(b)),set())
  if 'YENİ TÜRK' in g:
   candidates={x for x in candidates if byid[x].get('country') in ('TR','CY') or x.lower().endswith(('.tr','.cy'))}
  if len(candidates)!=1:
   ambiguous[g]+=1;continue
  channel_id=next(iter(candidates))
 if not logo_byid.get(channel_id):continue
 logo=logo_byid[channel_id][0]['url']
 if 'tvg-logo="' in b[0]:b[0]=re.sub(r'tvg-logo="[^"]*"',lambda _:f'tvg-logo="{logo}"',b[0],count=1)
 else:b[0]=b[0].replace(' group-title=',f' tvg-logo="{logo}" group-title=',1)
 count[g+':added']+=1
groups=collections.OrderedDict()
for b in blocks:groups.setdefault(group(b),[]).append(b)
def key(b):return (clean(name(b)),name(b))
for g in groups:
 if 'YEDEKLER' in g or 'YENİ TÜRK' in g:groups[g].sort(key=key)
out=''.join(head)+''.join(''.join(b) for bs in groups.values() for b in bs)
assert out.count('#EXTINF:')==len(blocks)
assert len(groups)==14
p.write_text(out,encoding='utf-8')
print('LOGO_AUDIT',json.dumps({'stats':dict(count),'missing_before':dict(missing),'unmatched_or_ambiguous':dict(ambiguous),'total':len(blocks)},ensure_ascii=False))
