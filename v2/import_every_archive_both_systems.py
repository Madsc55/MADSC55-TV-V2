#!/usr/bin/env python3
"""Union all accessible old/new IPTV playlists and archives into V2 YEDEKLER without deletion."""
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAY=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
TEST=ROOT/"v2/test_playlist_invariants.py"
MANIFEST=ROOT/"v2/ibo_authorized_change.json"
GROUP=re.compile(r'group-title="[^"]*"')
def parse(path):
    try: data=path.read_text(encoding="utf-8-sig",errors="replace")
    except (OSError,UnicodeError):return []
    blocks=[];current=None
    for line in data.splitlines(keepends=True):
        if line.startswith("#EXTINF:"):
            if current:blocks.append("".join(current))
            current=[line]
        elif current is not None:current.append(line)
    if current:blocks.append("".join(current))
    return blocks
def url(b):
    return next((line.strip() for line in b.splitlines()[1:] if line.strip().startswith(("http://","https://"))),None)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--old-repo",type=Path,required=True);ap.add_argument("--scan-dir",type=Path,required=True);args=ap.parse_args()
    original=PLAY.read_bytes();original_text=original.decode("utf-8-sig")
    first=original_text.find("#EXTINF:")
    if first<0:raise SystemExit("No playlist entries")
    header=original_text[:first];records=parse(PLAY)
    protected=[b for b in records if "YEDEKLER" not in b.splitlines()[0]]
    existing=[b for b in records if "YEDEKLER" in b.splitlines()[0]]
    if len(protected)!=838 or len(existing)!=16991 or records!=protected+existing:
        raise SystemExit("Main or backups changed unexpectedly")
    seen={u for b in existing if (u:=url(b))}
    sources=[]
    for base in (args.old_repo,ROOT/"v2/arsiv",args.scan_dir):
        if not base.exists():raise SystemExit(f"Missing source {base}")
        sources.extend(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in (".m3u",".m3u8"))
    # Other V2 playlists, including archived and previous test playlists.
    sources.extend(p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in (".m3u",".m3u8") and p!=PLAY and ".git" not in p.parts)
    sources=sorted(set(sources),key=str)
    if len(sources)<10:raise SystemExit("Too few source playlists")
    added=[];counts={};invalid=0
    # User requested the protected main channels also appear as backup copies.
    # Preserve the original 838 main records byte-for-byte.
    for block in protected:
        u=url(block)
        if u and u not in seen:
            seen.add(u)
            added.append(block)
    counts["protected_main_copies"]=len(added)
    for p in sources:
        n=0
        for block in parse(p):
            u=url(block)
            if not u or not u.startswith(("http://","https://")):invalid+=1;continue
            if u in seen:continue
            if not GROUP.search(block.splitlines()[0]):
                block=block.replace(block.splitlines()[0],block.splitlines()[0].rstrip("\r\n")+' group-title="🗂️ YEDEKLER"\n',1)
            seen.add(u);added.append(block);n+=1
        counts[(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else "old/"+str(p.relative_to(args.old_repo)) if p.is_relative_to(args.old_repo) else "scan/"+str(p.relative_to(args.scan_dir)) if p.is_relative_to(args.scan_dir) else str(p))]=n
    if not added:
        print(json.dumps({"added":0,"backups":len(existing),"source_files":len(sources),"invalid_records":invalid,"status":"already_imported"},ensure_ascii=False))
        return
    total=len(existing)+len(added);label=f'group-title="🗂️ YEDEKLER ({total})"'
    def rewrite(block):
        lines=block.splitlines(keepends=True)
        if GROUP.search(lines[0]):
            lines[0]=GROUP.sub(lambda _:label,lines[0],count=1)
        else:
            lines[0]=lines[0].rstrip("\r\n")+" "+label+"\n"
        return "".join(lines)
    result=header+"".join(protected)+"".join(map(rewrite,existing+added))
    if len(parse_text(result))!=838+total:raise SystemExit("Output entry count mismatch")
    if [url(b) for b in parse_text(result)[838:838+16991]] != [url(b) for b in existing]:
        raise SystemExit("Existing backup order changed")
    tests=TEST.read_text(encoding="utf-8")
    if tests.count("17829")!=1 or tests.count("16991")<3:raise SystemExit("Unexpected test baseline")
    tests=tests.replace("17829",str(838+total)).replace("16991",str(total))
    manifest={"base_sha256":hashlib.sha256(original).hexdigest(),"result_sha256":hashlib.sha256(result.encode()).hexdigest(),"operation":"category","request":"User authorized all old and V2 playlists including all archives in YEDEKLER without deleting original archive files or protected 838 channels.","channels":[f"{len(added)} additional unique URLs from {len(sources)} playlist files; {invalid} invalid records skipped; AV not assumed"]}
    PLAY.write_text(result,encoding="utf-8");TEST.write_text(tests,encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"added":len(added),"backups":total,"source_files":len(sources),"per_file":counts,"invalid_records":invalid},ensure_ascii=False))
def parse_text(data):
    tmp=[];cur=None
    for line in data.splitlines(keepends=True):
        if line.startswith("#EXTINF:"):
            if cur:tmp.append("".join(cur))
            cur=[line]
        elif cur is not None:cur.append(line)
    if cur:tmp.append("".join(cur))
    return tmp
if __name__=="__main__":main()
