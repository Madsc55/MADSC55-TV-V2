#!/usr/bin/env python3
"""Add all decoded scan #61 candidates to EXISTING YEDEKLER for user review."""
import hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIVE=ROOT/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
SNAP=ROOT/"v2/reports/private-playback-snapshot.json"
PLAY=ROOT/"v2/reports/all-source-playback-aggregate.json"
def safe(x): return str(x or "").replace("\n"," ").replace("\r"," ").replace('"',"'").strip()
def main():
    from discover import entries
    snapshot=json.loads(SNAP.read_text())["candidates"]
    tested=json.loads(PLAY.read_text())
    if tested.get("unique_tested")!=27047 or tested.get("video_decoded")!=11808 or not tested.get("coverage_complete"):
        sys.exit("Refusing non-#61 or incomplete playback evidence")
    decoded={r["url_sha256"]:r for r in tested["channel_results"] if r["playback"]=="VIDEO_DECODED"}
    byhash={hashlib.sha256(x["url"].encode()).hexdigest():x for x in snapshot}
    missing=set(decoded)-set(byhash)
    if missing: sys.exit(f"Source snapshot missing {len(missing)} decoded hashes; refusing partial publication")
    original=LIVE.read_text(encoding="utf-8-sig")
    old=list(entries(original)); urls={x["url"] for x in old}
    groups={x["group"] for x in old}
    if len(groups)!=13 or not any("YEDEKLER" in x for x in groups): sys.exit("Category invariant failed")
    lines=[]
    for digest,probe in decoded.items():
        x=byhash[digest];url=x["url"]
        if url in urls: continue
        urls.add(url)
        name=safe(x.get("name")).upper() or "ISIMSIZ ADAY"
        height=probe.get("video_height")
        suffix=f" {height}P" if isinstance(height,int) and height>0 else ""
        audio="" if probe.get("audio") else " [SES KONTROL]"
        logo=safe(x.get("logo"))
        tvg=safe(x.get("tvg_id"))
        lines.extend([f'#EXTINF:-1 tvg-id="{tvg}" tvg-name="{name}" tvg-logo="{logo}" group-title="🗂️ YEDEKLER (14)",🧪 {name}{suffix}{audio}',url])
    if len(lines)//2<9000: sys.exit(f"Suspiciously few matched additions: {len(lines)//2}")
    result=original.rstrip()+"\n"+"\n".join(lines)+"\n"
    counts={}
    for match in re.finditer(r'group-title="([^"]+)"',result):
        key=match.group(1);counts[key]=counts.get(key,0)+1
    if len(counts)!=13: sys.exit("Unexpected category count")
    for oldname,count in counts.items():
        newname=re.sub(r'\s*\(\d+\)$',"",oldname)+f" ({count})"
        result=result.replace('group-title="'+oldname+'"','group-title="'+newname+'"')
    if "TRT 1 1440P QHD" not in result or "DHA CANLI 720P HD" not in result:sys.exit("Original backups missing")
    LIVE.write_text(result,encoding="utf-8")
    print(json.dumps({"added":len(lines)//2,"total_entries":sum(counts.values()),"categories":len(counts),"original_backups_preserved":True}))
if __name__=="__main__":main()
