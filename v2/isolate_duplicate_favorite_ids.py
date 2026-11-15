#!/usr/bin/env python3
"""Audit and generate an isolated M3U copy with unique tvg-id per stream entry.

Never rewrites the source or protected playlists. This does not modify the
favorites database of an external IPTV player.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ID = re.compile(r'(?<![\\w-])tvg-id="([^"]*)"')

def entries(lines):
    result = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF:"):
            url = next((x.strip() for x in lines[i+1:] if x.strip() and not x.startswith("#")), "")
            if url:
                m = ID.search(line)
                result.append((i, m.group(1) if m else "", url))
    return result

def isolate(source):
    lines = source.splitlines(keepends=True)
    found = entries(lines)
    counts = Counter(ident for _, ident, _ in found if ident)
    duplicates = {k:v for k,v in counts.items() if v > 1}
    used = {ident for _, ident, _ in found if ident}
    seen_url = defaultdict(int)
    changed = []
    for line_no, ident, url in found:
        if not ident or counts[ident] <= 1:
            continue
        seen_url[url] += 1
        seed = f"{ident}\\0{url}\\0{seen_url[url]}".encode()
        suffix = hashlib.sha256(seed).hexdigest()[:20]
        new_id = f"v2-{suffix}"
        while new_id in used:
            suffix = hashlib.sha256((new_id+url).encode()).hexdigest()[:20]
            new_id = f"v2-{suffix}"
        used.add(new_id)
        lines[line_no] = ID.sub(lambda m: f'tvg-id="{new_id}"', lines[line_no], count=1)
        changed.append({"line": line_no+1, "old_id": ident, "new_id": new_id})
    return "".join(lines), {"entries":len(found), "duplicate_id_groups":len(duplicates),
                              "duplicate_entries":sum(duplicates.values()),
                              "rewritten":len(changed), "changes":changed}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    if a.source.resolve()==a.output.resolve():
        p.error("Source must never be overwritten")
    for dest in (a.output,a.report):
        if dest.exists() or dest.is_symlink():
            p.error(f"Refusing overwrite: {dest}")
    raw=a.source.read_text(encoding="utf-8-sig")
    result,report=isolate(raw)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:f.write(result)
    with a.report.open("x",encoding="utf-8") as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!="changes"}))

if __name__=="__main__":
    main()
