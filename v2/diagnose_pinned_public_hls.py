#!/usr/bin/env python3
"""Bounded, read-only public HLS transport diagnostics for PR #365 only.

Public VOD test streams are not Turkish broadcaster, speech-language or device
acceptance. Each request is public-IP pinned and redirects are fail-closed.
No user playlist is read or changed, and raw URLs are not logged.
"""
import json
import subprocess
import tempfile
from pathlib import Path
try:
    from .safe_hls_prefetch import prefetch_hls, UnsafeMediaSource, LOCAL_PROTOCOLS
except ImportError:
    from safe_hls_prefetch import prefetch_hls, UnsafeMediaSource, LOCAL_PROTOCOLS

PUBLIC_SAMPLES = (
    ("apple", "https://devstreaming-cdn.apple.com/videos/streaming/"
              "examples/bipbop_16x9/bipbop_16x9_variant.m3u8"),
    ("mux", "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"),
)

def try_sample(sample_id, url):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest_dir = root / "hls"
        manifest_dir.mkdir()
        try:
            local = prefetch_hls(url, manifest_dir, seconds=6)
        except UnsafeMediaSource as exc:
            return {"id":sample_id, "status":"UNVERIFIED", "stage":"PINNED_FETCH",
                    "reason":str(exc)[:100]}
        except (OSError, ValueError) as exc:
            return {"id":sample_id, "status":"UNVERIFIED", "stage":"PINNED_FETCH",
                    "reason":type(exc).__name__}
        outputs = [
            (["-frames:v", "1"], root / "frame.png"),
            (["-t", "2", "-vn", "-ac", "1", "-ar", "16000"], root / "audio.wav"),
        ]
        for options, output in outputs:
            args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                    "-protocol_whitelist", LOCAL_PROTOCOLS, "-i", str(local)]
            args += options + ["-y", str(output)]
            try:
                result = subprocess.run(args, capture_output=True, timeout=25, check=False)
            except (OSError, subprocess.TimeoutExpired):
                result = None
            if result is None or result.returncode != 0 or not output.exists() or output.stat().st_size < 1000:
                return {"id":sample_id, "status":"UNVERIFIED", "stage":"LOCAL_AV_DECODE"}
        return {"id":sample_id, "status":"PUBLIC_HLS_PINNED_AV_OK",
                "network_ffmpeg_protocols":False}

def run():
    outcomes = []
    for sample_id, url in PUBLIC_SAMPLES:
        result = try_sample(sample_id, url)
        outcomes.append(result)
        if result["status"] == "PUBLIC_HLS_PINNED_AV_OK":
            print(json.dumps({"status":"PUBLIC_HLS_PINNED_AV_OK",
                              "sample_id":sample_id, "playlist_modified":False,
                              "real_turkish_channel_verified":False,
                              "device_accepted":False}))
            return
    print(json.dumps({"status":"PUBLIC_HLS_UNVERIFIED", "samples":outcomes,
                      "playlist_modified":False,
                      "real_turkish_channel_verified":False}))
    raise SystemExit(1)

if __name__ == "__main__":
    run()
