#!/usr/bin/env python3
"""Opt-in bounded OCR and subtitle sampling for a single reviewed HTTP(S) stream.

No playlist mutation, no auto-language approval, and no raw text in output.
Requires local ffmpeg and tesseract; subtitle extraction is optional.
"""
import argparse
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
try:
    from .backup_text_evidence import inspect_text_observations
except ImportError:
    from backup_text_evidence import inspect_text_observations

# Untrusted HTTP/HLS input must not be able to open local file: URLs.\nSTREAM_PROTOCOL_WHITELIST = "http,https,tcp,tls,crypto"\n\ndef valid_url(url):
    if not isinstance(url, str) or not url or len(url) > 4096 or any(ord(ch) < 33 or ord(ch) == 127 for ch in url):
        return False
    try:
        p = urlsplit(url)
        host = p.hostname
        if p.scheme not in ("http", "https") or not host or p.username or p.password or p.fragment:
            return False
        if p.port is not None and not 1 <= p.port <= 65535:
            return False
        normalized_host = host.lower().rstrip(".")
        if ":" not in normalized_host and not re.fullmatch(r"[a-z0-9.-]+", normalized_host):
            return False
        if ":" not in normalized_host and any(not label or label.startswith("-") or label.endswith("-") for label in normalized_host.split(".")):
            return False
        if normalized_host in ("localhost", "localhost.localdomain") or normalized_host.endswith((".localhost", ".local", ".internal")):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            # Reject libc's legacy numeric IPv4 forms such as 127.1,
            # 0x7f.0.0.1 and 0177.0.0.1; these are not DNS names.
            labels = normalized_host.split(".")
            if all(re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)", label) for label in labels):
                return False
            # Runtime DNS resolution, redirects and network egress must still
            # be constrained outside FFmpeg; lexical validation is not enough.
            return bool(normalized_host and "." in normalized_host and not normalized_host.endswith(".invalid"))
        return address.is_global
    except ValueError:
        return False

def public_dns_for_url(url):
    """Additional public-address check. External egress must independently
    prevent DNS rebinding, redirects and unsafe nested HLS requests.
    """
    if not valid_url(url):
        return False
    p = urlsplit(url)
    try:
        addresses = socket.getaddrinfo(
            p.hostname, p.port or (443 if p.scheme == "https" else 80),
            type=socket.SOCK_STREAM)
    except (OSError, ValueError):
        return False
    if not addresses:
        return False
    try:
        return all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (IndexError, TypeError, ValueError):
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
    if os.environ.get("MADSC55_SECURE_EGRESS_CONFIRMED") != "1":
        return {"status":"SECURE_EGRESS_NOT_CONFIRMED","language_evidence_verified":False,
                "review_approved":False}
    if not public_dns_for_url(url):
        return {"status":"UNSAFE_DNS_TARGET","language_evidence_verified":False,
                "review_approved":False}
    if not shutil.which("ffmpeg"):
        return {"status":"FFMPEG_UNAVAILABLE","language_evidence_verified":False}
    observations = []
    with tempfile.TemporaryDirectory() as d:
        frame = str(Path(d) / "frame.png")
        # Fixed single frame, no playlist writes, network work bounded by timeout.
        cmd = ["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
               "-protocol_whitelist",STREAM_PROTOCOL_WHITELIST,
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
                   "-protocol_whitelist",STREAM_PROTOCOL_WHITELIST,
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
