#!/usr/bin/env python3
"""Apply explicit user-approved backup selections to a STAGED playlist only.

Manifest example:
{"approved": true, "placements": [{"backup_name": "EXACT NAME", "target": "HABER"}]}
Never probes streams or assumes a channel works. A manifest records an explicit
decision; the caller is responsible for real AV evidence before approval.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

TARGETS = ("FAVORİLER", "ULUSAL-HEPSİ", "HABER", "SPOR", "SİNEMA", "BELGESEL", "ÇOCUK", "YEREL")
def split(raw):
    i = raw.index("#EXTINF:")
    return raw[:i], re.findall(r"^#EXTINF:[\s\S]*?(?=^#EXTINF:|\Z)", raw[i:], re.M)
def meta(block):
    line = block.splitlines()[0]
    return line.rsplit(",",1)[-1].strip(), re.search(r'group-title="([^"]+)"',line).group(1)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--report",required=True)
    args=p.parse_args()
    original=Path(args.input).read_bytes()
    header,records=split(original.decode("utf-8-sig"))
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("approved") is not True or not isinstance(manifest.get("placements"),list) or not manifest["placements"]:
        raise SystemExit("Explicit approval and nonempty placements required")
    if len(records)!=18912 or sum("YEDEKLER" in meta(b)[1] for b in records)!=18074:
        raise SystemExit("Unexpected protected baseline")
    backup=collections.defaultdict(list)
    for b in records:
        name,group=meta(b)
        if "YEDEKLER" in group: backup[name].append(b)
    additions=[]
    for item in manifest["placements"]:
        name=item.get("backup_name")
        target=item.get("target")
        if target not in TARGETS or not isinstance(name,str) or len(backup[name])!=1:
            raise SystemExit("Ambiguous/missing backup or unsupported category: "+str(item))
        if item.get("av_verified") is not True:
            raise SystemExit("Real AV confirmation required for "+name)
        b=backup[name][0]
        matches=[(i,meta(r)[1]) for i,r in enumerate(records) if meta(r)[1].split(" (")[0].endswith(target)]
        if not matches:
            raise SystemExit("Target category not present: "+target)
        indices=[i for i,_ in matches]
        group=matches[0][1]
        if any(g!=group for _,g in matches):
            raise SystemExit("Ambiguous target category")
        prefix=re.escape(group.rsplit(" (",1)[0])
        old_count=int(re.search(r"\((\d+)\)$",group).group(1))
        new_group=group.rsplit(" (",1)[0]+" ("+str(old_count+1)+")"
        line=b.splitlines()[0]
        bcopy=b.replace(line,line.replace('group-title="'+meta(b)[1]+'"','group-title="'+new_group+'"'),1)
        additions.append((target,bcopy))
    if len({(x["backup_name"],x["target"]) for x in manifest["placements"]})!=len(additions):
        raise SystemExit("Duplicate placement")
    output=list(records)
    for target,bcopy in additions:
        idx=[i for i,r in enumerate(output) if meta(r)[1].split(" (")[0].endswith(target)]
        if not idx: raise SystemExit("Missing target")
        oldgroup=meta(output[idx[0]])[1]
        count=int(re.search(r"\((\d+)\)$",oldgroup).group(1))
        newgroup=oldgroup.rsplit(" (",1)[0]+" ("+str(count+1)+")"
        for i in idx:
            output[i]=output[i].replace('group-title="'+oldgroup+'"','group-title="'+newgroup+'"',1)
        bcopy=re.sub(r'group-title="[^"]+"','group-title="'+newgroup+'"',bcopy,count=1)
        output.insert(idx[-1]+1,bcopy)
    if [b for b in output if "YEDEKLER" in meta(b)[1]] != [b for b in records if "YEDEKLER" in meta(b)[1]]:
        raise SystemExit("Backup inventory modified")
    if len(output)!=len(records)+len(additions):
        raise SystemExit("Record count mismatch")
    result=(header+"".join(output)).encode("utf-8")
    for f in (args.output,args.report):
        if Path(f).exists(): raise SystemExit("Refusing to overwrite: "+f)
    Path(args.output).write_bytes(result)
    report={"status":"STAGED_ONLY_NOT_PUBLISHED","approved_placements":len(additions),"original_records":len(records),"staged_records":len(output),"backup_records_unchanged":18074,"source_sha256":hashlib.sha256(original).hexdigest(),"staged_sha256":hashlib.sha256(result).hexdigest(),"note":"av_verified is a user-supplied assertion; not independent AV proof"}
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
