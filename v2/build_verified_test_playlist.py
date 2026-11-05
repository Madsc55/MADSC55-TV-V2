#!/usr/bin/env python3
"""Separate IBO test list: only explicit real FFmpeg video+audio evidence.

HTTP hints, FFprobe metadata, page URLs and video-only are not AV proof.
Never writes to the protected main playlist or favorites.
"""
import json
from urllib.parse import urlsplit
from discover import ROOT,LIVE,entries
from webpage_source_discovery import public_hostname

REPORT=ROOT/"v2/reports/turkish-stream-review-queue.json"
OUT=ROOT/"v2/reports/av-verified-ibo-test-only.m3u8"
SUMMARY=ROOT/"v2/reports/av-verified-test-summary.json"

def clean(value):
    return str(value or "").replace("\r"," ").replace("\n"," ").replace('"',"'").strip()

def accepted(item):
    if not isinstance(item,dict): return False
    if (item.get("status")!="VIDEO_AUDIO_DECODED"
            or item.get("proof_source")!="FFMPEG_BOTH_DECODED"
            or item.get("video_decoded") is not True
            or item.get("audio_decoded") is not True
            or not {"video","audio"}.issubset(set(item.get("media_types") or []))):
        return False
    url=item.get("url")
    if not isinstance(url,str): return False
    try:
        p=urlsplit(url)
        return (p.scheme in ("http","https") and bool(p.hostname)
                and public_hostname(p.hostname)
                and p.username is None and p.password is None and not p.fragment
                and p.hostname.lower() not in ("www.youtube.com","youtube.com","youtu.be"))
    except ValueError: return False

def main():
    queue=json.loads(REPORT.read_text(encoding="utf-8"))["items"]
    existing={e["url"] for e in entries(LIVE.read_text(encoding="utf-8-sig"))}
    seen,lines=set(),["#EXTM3U"]
    for item in queue:
        if not accepted(item): continue
        url=item["url"]
        if url in existing or url in seen: continue
        seen.add(url)
        lines.extend(['#EXTINF:-1 group-title="TEST - AV KANITLI, CIHAZ BEKLIYOR",'+clean(item.get("channel_id","ADAY")),url])
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    SUMMARY.write_text(json.dumps({
        "policy":"SEPARATE_IBO_FFMPEG_VIDEO_AUDIO_REQUIRED_DEVICE_PENDING",
        "entries":len(seen),"input_rows":len(queue),
        "main_playlist_modified":False,"ibo_device_verified":False
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Separate FFmpeg AV test entries:",len(seen))

if __name__=="__main__":
    main()
