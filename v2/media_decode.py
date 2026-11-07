"""Bounded real-frame decoding of public HTTP(S) streams."""
import subprocess
import math
from historical_url_recovery import validate_url


def _error_category(stderr):
    """Only fixed categories: never include stream URLs, tokens or raw FFmpeg logs."""
    message = (stderr or "").lower()
    for name, terms in (
        ("protocol", ("protocol not on whitelist", "protocol not found")),
        ("http", ("http error", "server returned", "403 forbidden", "404 not found")),
        ("tls", ("certificate", "ssl", "tls handshake")),
        ("timeout", ("timed out", "timeout")),
        ("decoder", ("invalid data", "decoder", "could not find codec")),
        ("mapping", ("matches no streams", "stream map")),
    ):
        if any(term in message for term in terms):
            return name
    return "other"


def decode_media(entry, timeout=20, diagnostic=None):
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
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        if diagnostic is not None:
            diagnostic["reason"] = "timeout" if isinstance(exc, subprocess.TimeoutExpired) else "execution_error"
        return False
    if result.returncode != 0:
        if diagnostic is not None:
            diagnostic["reason"] = "ffmpeg_nonzero_exit"
            diagnostic["exit_code"] = result.returncode
            diagnostic["stderr_category"] = _error_category(result.stderr)
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
    verified = all(any(media_types.get(index) == kind for index in decoded)
                   for kind in ("video", "audio"))
    if diagnostic is not None:
        diagnostic["reason"] = "av_verified" if verified else "missing_decoded_frames"
        diagnostic["decoded_types"] = sorted({media_types.get(i, "unknown") for i in decoded})
    return verified
