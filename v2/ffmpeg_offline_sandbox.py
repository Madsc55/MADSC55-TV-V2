#!/usr/bin/env python3
"""Linux fail-closed FFmpeg network namespace launcher.

Only local, pre-downloaded media may be decoded. This is an offline building
block, not permission to run #497 live retries. Requires a working bubblewrap
network namespace; missing sandbox => refusal, never unsandboxed fallback.
"""
import os
from pathlib import Path
import shutil
import subprocess

class SandboxUnavailable(RuntimeError):
    pass

def isolated_local_ffmpeg(input_path, output_path, *, ffmpeg="ffmpeg", bwrap="bwrap",
                          timeout=25, runner=subprocess.run, which=shutil.which):
    source, target = Path(input_path), Path(output_path)
    if (not source.is_absolute() or not target.is_absolute() or
            source.is_symlink() or not source.is_file() or
            target.exists() or target.is_symlink() or
            not target.parent.is_dir() or source == target):
        raise ValueError("Only an existing absolute local input and new output are allowed")
    # Deliberately do not accept arbitrary FFmpeg flags or remote input.
    if source.suffix.lower() not in (".ts", ".mp4", ".mkv"):
        raise ValueError("Unsupported local input")
    if target.suffix.lower() != ".mkv":
        raise ValueError("Output must be MKV")
    sandbox, decoder = which(bwrap), which(ffmpeg)
    if not sandbox or not decoder or not os.path.isabs(sandbox) or not os.path.isabs(decoder):
        raise SandboxUnavailable("Network namespace or FFmpeg unavailable")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("Invalid timeout")
    # Bubblewrap unshares network namespace before starting FFmpeg. Root filesystem
    # is read-only; only the target directory is writable. /proc and /dev are
    # private. No shell, no HTTP protocols, no automatic fallback.
    cmd = [sandbox, "--die-with-parent", "--unshare-net", "--unshare-pid",
           "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev",
           "--bind", str(target.parent), str(target.parent),
           "--", decoder, "-nostdin", "-hide_banner", "-v", "error",
           "-protocol_whitelist", "file", "-i", str(source),
           "-t", "12", "-map", "0:v:0?", "-map", "0:a:0?",
           "-c:v", "mpeg4", "-c:a", "aac", "-n", str(target)]
    result = runner(cmd, timeout=timeout, capture_output=True, check=False)
    if result.returncode != 0:
        raise SandboxUnavailable("Isolated decode failed; no unsafe fallback")
    if target.is_symlink() or not target.is_file():
        raise SandboxUnavailable("No isolated output")
    return {"status": "LOCAL_DECODE_ONLY", "network_namespace_requested": True,
            "live_retry_authorized": False, "av_verified": False}
