#!/usr/bin/env python3
"""Real FFprobe+FFmpeg decode of SHA-exact, presently absent historical streams.

The immutable 4,955 URL-SHA baseline is checked first. The only URLs eligible
are exact byte-for-byte matches recovered from existing V2 Git history.
No URLs enter public JSON/logs, no playlist writes, and no IBO claim.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

from final_batch_acceptance import probe as real_av_probe
from historical_targeted_playback import load_missing_report, find_exact_urls
from historical_url_recovery import validate_url

HEX = re.compile(r"[0-9a-f]{64}\Z")
SAFE_RESULTS = {"VIDEO_AUDIO_DECODED","VIDEO_AUDIO_STREAMS_ONLY","VIDEO_ONLY",
    "AUDIO_ONLY","NO_AV","UNSAFE_OR_UNRESOLVED_HOST","UNVERIFIED",
    "PROBE_UNCONFIRMED"}
SAFE_FAILURES = {"FFPROBE_OPTION_UNSUPPORTED","AUTH_REQUIRED","HTTP_FORBIDDEN",
    "HTTP_NOT_FOUND","REDIRECT_REQUIRED_OR_BLOCKED","PROTOCOL_DISALLOWED_BY_SAFETY",
    "NETWORK_TIMEOUT","DNS_RESOLUTION_ERROR","HTTP_RESPONSE_ERROR",
    "MEDIA_FORMAT_UNSUPPORTED","UNKNOWN_NETWORK_OR_MEDIA_ERROR"}


def grouped_decode(missing, recovered, *, prober=real_av_probe, workers=4):
    if not isinstance(missing,set) or len(missing)>4955 or not isinstance(recovered,dict):
        raise ValueError("Unexpected historical missing hash scope")
    if not isinstance(workers,int) or not 1<=workers<=8:
        raise ValueError("Invalid AV worker size")
    if not all(isinstance(x,str) and HEX.fullmatch(x) for x in missing):
        raise ValueError("Invalid original URL hash")
    if not set(recovered)<=missing:
        raise ValueError("Git history returned an unrequested identity")
    valid=[]
    for digest in sorted(recovered):
        url=recovered[digest]
        if not validate_url(url) or hashlib.sha256(url.encode("utf-8")).hexdigest()!=digest:
            raise ValueError("Historical Git URL is not a verified exact hash")
        valid.append((digest,url))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        result=list(executor.map(prober,valid))
    evidence=[]
    for (digest,_), row in zip(valid,result):
        if not isinstance(row,dict) or row.get("url_sha256")!=digest:
            raise ValueError("AV proof not tied to exact recovered identity")
        status=row.get("status")
        if (not isinstance(status,str) or
            not (status in SAFE_RESULTS or status.startswith("PROBE_FAILED_") and
                 status[len("PROBE_FAILED_"):] in SAFE_FAILURES)):
            raise ValueError("Unreviewed URL-bearing probe status")
        video,audio,decoded=(row.get(x) is True for x in ("video","audio","decoded"))
        if decoded and (status!="VIDEO_AUDIO_DECODED" or not video or not audio):
            raise ValueError("False FFmpeg video/audio decode result")
        if status=="VIDEO_AUDIO_DECODED" and (not decoded or not video or not audio):
            raise ValueError("Decoder status requires genuine video and audio frames")
        if status!="VIDEO_AUDIO_DECODED" and decoded:
            raise ValueError("Decoded evidence requires the matching decoder status")
        evidence.append({"url_sha256":digest, "status":status,
                         "video_stream":video, "audio_stream":audio,
                         "ffmpeg_video_audio_decoded":decoded})
    report={"schema":1, "kind":"V2_HISTORICAL_EXACT_CURRENT_MISSING_REAL_FFMPEG",
        "original_historical_url_hashes_requested":len(missing),
        "exact_git_history_url_hashes_found":len(valid),
        "not_in_git_history_sha256":sorted(missing-set(recovered)),
        "current_real_ffmpeg_video_audio_decoded_count":sum(x["ffmpeg_video_audio_decoded"] for x in evidence),
        "ffprobe_video_audio_both_streams_count":sum(
            x["video_stream"] and x["audio_stream"] for x in evidence),
        "url_hashes_unverified_after_real_probe":sum(
            not x["ffmpeg_video_audio_decoded"] for x in evidence),
        "status_counts":dict(sorted(Counter(x["status"] for x in evidence).items())),
        "results":evidence,
        "no_plaintext_urls":True, "original_history_preserved":True,
        "unverified_not_removed":True, "protected_playlist_modified":False,
        "spoken_language_verified":False, "ibo_device_verified":False}
    if "://" in json.dumps(report):
        raise ValueError("Unsafe public URL in historical AV result")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--real-av-batch",action="store_true",required=True)
    p.add_argument("--missing-report",type=Path,required=True)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.resolve()==args.missing_report.resolve():
        p.error("Refusing overwrite or aliased evidence")
    missing=load_missing_report(args.missing_report,args.baseline)
    recovered, provenance=find_exact_urls(missing)
    report=grouped_decode(missing,recovered)
    report["git_blobs_inspected_or_available"]=provenance["git_blobs_inspected_or_available"]
    report["oversized_git_blobs_skipped"]=provenance["oversized_git_blobs_skipped"]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("HISTORICAL_EXACT_REAL_FFMPEG",json.dumps({k:report[k] for k in (
        "original_historical_url_hashes_requested",
        "exact_git_history_url_hashes_found",
        "current_real_ffmpeg_video_audio_decoded_count",
        "ffprobe_video_audio_both_streams_count",
        "url_hashes_unverified_after_real_probe",
        "status_counts")},sort_keys=True))


if __name__=="__main__":
    main()
