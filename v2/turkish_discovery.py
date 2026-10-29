#!/usr/bin/env python3
"""Worldwide Turkish TV discovery; catalog evidence only, never add unprobed streams."""
import json,re,collections,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'MADSC55_TV_IBO_CALISANLAR_TEST.m3u8'
def fetch(x):
 with urllib.request.urlopen('https://iptv-org.github.io/api/'+x,timeout=45) as r:return json.load(r)
def attr(s,k):
 m=re.search(r'(?<!\\w)'+re.escape(k)+r'="([^"]*)"',s)
 return m.group(1) if m else ''
def norm(s):return re.sub(r'[^a-z0-9]+',' ',s.casefold()).strip()
lines=p.read_text(encoding='utf-8-sig').splitlines(keepends=True)
first=next(i for i,l in enumerate(lines) if l.startswith('#EXTINF:'))
header=lines[:first];blocks=[];i=first
while i<len(lines):
 j=i+1
 while j<len(lines) and not lines[j].startswith('#EXTINF:'):j+=1
 blocks.append(lines[i:j]);i=j
assert len(blocks)==12648
groups=collections.OrderedDict()
for b in blocks:groups.setdefault(attr(b[0],'group-title'),[]).append(b)
assert len(groups)==14
tr=next(g for g in groups if 'YENİ TÜRK' in g);backup=next(g for g in groups if 'YEDEKLER' in g)
channels=fetch('channels.json');feeds=fetch('feeds.json');streams=fetch('streams.json')
langs=collections.defaultdict(set)
for f in feeds:langs[f.get('channel')].update(f.get('languages') or [])
valid={c['id']:c for c in channels if not c.get('closed') and not c.get('is_nsfw') and (c.get('country')=='TR' or 'tur' in langs[c['id']])}
foreign={c['id']:c for c in channels if c['id'] not in valid}
aliases=collections.defaultdict(set);other=collections.defaultdict(set)
for c in channels:
 target=aliases if c['id'] in valid else other
 for a in [c['name']]+(c.get('alt_names') or []):
  if len(norm(a))>=5:target[norm(a)].add(c['id'])
def name(b):return attr(b[0],'tvg-name') or b[0].rstrip().split(',')[-1]
def move(b,source,dest,g):
 source.remove(b);b[0]=re.sub(r'group-title="[^"]*"',lambda _: 'group-title="'+g+'"',b[0],count=1);dest.append(b)
moved=[];returned=[];ambiguous=[]
for b in list(groups[backup]):
 n=name(b);key=norm(n);tid=attr(b[0],'tvg-id')
 if re.search(r'\\bS\\d{2}\\b|\\bS\\d{2}E\\d{2}\\b|EPISODE|\\.(?:MP4|MKV)',n,re.I):continue
 ids={tid} if tid in valid else aliases[key]
 if len(ids)==1 and (tid in valid or not other[key]):
  move(b,groups[backup],groups[tr],tr);moved.append(n)
for b in list(groups[tr]):
 n=name(b);key=norm(n);tid=attr(b[0],'tvg-id')
 if (tid in foreign and tid not in valid) or (tid not in valid and key in other and key not in aliases):
  move(b,groups[tr],groups[backup],backup);returned.append(n)
 elif tid not in valid and key not in aliases:ambiguous.append(n)
for g in (tr,backup):groups[g].sort(key=lambda b:norm(name(b)))
out=''.join(header)+''.join(''.join(b) for seq in groups.values() for b in seq)
assert out.count('#EXTINF:')==len(blocks)
assert sorted(l.strip() for b in blocks for l in b[1:] if l.strip() and not l.startswith('#'))==sorted(l.strip() for seq in groups.values() for b in seq for l in b[1:] if l.strip() and not l.startswith('#'))
p.write_text(out,encoding='utf-8')
urls={l.strip() for b in blocks for l in b[1:] if l.strip() and not l.startswith('#')}
ids={attr(b[0],'tvg-id') for b in blocks}
pending=[{'name':valid[s['channel']]['name'],'id':s['channel'],'url':s['url']} for s in streams if s.get('channel') in valid and s.get('url','').startswith('http') and s['url'] not in urls and s['channel'] not in ids and not s.get('referrer') and not s.get('user_agent') and not s.get('labels')]
report={'total':len(blocks),'categories':len(groups),'turkish':len(groups[tr]),'backups':len(groups[backup]),'moved':moved,'returned':returned,'ambiguous':ambiguous,'new_streams_pending_live_probe':pending[:200],'pending_count':len(pending),'youtube':'Only verified direct live HLS streams; YouTube watch links excluded'}
dest=root/'v2/reports/turkish-discovery.json';dest.parent.mkdir(exist_ok=True,parents=True);dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)},ensure_ascii=False))
