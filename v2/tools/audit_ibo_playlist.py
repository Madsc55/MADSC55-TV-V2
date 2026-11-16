#!/usr/bin/env python3
"""Read-only IPTV audit. Never edits the original playlist or existing archives."""
import argparse, concurrent.futures, csv, json, pathlib, re, subprocess, time
from collections import Counter

EXTINF = re.compile(r"^#EXTINF", re.I)
GROUP = re.compile(r'group-title\s*=\s*(?:"([^"]*)"|\x27([^\x27]*)\x27|([^,\s]*))', re.I)

def entries(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    header = raw[0] if raw and raw[0].startswith("#EXTM3U") else "#EXTM3U"
    pending = []
    for line in raw[1:]:
        if EXTINF.match(line):
            pending = [line]
        elif line.startswith("#") or not line.strip():
            if pending: pending.append(line)
        else:
            if pending:
                meta = pending[0]
                match = GROUP.search(meta)
                group = next((x for x in match.groups() if x is not None), "") if match else ""
                yield {"group":group,"name":meta.split(",",1)[-1],"url":line.strip(),"block":pending+[line]}
                pending = []
    return header

def verify(item, timeout, retries):
    url = item["url"]
    if not url.startswith(("http://","https://")):
        return "unsupported", "non-HTTP stream (requires separate protocol probe)"
    last = ""
    for attempt in range(retries + 1):
        try:
            p = subprocess.run(["ffprobe","-v","error","-rw_timeout",str(timeout*1000000),
                "-analyzeduration","5000000","-probesize","5000000","-show_entries",
                "stream=codec_type","-of","json",url], capture_output=True,text=True,
                timeout=timeout+5)
            if p.returncode == 0:
                streams = json.loads(p.stdout).get("streams",[])
                types = {s.get("codec_type") for s in streams}
                if "video" in types or "audio" in types:
                    return "verified", "+".join(sorted(types & {"audio","video"}))
                last = "no audio/video stream"
            else: last = (p.stderr or "probe failed").strip()[-300:]
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc: last = str(exc)[-300:]
        if attempt < retries: time.sleep(min(2**attempt, 8))
    # A failed network probe is not proof of a permanently dead channel.
    return "unverified", last

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--playlist",default="MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
    ap.add_argument("--output",default="v2/archives/channel_audit_20261116")
    ap.add_argument("--workers",type=int,default=8)
    ap.add_argument("--timeout",type=int,default=18)
    ap.add_argument("--retries",type=int,default=2)
    args=ap.parse_args()
    source=pathlib.Path(args.playlist)
    if not source.is_file(): raise SystemExit("Source playlist not found: "+str(source))
    lines=source.read_text(encoding="utf-8-sig",errors="replace").splitlines()
    header=lines[0] if lines and lines[0].startswith("#EXTM3U") else "#EXTM3U"
    items=list(entries(source))
    if not items: raise SystemExit("Refusing to audit empty playlist")
    out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=True)
    results=[None]*len(items)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(verify,item,args.timeout,args.retries):i for i,item in enumerate(items)}
        for n,future in enumerate(concurrent.futures.as_completed(futures),1):
            i=futures[future];results[i]=future.result()
            if n%100==0: print(f"Audited {n}/{len(items)}",flush=True)
    with (out/"channel_results.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f);writer.writerow(["position","category","name","url","result","evidence"])
        for i,(item,(status,evidence)) in enumerate(zip(items,results),1):
            writer.writerow([i,item["group"],item["name"],item["url"],status,evidence])
    def write_playlist(filename,keep):
        with (out/filename).open("w",encoding="utf-8") as f:
            f.write(header+"\n")
            for item,(status,_) in zip(items,results):
                if status in keep: f.write("\n".join(item["block"])+"\n")
    write_playlist("verified_working.m3u8",{"verified"})
    write_playlist("unverified_for_retest.m3u8",{"unverified","unsupported"})
    # Never call a failed probe 'dead'. No automatic deletion or movement.
    counts=Counter(s for s,_ in results)
    summary={"source":str(source),"total":len(items),"results":dict(counts),
             "categories":dict(Counter(i["group"] for i in items)),
             "policy":"Unverified is not confirmed dead; original playlist unchanged"}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=="__main__": main()
