"""Bounded real-frame decoding of public HTTP(S) streams."""
import subprocess
import math
from historical_url_recovery import validate_url


def decode_media(entry, timeout=20):
    """True only if FFmpeg emits both decoded video and audio frame checksums."""
    url = entry.get("url") if isinstance(entry, dict) else None
    if (not validate_url(url) or isinstance(timeout, bool) or
            not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or
            not 1 <= timeout <= 120):
        return False
    command = [
        "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
        "-protocol_whitelist", "http,https,tcp,tls,crypto",
        "-rw_timeout", str(int(timeout * 1000000)),
        "-i", url, "-map", "0:v:0", "-map", "0:a:0",
        "-t", str(int(timeout)),
        "-f", "framemd5", "-"
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout + 5, check=False)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    if result.returncode != 0:
        return False
    media_types = {}
    decoded = set()
    for line in result.stdout.splitlines():
        if line.startswith("#media_type "):
            parts = line[len("#media_type "):].split(":", 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                media_types[int(parts[0].strip())] = parts[1].strip()
        elif line and not line.startswith("#"):
            parts = [part.strip() for part in line.split(",")]
            if (len(parts) >= 6 and parts[0].isdigit() and
                    parts[4].isdigit() and int(parts[4]) > 0 and parts[5]):
                decoded.add(int(parts[0]))
    return all(any(media_types.get(index) == kind for index in decoded)
               for kind in ("video", "audio"))
