"""Bounded real-frame decoding of public HTTP(S) streams."""
import subprocess
from historical_url_recovery import validate_url


def decode_media(entry, timeout=20):
    """True only if ffmpeg actually outputs a decoded video frame checksum."""
    url = entry.get("url") if isinstance(entry, dict) else None
    if not validate_url(url) or not 1 <= timeout <= 120:
        return False
    command = [
        "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
        "-protocol_whitelist", "http,https,tcp,tls,crypto",
        "-rw_timeout", str(int(timeout * 1000000)),
        "-i", url, "-map", "0:v:0", "-frames:v", "1",
        "-f", "framemd5", "-"
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout + 5, check=False)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    if result.returncode != 0:
        return False
    return ("#media_type 0: video" in result.stdout and
            any(line and not line.startswith("#") and len(line.split(",")) >= 6
                for line in result.stdout.splitlines()))
