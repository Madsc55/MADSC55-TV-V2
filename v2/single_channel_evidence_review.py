#!/usr/bin/env python3
"""Read-only single-channel AV, ASR, OCR and WebVTT evidence sampler.

A report is an anonymized review aid, never channel promotion or an IBO edit.
Live sampling requires a reviewed source and separately attested secure egress.
Unsupported live formats remain inconclusive.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

try:
    from .backup_text_sampler import valid_url
    from .backup_text_evidence import inspect_text_observations
    from .safe_hls_prefetch import (
        prefetch_hls, subtitle_observations, UnsafeMediaSource, LOCAL_PROTOCOLS
    )
except ImportError:
    from backup_text_sampler import valid_url
    from backup_text_evidence import inspect_text_observations
    from safe_hls_prefetch import (
        prefetch_hls, subtitle_observations, UnsafeMediaSource, LOCAL_PROTOCOLS
    )

def _decode_local(local_hls, target, options, seconds):
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
               "-protocol_whitelist", LOCAL_PROTOCOLS,
               "-i", str(local_hls), "-t", str(seconds)]
    command.extend(options)
    command.extend(["-y", str(target)])
    try:
        result = subprocess.run(command, capture_output=True, timeout=seconds + 20,
                                check=False)
        return result.returncode == 0 and target.exists()
    except (OSError, subprocess.TimeoutExpired):
        return False

def _offline_asr_hint(wav, model_dir):
    if model_dir is None:
        return {"status": "ASR_NOT_RUN", "spoken_turkish_hint": False}
    model_dir = Path(model_dir)
    if not model_dir.is_dir():
        return {"status": "ASR_LOCAL_MODEL_UNAVAILABLE", "spoken_turkish_hint": False}
    try:
        from faster_whisper import WhisperModel
        # Only a user-installed local model: no model download in a review.
        model = WhisperModel(str(model_dir), device="cpu", compute_type="int8",
                             local_files_only=True)
        segments, info = model.transcribe(str(wav), beam_size=1, vad_filter=True)
        speech_present = any(s.text.strip() for s in segments)
        probability = float(info.language_probability)
        hint = (speech_present and info.language == "tr" and
                0 <= probability <= 1)
        return {"status": "ASR_HINT_ONLY", "spoken_turkish_hint": bool(hint),
                "speech_detected": bool(speech_present)}
    except (ImportError, OSError, ValueError, RuntimeError, TypeError, AttributeError):
        return {"status": "ASR_SAMPLE_UNAVAILABLE", "spoken_turkish_hint": False}

def review_one(url, output_path, seconds=8, source_authorized=False, model_dir=None):
    output_path = Path(output_path)
    if source_authorized is not True:
        raise ValueError("An approved single source is required")
    if os.environ.get("MADSC55_SECURE_EGRESS_CONFIRMED") != "1":
        raise ValueError("Independent secure egress attestation required")
    if not valid_url(url):
        raise ValueError("Unsafe source URL")
    if not isinstance(seconds, int) or not 5 <= seconds <= 15:
        raise ValueError("Sample seconds must be 5..15")
    if output_path.exists():
        raise FileExistsError("Refusing to overwrite any existing file")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg unavailable")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    with tempfile.TemporaryDirectory(prefix="v2-one-review-") as directory:
        root = Path(directory)
        # Network protocol handling stays exclusively inside pinned prefetch.
        local_hls = prefetch_hls(url, root, seconds=seconds)
        frame, wav = root / "frame.png", root / "audio.wav"
        video = _decode_local(local_hls, frame, ["-frames:v", "1"], seconds)
        audio = _decode_local(local_hls, wav, ["-vn", "-ac", "1",
                                               "-ar", "16000"], seconds)
        video = video and frame.stat().st_size > 512
        audio = audio and wav.stat().st_size > 16000
        observations = []
        if video and shutil.which("tesseract"):
            try:
                proc = subprocess.run(["tesseract", str(frame), "stdout",
                                       "-l", "tur+eng"], capture_output=True,
                                      text=True, timeout=12, check=False)
                if proc.returncode == 0 and proc.stdout:
                    observations.append({"kind": "OCR", "text": proc.stdout[:4096]})
            except (OSError, subprocess.TimeoutExpired):
                pass
        try:
            observations.extend(subtitle_observations(url))
        except (UnsafeMediaSource, OSError, UnicodeError):
            pass
        hints = inspect_text_observations(observations)
        asr = (_offline_asr_hint(wav, model_dir) if audio
               else {"status": "NO_DECODED_AUDIO", "spoken_turkish_hint": False})
        report = {
            "policy": "READ_ONLY_SINGLE_CHANNEL_REVIEW_NO_AUTO_APPROVAL",
            "url_sha256": digest,
            "status": "AV_SAMPLED_REVIEW_REQUIRED" if video and audio else "AV_INCOMPLETE",
            "video_decoded": bool(video),
            "audio_decoded": bool(audio),
            "asr_status": asr["status"],
            "spoken_turkish_hint": asr["spoken_turkish_hint"],
            "ocr_turkish_hint": any(r["kind"] == "OCR" and r["turkish_review_hint"]
                                    for r in hints["observations"]),
            "subtitle_turkish_hint": any(r["kind"] == "SUBTITLE" and r["turkish_review_hint"]
                                         for r in hints["observations"]),
            "language_evidence_verified": False,
            "review_approved": False,
            "device_accepted": False,
            "real_turkish_broadcaster_verified": False,
            "source_raw_text_retained": False,
            "playlist_modified": False,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as destination:
        json.dump(report, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
    return report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=8)
    p.add_argument("--reviewed-source-authorized", action="store_true")
    p.add_argument("--local-asr-model", type=Path)
    args = p.parse_args()
    result = review_one(args.url, args.output, args.seconds,
                        args.reviewed_source_authorized, args.local_asr_model)
    print(json.dumps({k: result[k] for k in (
        "status", "video_decoded", "audio_decoded", "spoken_turkish_hint",
        "ocr_turkish_hint", "subtitle_turkish_hint", "review_approved")}))
if __name__ == "__main__":
    main()
