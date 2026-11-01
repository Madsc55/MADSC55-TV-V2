#!/usr/bin/env python3
"""Probe actual stream audio/video codecs using ffprobe; HTTP 200 is not proof."""
import argparse
import json
import os
import shutil
import subprocess
from urllib.parse import urlsplit

def probe(url, timeout=25, ffprobe='ffprobe'):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return {'status': 'INVALID_URL', 'video': False, 'audio': False}
    executable = shutil.which(ffprobe)
    if not executable:
        return {'status': 'PROBE_UNAVAILABLE', 'video': False, 'audio': False}
    command = [executable, '-v', 'error', '-nostdin', '-probesize', '1500000',
               '-analyzeduration', '3000000', '-rw_timeout', str(int(timeout * 1000000)),
               '-show_entries', 'stream=codec_type,codec_name,width,height',
               '-of', 'json', url]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 5,
                                check=False, env={**os.environ, 'AV_LOG_FORCE_NOCOLOR': '1'})
    except subprocess.TimeoutExpired:
        return {'status': 'TIMEOUT', 'video': False, 'audio': False}
    except OSError:
        return {'status': 'PROBE_FAILED', 'video': False, 'audio': False}
    if result.returncode != 0:
        return {'status': 'PROBE_FAILED', 'video': False, 'audio': False}
    try:
        streams = json.loads(result.stdout).get('streams', [])
    except (ValueError, TypeError):
        return {'status': 'INVALID_PROBE_RESULT', 'video': False, 'audio': False}
    video = any(x.get('codec_type') == 'video' and x.get('codec_name') not in (None, 'unknown') for x in streams)
    audio = any(x.get('codec_type') == 'audio' and x.get('codec_name') not in (None, 'unknown') for x in streams)
    return {'status': 'AV_VERIFIED' if video and audio else ('VIDEO_ONLY' if video else ('AUDIO_ONLY' if audio else 'NO_MEDIA')),
            'video': video, 'audio': audio}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--timeout', type=float, default=25)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error('timeout must be 1..120 seconds')
    outcome = probe(args.url, args.timeout)
    print(json.dumps(outcome))
    if outcome['status'] != 'AV_VERIFIED':
        raise SystemExit(2)

if __name__ == '__main__':
    main()
