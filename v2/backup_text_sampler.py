#!/usr/bin/env python3
"""Opt-in bounded OCR and subtitle sampling for a single reviewed HTTP(S) stream.

No playlist mutation, no auto-language approval, and no raw text in output.
Requires local ffmpeg and tesseract; subtitle extraction is optional.
"""
import argparse
import ipaddress
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
try:
    from .backup_text_evidence import inspect_text_observations
except ImportError:
    from backup_text_evidence import inspect_text_observations

def valid_url(url):
    if not isinstance(url, str) or len(url) > 4096:
        return False
    try:
        p = urlsplit(url)
        host = p.hostname
        if p.scheme not in ("http", "https") or not host or p.username or p.password:
            return False
        if host.lower().rstrip(".") in ("localhost", "localhost.localdomain") or host.lower().endswith(".localhost"):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return True  # DNS must additionally be restricted at network egress.
        return address.is_global
    except ValueError:
        return False

def execute(cmd, timeout):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""

def sample(url, seconds=8, include_subtitles=True):
    if not valid_url(url):
        raise ValueError("Invalid stream URL")
    if not isinstance(seconds, int) or not 2 <= seconds <= 15:
        raise ValueError("seconds must be 2..15")
    if not shutil.which("ffmpeg"):
        return {"status":"FFMPEG_UNAVAILABLE","language_evidence_verified":False}
    observations = []
    with tempfile.TemporaryDirectory() as d:
        frame = str(Path(d) / "frame.png")
        # Fixed single frame, no playlist writes, network work bounded by timeout.
        cmd = ["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
               "-rw_timeout","8000000","-i",url,"-t",str(seconds),
               "-frames:v","1","-y",frame]
        execute(cmd,seconds+12)
        if Path(frame).exists() and shutil.which("tesseract"):
            text = execute(["tesseract",frame,"stdout","-l","tur+eng"],12)
            if text:
                observations.append({"kind":"OCR","text":text[:4096]})
        if include_subtitles:
            subtitle = str(Path(d) / "subtitle.srt")
            cmd = ["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
                   "-rw_timeout","8000000","-i",url,"-map","0:s:0?",
                   "-t",str(seconds),"-f","srt","-y",subtitle]
            execute(cmd,seconds+12)
            p=Path(subtitle)
            if p.exists() and p.stat().st_size:
                observations.append({"kind":"SUBTITLE","text":p.read_text(encoding="utf-8",errors="replace")[:4096]})
    report=inspect_text_observations(observations)
    return {"status":"HINTS_ONLY" if observations else "NO_TEXT_EVIDENCE",
            "observation_count":len(observations),
            "ocr_hint":any(x["kind"]=="OCR" and x["turkish_review_hint"] for x in report["observations"]),
            "subtitle_hint":any(x["kind"]=="SUBTITLE" and x["turkish_review_hint"] for x in report["observations"]),
            "language_evidence_verified":False,"review_approved":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--url",required=True)
    parser.add_argument("--seconds",type=int,default=8)
    parser.add_argument("--no-subtitles",action="store_true")
    args=parser.parse_args()
    print(json.dumps(sample(args.url,args.seconds,not args.no_subtitles)))

if __name__=="__main__":
    main()
