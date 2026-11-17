#!/usr/bin/env python3
"""One fixed public HLS transport diagnostic; no IPTV scan or playlist writes.

Runs ONLY in the PR #365 read-only CI step. This synthetic public demonstration
stream is never real Turkish broadcaster, device or speech-language evidence.
"""
import json
import subprocess
import tempfile
from pathlib import Path
try:
    from .safe_hls_prefetch import prefetch_hls, UnsafeMediaSource, LOCAL_PROTOCOLS
except ImportError:
    from safe_hls_prefetch import prefetch_hls, UnsafeMediaSource, LOCAL_PROTOCOLS

PUBLIC_SAMPLE = (
    "https://devstreaming-cdn.apple.com/videos/streaming/examples/"
    "bipbop_16x9/bipbop_16x9_variant.m3u8"
)

def run():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest_dir = root / "hls"
        manifest_dir.mkdir()
        try:
            local = prefetch_hls(PUBLIC_SAMPLE, manifest_dir, seconds=6)
        except UnsafeMediaSource as exc:
            print(json.dumps({"status":"PUBLIC_HLS_UNVERIFIED",
                              "stage":"PINNED_FETCH",
                              "reason":str(exc)[:100],
                              "playlist_modified":False}))
            raise SystemExit(1)
        except (OSError, ValueError) as exc:
            print(json.dumps({"status":"PUBLIC_HLS_UNVERIFIED",
                              "stage":"PINNED_FETCH",
                              "reason":type(exc).__name__,
                              "playlist_modified":False}))
            raise SystemExit(1)
        outputs = [
            (["-frames:v", "1"], root / "frame.png"),
            (["-t", "2", "-vn", "-ac", "1", "-ar", "16000"], root / "audio.wav"),
        ]
        for extra, target in outputs:
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                       "-protocol_whitelist", LOCAL_PROTOCOLS, "-i", str(local)]
            command += extra + ["-y", str(target)]
            try:
                done = subprocess.run(command, capture_output=True,
                                      timeout=25, check=False)
            except (OSError, subprocess.TimeoutExpired):
                done = None
            if done is None or done.returncode != 0 or not target.exists() or target.stat().st_size < 1000:
                print(json.dumps({"status":"PUBLIC_HLS_UNVERIFIED",
                                  "stage":"LOCAL_AV_DECODE",
                                  "playlist_modified":False}))
                raise SystemExit(1)
        print(json.dumps({"status":"PUBLIC_HLS_PINNED_AV_OK",
                          "network_ffmpeg_protocols":False,
                          "playlist_modified":False,
                          "real_turkish_channel_verified":False,
                          "device_accepted":False}))

if __name__ == "__main__":
    run()
