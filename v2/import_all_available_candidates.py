#!/usr/bin/env python3
"""Add every accessible scan/legacy candidate to YEDEKLER, excluding archive and existing URLs."""
from pathlib import Path
import argparse, hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
PLAY=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
TEST=ROOT/"v2/test_playlist_invariants.py"
MANIFEST=ROOT/"v2/ibo_authorized_change.json"
ARCHIVE=ROOT/"v2/arsiv/yabanci_kanallar_2026-11-16_2881.m3u8"
GROUP=re.compile(r'group-title="[^"]*"')
def blocks(text):
    header=[]; records=[]
    for line in text.splitlines(keepends=True):
        if line.startswith("#EXTINF:"): records.append([line])
        elif records: records[-1].append(line)
        else: header.append(line)
    return "".join(header),["".join(x) for x in records]
def url(b):
    return next((x.strip() for x in b.splitlines()[1:] if x.strip().startswith(("https://","http://"))),None)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scan-dir",type=Path,required=True)
    args=parser.parse_args()
    original=PLAY.read_bytes(); header,current=blocks(original.decode("utf-8-sig"))
    protected=[x for x in current if "YEDEKLER" not in x.splitlines()[0]]
    existing=[x for x in current if "YEDEKLER" in x.splitlines()[0]]
    if len(protected)!=838 or len(existing)!=1285 or current!=protected+existing:
        raise SystemExit("Protected playlist or existing backups changed")
    _,archived=blocks(ARCHIVE.read_text(encoding="utf-8-sig"))
    seen={u for x in current+archived if (u:=url(x))}
    files=sorted(args.scan_dir.glob("IBO_YENI_ADAYLAR*.m3u8"))
    files+=sorted((ROOT/"v2/arsiv").glob("eski_sistem_aktarim_adaylari_2026-11-16_parca_*.m3u8"))
    if len(files)<7: raise SystemExit(f"Expected 3 scan and 4 legacy sources, got {len(files)}")
    added=[]; per_file={}
    for path in files:
        _,candidates=blocks(path.read_text(encoding="utf-8-sig"))
        count=0
        for b in candidates:
            u=url(b)
            if not u or u in seen:continue
            if not GROUP.search(b.splitlines()[0]):continue
            seen.add(u);added.append(b);count+=1
        per_file[path.name]=count
    if not added:raise SystemExit("No new unique candidates; refusing empty PR")
    new_count=len(existing)+len(added)
    label=f'group-title="🗂️ YEDEKLER ({new_count})"'
    def rewrite(b):
        lines=b.splitlines(keepends=True)
        lines[0]=GROUP.sub(lambda _:label,lines[0],count=1)
        return "".join(lines)
    result=header+"".join(protected)+"".join(map(rewrite,existing+added))
    _,after=blocks(result)
    if after[:838]!=protected or len(after)!=838+new_count:
        raise SystemExit("Protected channel invariant failed")
    if [url(x) for x in after[838:838+1285]] != [url(x) for x in existing]:
        raise SystemExit("Existing backups changed")
    if len({url(x) for x in after[838:]})!=new_count:
        raise SystemExit("Duplicate backup URL")
    tests=TEST.read_text(encoding="utf-8")
    if tests.count("2123")!=1 or tests.count("1285")<3:
        raise SystemExit("Unexpected invariant test layout")
    tests=tests.replace("2123",str(838+new_count)).replace("1285",str(new_count))
    manifest={"base_sha256":hashlib.sha256(original).hexdigest(),
      "result_sha256":hashlib.sha256(result.encode("utf-8")).hexdigest(),
      "operation":"category",
      "request":"User authorized import of all accessible scan and legacy candidates excluding archived, existing and protected channels; do not change 838 protected entries.",
      "channels":[f"{len(added)} distinct scan and legacy URL candidates imported for testing; AV status not assumed"]}
    PLAY.write_bytes(result.encode("utf-8"));TEST.write_text(tests,encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"new":len(added),"backups":new_count,"sources":per_file},ensure_ascii=False))
if __name__=="__main__":main()
