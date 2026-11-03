#!/usr/bin/env python3
"""Bounded, opt-in speech-language evidence for already discovered streams.

Never publishes a playlist, and never treats metadata as language proof.
Requires faster-whisper and ffmpeg installed by an explicit review job.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

REPORTS = Path(__file__).resolve().parent / "reports"

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=REPORTS / "private-playback-snapshot.json")
    parser.add_argument("--playback", type=Path, default=REPORTS / "all-source-playback-aggregate.json")
    parser.add_argument("--output", type=Path, default=REPORTS / "spoken-language-samples.json")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.limit <= 16 or not 5 <= args.seconds <= 30:
        parser.error("Safety bounds: 1-16 streams, 5-30 seconds")
    from faster_whisper import WhisperModel
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    playback = json.loads(args.playback.read_text(encoding="utf-8"))
    if not playback.get("coverage_complete"):
        raise SystemExit("Incomplete playback inventory")
    tested = {x["url_sha256"]: x for x in playback["channel_results"]}
    if len(tested) != len(playback["channel_results"]):
        raise SystemExit("Duplicate playback hashes")
    if len(snapshot.get("candidates", [])) != len(tested):
        raise SystemExit("Snapshot and playback candidate count mismatch")
    selected = []
    for item in snapshot["candidates"]:
        url = item.get("url", "")
        digest = hashlib.sha256(url.encode()).hexdigest()
        match = tested.get(digest)
        if match and match.get("playback") == "VIDEO_DECODED" and str(match.get("audio", "")).upper() in ("TRUE", "YES", "PRESENT", "AUDIO_PRESENT", "AUDIO_DECODED") and url.startswith(("https://", "http://")):
            selected.append((digest, url))
        if len(selected) >= args.limit:
            break
    if not selected:
        raise SystemExit("No eligible video+audio streams for speech sampling")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    results = []
    for digest, url in selected:
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "sample.wav"
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                       "-rw_timeout", "8000000", "-i", url, "-t", str(args.seconds),
                       "-vn", "-ac", "1", "-ar", "16000", "-y", str(wav)]
            try:
                completed = subprocess.run(command, capture_output=True, timeout=45, check=False)
                if completed.returncode != 0 or not wav.exists() or wav.stat().st_size < 16000:
                    results.append({"url_sha256": digest, "status": "AUDIO_SAMPLE_UNAVAILABLE", "approved": False})
                    continue
                segments, info = model.transcribe(str(wav), beam_size=1, vad_filter=True)
                transcript = " ".join(s.text.strip() for s in segments).strip()
                results.append({"url_sha256": digest, "status": "LANGUAGE_MODEL_HINT_ONLY",
                                "detected_language": info.language, "language_probability": round(info.language_probability, 4),
                                "speech_detected": bool(transcript), "approved": False,
                                "spoken_turkish_verified": False})
            except (subprocess.TimeoutExpired, OSError, ValueError, RuntimeError, TypeError) as exc:
                results.append({"url_sha256": digest, "status": "SAMPLE_ERROR", "error_type": type(exc).__name__, "approved": False})
    output = {"policy": "READ_ONLY_SAMPLED_ASR_HINTS_REQUIRE_REVIEW", "sampled": len(results),
              "model": "faster-whisper tiny", "seconds_per_stream": args.seconds,
              "limitations": "Language detection is probabilistic; silence, music and multilingual streams can mislead. No automatic verification or promotion.",
              "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sampled": len(results), "turkish_hints": sum(x.get("detected_language") == "tr" and x.get("speech_detected", False) for x in results)}))

if __name__ == "__main__":
    run()
