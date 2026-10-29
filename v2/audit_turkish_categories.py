#!/usr/bin/env python3
"""Conservative Turkish-channel classification, preserving all streams and metadata."""
import re,json,collections,unicodedata
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'MADSC55_TV_IBO_CALISANLAR_TEST.m3u8'
raw=p.read_text(encoding='utf-8-sig')
lines=raw.splitlines(keepends=True)
first=next(i for i,l in enumerate(lines) if l.startswith('#EXTINF:'))
header=lines[:first]; blocks=[];i=first
while i<len(lines):
 if not lines[i].startswith('#EXTINF:'): raise ValueError('Unexpected playlist layout')
 j=i+1
 while j<len(lines) and not lines[j].startswith('#EXTINF:'): j+=1
 blocks.append(lines[i:j]);i=j
def attr(b,k):
 m=re.search(r'(?<!\w)'+re.escape(k)+r'="([^"]*)"',b[0])
 return m.group(1) if m else ''
def name(b):return attr(b,'tvg-name') or b[0].rstrip().split(',')[-1]
def group(b):return attr(b,'group-title')
def normalized(s):
 return ''.join(c for c in unicodedata.normalize('NFKD',s.upper().replace('İ','I').replace('ı','I')) if not unicodedata.combining(c))
def is_vod(s):
 return bool(re.search(r'\bS\d{1,2}E\d{1,3}\b|\bS\d{2}\b.*\bS\d{2}E|\bWEB[- .]?DL\b|\b(EPISODE|SEASON)\b|\.(MP4|MKV)\b',s,re.I))
# Explicit Turkish broadcasting markers only; avoid assuming that a Turkish word means Turkish TV.
known=re.compile(r'\b(TRT|ATV|KANAL D|SHOW TV|STAR TV|HABERTURK|HABER TURK|CNN TURK|NTV|TV8|TV 8|TV100|TGRT|BEYAZ TV|ULKE TV|KRT|TELE ?1|TEVE2|DMAX|MINIKA|A HABER|A PARA|A SPOR|ACUN ILICALI|FLASH HABER|HALK TV|SOZCU TV|360 TV|TVNET|TV NET|YABAN TV|DREAM TURK|POWER TURK|KRAL POP|KRAL TV|CINE5|KANAL 7|EURO D|EUROSTAR|TRT TURK)\b',re.I)
def candidate(b):
 n=normalized(name(b)); tid=attr(b,'tvg-id')
 if is_vod(n) or re.search(r'\\bS\\d{2}\\s+E\\d{2}\\b|\\bS\\d{2}\\s+.*\\bE\\d{2}\\b|[- ]TR S\\d{2}\\b',n):return False
 if re.search(r'\.tr(?:@|$)',tid,re.I):return True
 if re.search(r'\b(?:GERMANY|ITALY|BANGLADESH|BRAZIL|CANADA|MALDIVES)\b',n):return False
 if re.search(r'\bTR\b
 return bool(re.search(r'^(?:TRT(?:\\s|$)|CNN TURK\\b|HABER TURK\\b|HABERTURK\\b|BEYAZ TV\\b|TGRT\\b|KANAL 7\\b|SHOW TV\\b|STAR TV\\b|A HABER\\b|A PARA\\b|A SPOR\\b|DREAM TURK\\b|TV100\\b)',n))
groups=collections.OrderedDict()
for b in blocks:groups.setdefault(group(b),[]).append(b)
tr=next((g for g in groups if 'YENİ TÜRK' in g),None)
backup=next((g for g in groups if 'YEDEKLER' in g),None)
if not tr or not backup or len(groups)!=14:raise ValueError('Missing expected categories')
before=collections.Counter({g:len(v) for g,v in groups.items()})
# Never remove Turkish-category channels automatically: flag ambiguous cases for human review.
move=[]; review=[]
# Undo the prior overly broad automatic batch before applying strict country evidence.
prior=root/'v2/reports/turkish-category-audit.json'
if prior.exists():
 old=json.loads(prior.read_text(encoding='utf-8'))
 counts=collections.Counter(old.get('moved_names',[]))
 for b in list(groups[tr]):
  n=name(b)
  if counts[n]>0:
   counts[n]-=1;groups[tr].remove(b)
   b[0]=re.sub(r'group-title="[^"]*"',lambda _: 'group-title="'+backup+'"',b[0],count=1)
   groups[backup].append(b)
 if any(counts.values()):raise ValueError('Could not fully reverse previous unsafe batch')
for b in list(groups[backup]):
 if candidate(b):move.append(b)
for b in groups[tr]:
 if not candidate(b):review.append(name(b))
for b in move:
 groups[backup].remove(b)
 b[0]=re.sub(r'group-title="[^"]*"',lambda _: 'group-title="'+tr+'"',b[0],count=1)
 groups[tr].append(b)
# Remove only the exact test-tube symbol, from both display and tvg-name.
cleaned=0
for g in (tr,backup):
 for b in groups[g]:
  if '🧪' in b[0]:
   b[0]=b[0].replace('🧪','');cleaned+=1
def key(b):return normalized(name(b))
for g in (tr,backup):groups[g].sort(key=key)
out=''.join(header)+''.join(''.join(b) for seq in groups.values() for b in seq)
assert out.count('#EXTINF:')==len(blocks)==12648
assert len(groups)==14
assert len(groups[tr])+len(groups[backup])==before[tr]+before[backup]
assert sorted(l for b in blocks for l in b[1:] if l.strip() and not l.startswith('#'))==sorted(l for seq in groups.values() for b in seq for l in b[1:] if l.strip() and not l.startswith('#'))
p.write_text(out,encoding='utf-8')
report={'total':len(blocks),'categories':len(groups),'before':{tr:before[tr],backup:before[backup]},'after':{tr:len(groups[tr]),backup:len(groups[backup])},'moved_to_turkish':len(move),'moved_names':[name(b) for b in move],'ambiguous_in_turkish_needs_review':review,'test_marked_entries_cleaned':cleaned,'policy':'Conservative automated moves; ambiguous Turkish entries remain for review.'}
dest=root/'v2/reports/turkish-category-audit.json';dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'
',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('moved_names','ambiguous_in_turkish_needs_review')},ensure_ascii=False))
,n):return True
 return bool(re.search(r'^(?:TRT(?:\\s|$)|CNN TURK\\b|HABER TURK\\b|HABERTURK\\b|BEYAZ TV\\b|TGRT\\b|KANAL 7\\b|SHOW TV\\b|STAR TV\\b|A HABER\\b|A PARA\\b|A SPOR\\b|DREAM TURK\\b|TV100\\b)',n))
groups=collections.OrderedDict()
for b in blocks:groups.setdefault(group(b),[]).append(b)
tr=next((g for g in groups if 'YENİ TÜRK' in g),None)
backup=next((g for g in groups if 'YEDEKLER' in g),None)
if not tr or not backup or len(groups)!=14:raise ValueError('Missing expected categories')
before=collections.Counter({g:len(v) for g,v in groups.items()})
# Never remove Turkish-category channels automatically: flag ambiguous cases for human review.
move=[]; review=[]
# Undo the prior overly broad automatic batch before applying strict country evidence.
prior=root/'v2/reports/turkish-category-audit.json'
if prior.exists():
 old=json.loads(prior.read_text(encoding='utf-8'))
 counts=collections.Counter(old.get('moved_names',[]))
 for b in list(groups[tr]):
  n=name(b)
  if counts[n]>0:
   counts[n]-=1;groups[tr].remove(b)
   b[0]=re.sub(r'group-title="[^"]*"',lambda _: 'group-title="'+backup+'"',b[0],count=1)
   groups[backup].append(b)
 if any(counts.values()):raise ValueError('Could not fully reverse previous unsafe batch')
for b in list(groups[backup]):
 if candidate(b):move.append(b)
for b in groups[tr]:
 if not candidate(b):review.append(name(b))
for b in move:
 groups[backup].remove(b)
 b[0]=re.sub(r'group-title="[^"]*"',lambda _: 'group-title="'+tr+'"',b[0],count=1)
 groups[tr].append(b)
# Remove only the exact test-tube symbol, from both display and tvg-name.
cleaned=0
for g in (tr,backup):
 for b in groups[g]:
  if '🧪' in b[0]:
   b[0]=b[0].replace('🧪','');cleaned+=1
def key(b):return normalized(name(b))
for g in (tr,backup):groups[g].sort(key=key)
out=''.join(header)+''.join(''.join(b) for seq in groups.values() for b in seq)
assert out.count('#EXTINF:')==len(blocks)==12648
assert len(groups)==14
assert len(groups[tr])+len(groups[backup])==before[tr]+before[backup]
assert sorted(l for b in blocks for l in b[1:] if l.strip() and not l.startswith('#'))==sorted(l for seq in groups.values() for b in seq for l in b[1:] if l.strip() and not l.startswith('#'))
p.write_text(out,encoding='utf-8')
report={'total':len(blocks),'categories':len(groups),'before':{tr:before[tr],backup:before[backup]},'after':{tr:len(groups[tr]),backup:len(groups[backup])},'moved_to_turkish':len(move),'moved_names':[name(b) for b in move],'ambiguous_in_turkish_needs_review':review,'test_marked_entries_cleaned':cleaned,'policy':'Conservative automated moves; ambiguous Turkish entries remain for review.'}
dest=root/'v2/reports/turkish-category-audit.json';dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'
',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('moved_names','ambiguous_in_turkish_needs_review')},ensure_ascii=False))
