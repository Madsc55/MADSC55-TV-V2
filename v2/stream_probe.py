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
    command = [executable, '-v', 'error', '-probesize', '1500000',
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
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            return {'status': 'INVALID_PROBE_RESULT', 'video': False, 'audio': False}
        streams = payload.get('streams', [])
    except (ValueError, TypeError):
        return {'status': 'INVALID_PROBE_RESULT', 'video': False, 'audio': False}
    if not isinstance(streams, list) or any(not isinstance(x, dict) for x in streams):
        return {'status': 'INVALID_PROBE_RESULT', 'video': False, 'audio': False}
    video = any(x.get('codec_type') == 'video' and x.get('codec_name') not in (None, 'unknown') for x in streams)
    audio = any(x.get('codec_type') == 'audio' and x.get('codec_name') not in (None, 'unknown') for x in streams)
    # Resolution is measured only from ffprobe video-stream metadata, never from a channel label.
    dimensions = [(s.get('width'), s.get('height')) for s in streams
                  if s.get('codec_type') == 'video' and s.get('codec_name') not in (None, 'unknown')]
    dimensions = [(w, h) for w, h in dimensions
                  if type(w) is int and type(h) is int and 0 < w <= 16384 and 0 < h <= 16384]
    width, height = max(dimensions, key=lambda pair: pair[0] * pair[1]) if dimensions else (None, None)
    # ffprobe discovers declared streams, but does not prove decoded video frames or audible samples.
    return {'streams': streams, 'status': 'AV_STREAMS_PRESENT' if video and audio else ('VIDEO_ONLY' if video else ('AUDIO_ONLY' if audio else 'NO_MEDIA')),
            'evidence_level': 'ffprobe_stream_metadata', 'decoded_av_verified': False,
            'video': video, 'audio': audio, 'width': width, 'height': height,
            'resolution_verified': bool(video and width and height)}


def verify_decoded_av(url, timeout=25, ffmpeg='ffmpeg'):
    """Require at least one actually decoded frame from both video and audio."""
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return {'decoded_av_verified': False, 'decode_status': 'INVALID_URL'}
    executable = shutil.which(ffmpeg)
    if not executable:
        return {'decoded_av_verified': False, 'decode_status': 'DECODER_UNAVAILABLE'}
    for selector in ('v:0', 'a:0'):
        command = [executable, '-nostdin', '-hide_banner', '-v', 'error',
                   '-rw_timeout', str(int(timeout * 1000000)), '-i', url,
                   '-map', '0:' + selector, '-frames:' + selector[0], '1',
                   '-f', 'framemd5', '-']
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=timeout + 5, check=False)
        except subprocess.TimeoutExpired:
            return {'decoded_av_verified': False, 'decode_status': 'TIMEOUT'}
        except OSError:
            return {'decoded_av_verified': False, 'decode_status': 'DECODE_FAILED'}
        # framemd5 emits a non-comment CSV line only for an actual decoded frame.
        frames = [line for line in result.stdout.splitlines()
                  if line.strip() and not line.lstrip().startswith('#')]
        if result.returncode != 0 or not frames:
            return {'decoded_av_verified': False, 'decode_status': 'NO_DECODED_FRAME'}
    return {'decoded_av_verified': True, 'decode_status': 'DECODED_AV'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--timeout', type=float, default=25)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error('timeout must be 1..120 seconds')
    outcome = probe(args.url, args.timeout)
    if outcome['status'] == 'AV_STREAMS_PRESENT':
        outcome.update(verify_decoded_av(args.url, args.timeout))
        if outcome['decoded_av_verified']:
            outcome['status'] = 'AV_VERIFIED'
    print(json.dumps(outcome))
    if outcome['status'] != 'AV_VERIFIED':
        raise SystemExit(2)

if __name__ == '__main__':
    main()
