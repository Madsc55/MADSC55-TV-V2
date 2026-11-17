#!/usr/bin/env python3
"""Export separate ANA_ARSIV, TURK and YABANCI M3U files from verified YEDEKLER snapshot."""
import argparse,hashlib,json,os,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
NAMES={"ANA_ARSIV":"ANA_ARSIV.m3u8","TURK":"TURK_ARSIV.m3u8","YABANCI":"YABANCI_ARSIV.m3u8","TEST":"YEDEKLER_TEST.m3u8"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    ap.add_argument("--first-batch",action="store_true",help="initial 2500 as TEST, rest as ANA_ARSIV; preview without mutating state")
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    s=json.loads((P/"state.json").read_text(encoding="utf-8"))
    data=(P/"YEDEKLER_ARCHIVE.m3u8").read_bytes()
    if hashlib.sha256(data).hexdigest()!=s["source_sha256"]:raise SystemExit("REFUSED: archive SHA mismatch")
    lines=data.decode("utf-8").splitlines(keepends=True)
    blocks=[];current=None
    for line in lines:
        if line.startswith("#EXTINF"):
            current=[line];blocks.append(current)
        elif current is not None:current.append(line)
    if len(blocks)!=s["total"]:raise SystemExit("REFUSED: archive channel count mismatch")
    if a.first_batch and (s["status"] or s["history"]):raise SystemExit("REFUSED: initial batch requires empty state")
    out={key:["#EXTM3U\n"] for key in NAMES}
    for idx,block in enumerate(blocks,1):
        status=("TEST" if idx<=2500 else "ANA_ARSIV") if a.first_batch else s["status"].get(str(idx),"ANA_ARSIV")
        if status not in out:raise SystemExit("REFUSED: invalid status")
        out[status].extend(block)
    counts={k:sum(1 for line in lines if line.startswith("#EXTINF")) for k,lines in out.items()}
    if sum(counts.values())!=s["total"]:raise SystemExit("REFUSED: channel loss")
    print(json.dumps(counts,ensure_ascii=False))
    if not a.apply:return
    a.output_dir.mkdir(parents=True,exist_ok=True)
    if any((a.output_dir/name).exists() for name in NAMES.values()):raise SystemExit("REFUSED: existing output; choose empty directory")
    for key,name in NAMES.items():
        dest=a.output_dir/name
        fd,tmp=tempfile.mkstemp(dir=a.output_dir,prefix="."+name)
        try:
            with os.fdopen(fd,"w",encoding="utf-8",newline="") as f:f.writelines(out[key])
            os.replace(tmp,dest)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
if __name__=="__main__":main()
