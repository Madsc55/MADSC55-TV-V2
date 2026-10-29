#!/usr/bin/env python3
"""Reversible category rollback; preserve all stream data in an archive."""
from pathlib import Path
import json,re,hashlib,datetime
root=Path(__file__).resolve().parents[1]
playlist=root/'MADSC55_TV_IBO_CALISANLAR_TEST.m3u8'
raw=playlist.read_text(encoding='utf-8')
lines=raw.splitlines(keepends=True)
header=[];blocks=[];current=None
for line in lines:
 if line.startswith('#EXTINF:'):
  if current:blocks.append(current)
  current=[line]
 elif current is None:header.append(line)
 else:current.append(line)
if current:blocks.append(current)
assert len(blocks)>=12000, 'Unexpectedly small playlist: refusing rollback'
def group(b):
 m=re.search(r'group-title="([^"]*)"',b[0])
 return m.group(1) if m else ''
def name(b):
 return b[0].split(',')[-1].strip().upper()
def permanent(b):
 n=name(b)
 return ('TRT 1' in n and '1440P' in n) or ('DHA CANLI' in n and '720P' in n)
backup=[b for b in blocks if 'YEDEKLER' in group(b)]
newturk=[b for b in blocks if 'YENİ TÜRK' in group(b)]
assert len(backup)>10000 and len(newturk)>100, 'Unexpected category layout: refusing rollback'
# Do not alter FAVORILER, ULUSAL-HEPSI, or any other established category.
archive=root/'v2/archives'
archive.mkdir(parents=True,exist_ok=True)
removed=[b for b in blocks if ('YEDEKLER' in group(b) and not permanent(b)) or 'YENİ TÜRK' in group(b)]
keep=[b for b in blocks if b not in removed]
assert len(keep)+len(removed)==len(blocks)
import copy
for label in ('TRT 1','DHA CANLI'):
 candidates=[b for b in blocks if label in name(b) and permanent(b)]
 if not candidates: raise RuntimeError('Missing permanent channel: '+label)
 clone=copy.deepcopy(candidates[0])
 clone[0]=re.sub(r'group-title="[^"]+"','group-title="🗂️ YEDEKLER (2)"',clone[0],count=1)
 keep.append(clone)
assert sum('YEDEKLER' in group(b) for b in keep)==2
archive_file=archive/'category-rollback-2026-10-29.m3u8'
archive_file.write_text(''.join(header)+''.join(''.join(b) for b in removed),encoding='utf-8')
# Update group-title count only for the remaining backup category; keep all other categories unchanged.
for b in keep:
 if 'YEDEKLER' in group(b):
  b[0]=re.sub(r'group-title="[^"]+"','group-title="🗂️ YEDEKLER (2)"',b[0],count=1)
playlist.write_text(''.join(header)+''.join(''.join(b) for b in keep),encoding='utf-8')
report={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_entries':len(blocks),'removed_to_archive':len(removed),'remaining_entries':len(keep),'archived_backups':sum('YEDEKLER' in group(b) for b in removed),'archived_new_turk':len(newturk),'permanent_backups_remaining':sum('YEDEKLER' in group(b) for b in keep),'original_sha256':hashlib.sha256(raw.encode()).hexdigest(),'archive_path':str(archive_file.relative_to(root)),'discovery_artifacts':'untouched'}
(root/'v2/reports/category-rollback-2026-10-29.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
