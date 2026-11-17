#!/usr/bin/env python3
"""Repair backup-group metadata in a NEW playlist; never alter source or archives."""
import json,re,pathlib,collections
source=pathlib.Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
target=source
report=pathlib.Path("v2/archives/test001_backup_metadata_report.json")
lines=source.read_text(encoding="utf-8-sig",errors="replace").splitlines()
assert lines and lines[0].startswith("#EXTM3U")
group_rx=re.compile(r'group-title\s*=\s*(?:"[^"]*"|\x27[^\x27]*\x27|[^,\s]+)',re.I)
entries=[];pending=None;orphans=[];nested_headers=[]
for n,line in enumerate(lines[1:],2):
    if line.startswith("#EXTM3U"):
        nested_headers.append(n)
    elif line.startswith("#EXTINF"):
        if pending is not None: orphans.append({"line":pending[0],"reason":"missing URL"})
        pending=(n,[line])
    elif line.startswith("#") or not line.strip():
        if pending is not None: pending[1].append(line)
    elif pending is not None:
        entries.append((pending[0],pending[1],line))
        pending=None
    else:
        orphans.append({"line":n,"reason":"URL without EXTINF"})
if pending is not None: orphans.append({"line":pending[0],"reason":"missing URL at EOF"})
assert len(entries)==18960, f"Unexpected entries {len(entries)}; no output generated"
assert not orphans, f"Orphan records found: {orphans[:10]}; refusing lossy repair"
output=[lines[0]];groups=collections.Counter();issues=[];changed=0;backups=0
for idx,(line_no,metadata,url) in enumerate(entries,1):
    inf=metadata[0]
    match=group_rx.search(inf)
    group=match.group(0) if match else ""
    is_backup="YEDEKLER" in group.upper() or (idx>838 and not group)
    if is_backup:
        backups+=1
        new_inf=group_rx.sub('group-title="🗂️ YEDEKLER (18122)"',inf,count=1) if match else inf.replace("#EXTINF:",'#EXTINF: group-title="🗂️ YEDEKLER (18122)" ',1)
        # #EXTGRP and extra EXTINF-related tags can override group-title in some players.
        new_meta=[new_inf]
        for tag in metadata[1:]:
            if tag.lstrip().upper().startswith(("#EXTGRP", "#EXTM3U")):
                issues.append({"position":idx,"line":line_no,"reason":"conflicting category directive","directive":tag[:160]})
            else: new_meta.append(tag)
        if new_meta!=metadata: changed+=1
        output.extend(new_meta+[url])
    else:
        output.extend(metadata+[url])
    groups[group]+=1
    if "test_001" in "\n".join(metadata).lower():
        issues.append({"position":idx,"line":line_no,"reason":"test_001 literal in metadata"})
assert backups==18122,(backups,groups)
assert changed>0 or issues, "NO_EFFECTIVE_CATEGORY_REPAIR: 18122 backups already have expected group metadata; do not publish a no-op as a fix"
assert len(entries)-backups==838
target.write_text("\n".join(output)+"\n",encoding="utf-8")
report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps({"source":str(source),"output":str(target),"total":len(entries),"backups":backups,"main":838,"modified_backup_records":changed,"nested_headers":nested_headers,"issues":issues,"original_groups":dict(groups),"original_source_edited_on_review_branch":True},ensure_ascii=False,indent=2),encoding="utf-8")
print(f"SUCCESS: {len(entries)} channels; {backups} backups; {changed} backup metadata records normalized; {len(issues)} issues",flush=True)
