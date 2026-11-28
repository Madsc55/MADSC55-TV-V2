#!/usr/bin/env python3
"""Read-only bounded Stage 2 orchestration. Evidence is not automatic acceptance."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from urllib.parse import urlencode

from v2.playlist_parts_manager import PLAYLIST, ROOT
from v2.discovery_34_live_contract import probe_queries
from v2.federated_m3u_source_discovery import discover_provider
from v2.official_sites_discovery import select_official_sites
from v2.stage1_metadata_refresh import fetch
from v2.nonforeign_fresh_full import inventory, review
from v2.yedekler_quality_review import get_quality_decoder
from v2.stream_quality_decision import decide

TASKS = ("B01","B03","B04","B05","B06","B07","B10","B11","B19","B24",
         "B25","B26","B27","B28","B29","B30")
PIN = "68fcad6bdcde53fffb25de32cefbecb7758986dfd3fd866b9928084012ba5d92"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def result(status, **details):
    return {"status":status, **details}

def command(module, relative, timeout):
    """Run existing adapter in a disposable checkout copy, not the live tree."""
    import shutil
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        shutil.copytree(ROOT/"v2",root/"v2",ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(PLAYLIST,root/PLAYLIST.name)
        target=root/relative
        target.unlink(missing_ok=True)
        run=subprocess.run([sys.executable,str(root/"v2"/module)],cwd=root,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           timeout=timeout,check=False)
        if not target.is_file() or target.stat().st_size>30_000_000:
            return result("INCOMPLETE",exit_code=run.returncode)
        doc=json.loads(target.read_text())
        # Never publish raw candidate stream addresses, credentials or provider stderr.
        counts={k:v for k,v in doc.items() if type(v) in (int,bool)}
        return result("OBSERVED" if run.returncode==0 else "INCOMPLETE",
                      exit_code=run.returncode,counts=counts,report_sha256=digest(target.read_bytes()))

def sources():
    out={}
    out["B01"]=guard(lambda:command("public_source_audit.py","v2/reports/public-source-audit.json",240))
    out["B03"]=guard(lambda:command("github_source_discovery.py","v2/reports/github-source-discovery.json",360))
    for task,provider in (("B04","gitlab"),("B05","codeberg")):
        def federated(p=provider):
            d=discover_provider(p,queries=("turkish-iptv","iptv"))
            return result("OBSERVED" if d["status"]=="ok" else "INCOMPLETE",
                          projects=d["projects_discovered"],sources=d["sources_found"],
                          rate_limited=bool(d.get("rate_limited")))
        out[task]=guard(federated)
    out["B06"]=guard(lambda:command("youtube_discovery.py","v2/reports/youtube-live-candidates.json",240))
    def directory():
        doc=json.loads(fetch("https://iptv-org.github.io/api/channels.json",25_000_000))
        rows=select_official_sites(doc,worldwide=True)
        return result("DIRECTORY_ONLY",worldwide=len(rows),
                      country_counts=dict(Counter(r["country"] for r in rows)))
    out["B07"]=guard(directory)
    out["B11"]=dict(out["B07"])
    def archive():
        # Fixed endpoint and query, metadata only; no archive stream extraction.
        import urllib.request
        from v2.discovery_34 import _NoRedirect, fetch_with_retry
        url="https://archive.org/advancedsearch.php?"+urlencode(
            {"q":"mediatype:movies AND (Turkish television OR Azerbaijan television)",
             "fl[]":"identifier","rows":20,"page":1,"output":"json"})
        def get(u):
            with urllib.request.build_opener(_NoRedirect).open(u,timeout=15) as res:
                data=res.read(1_000_001)
            if len(data)>1_000_000:
                raise ValueError("archive limit")
            return json.loads(data)
        d=fetch_with_retry(url,fetch=get)["response"]
        return result("DIRECTORY_ONLY",records=len(d["docs"]),total=d["numFound"])
    out["B10"]=guard(archive)
    return out

def guard(fn):
    try:
        return fn()
    except Exception as exc:
        return result("INCOMPLETE",error=type(exc).__name__)

def media(raw, model_dir, limit):
    rows=inventory(raw,"nonforeign")
    # Exclude all YEDEKLER and archive records: do not touch the 685 hold.
    selected=[r for r in rows if "YEDEKLER" not in r["category"].upper()
              and "ARŞİV" not in r["category"].upper() and r["url"]][:limit]
    exe=get_quality_decoder()
    if not exe or model_dir is None:
        raise ValueError("decoder and pinned model required")
    from faster_whisper import WhisperModel
    from v2.foreign_language_sample import sample
    model=WhisperModel(str(model_dir),device="cpu",compute_type="int8",local_files_only=True)
    records=[]
    for row in selected:
        observed=review(row,exe,set(),lambda data,fmt:sample(data,fmt,exe,model))
        # Never authorize a negative decision, movement or replacement.
        observed["red_eligible"]=False
        records.append(observed)
    return records

def summarize_media(records):
    attempts=[e for r in records for rnd in r.get("rounds",[]) for e in rnd.get("evidence",[])]
    lang=[e["language_review"] for e in attempts if isinstance(e.get("language_review"),dict)]
    av=sum(r.get("healthy_rounds")==3 for r in records)
    out={"B19":result("OBSERVED" if av else "INCOMPLETE",samples=len(records),three_round_av=av),
         "B24":result("OBSERVED" if attempts else "INCOMPLETE",attempts=len(attempts),
                     full_media=sum(e.get("full_sample") is True for e in attempts)),
         "B25":result("PRESERVED",backup_scope_excluded=True),
         "B29":result("INDEPENDENT_IDENTITY_REQUIRED",verified=0)}
    for task,key in (("B26","asr"),("B27","ocr"),("B28","webvtt")):
        values=[x[key] for x in lang if isinstance(x.get(key),dict)]
        out[task]=result("OBSERVED" if values else "INCOMPLETE",observations=len(values),
                         status_counts=dict(Counter(str(x.get("status","UNSPECIFIED")) for x in values)))
    # Existing review has no independently established identity or measured bitrate.
    # Run selection fail-closed rather than fabricate these prerequisites.
    ranked=decide([{"channel_id":None,"url_sha256":r.get("url_sha256"),
                    "identity_evidence_verified":False} for r in records])
    out["B30"]=result("INDEPENDENT_IDENTITY_AND_MEASUREMENTS_REQUIRED",
                      selected=sum(x["selected"] for x in ranked["decisions"]))
    return out

def run(raw, source_fn, media_fn, output, mode):
    if mode=="live" and digest(raw)!=PIN:
        raise ValueError("playlist checkpoint mismatch")
    results=source_fn()
    media_error=None
    try:
        records=media_fn()
    except Exception as exc:
        records=[]
        media_error=type(exc).__name__
    results.update(summarize_media(records))
    if set(results)!=set(TASKS):
        raise ValueError("missing task evidence")
    report={"schema":1,"mode":mode,"created_utc":datetime.now(timezone.utc).isoformat(),
            "playlist_sha256":digest(raw),"tasks":results,"media_error":media_error,
            "playlist_modified":False,"production_accepted":False}
    output.mkdir(parents=True,exist_ok=False)
    (output/"stage2.json").write_text(json.dumps(report,indent=2)+"\n")
    md=["# Stage 2 evidence", "", "Mode: "+mode,"","| Task | Result |","|---|---|"]
    md.extend("| "+t+" | "+results[t]["status"]+" |" for t in TASKS)
    (output/"stage2.md").write_text("\n".join(md)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--model-dir",type=Path,required=True)
    p.add_argument("--limit",type=int,default=2,choices=range(1,5))
    a=p.parse_args()
    raw=PLAYLIST.read_bytes()
    report=run(raw,sources,lambda:media(raw,a.model_dir,a.limit),a.output,"live")
    if PLAYLIST.read_bytes()!=raw:
        raise RuntimeError("playlist changed")
    print(json.dumps(report))
    if report["media_error"] or any(v["status"]=="INCOMPLETE" for v in report["tasks"].values()):
        raise SystemExit(1)

if __name__=="__main__":
    main()
