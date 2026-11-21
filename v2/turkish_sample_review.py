"""Read the audio, picture and embedded subtitles of one local captured MKV."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import wave

from v2.backup_text_evidence import inspect_text_observations
from v2.ibo_archive_url_dedup import sha, urls
from v2.spoken_language_sample_review import transcribe_sample
from v2.turkish_channel_triage import classify_channel
from v2.turkish_local_media_probe import probe_local_sample, validate_sample
from v2.turkish_media_sample_capture import MAX_BYTES, MAX_SECONDS
from v2.turkish_webvtt_evidence import MAX_BYTES as MAX_VTT_BYTES, review_decoded_cues

MAX_FRAMES = 3
MAX_TRACKS = 4


def snapshot(source, target):
    """Pin all observations to the same private copy of the exact input bytes."""
    validate_sample(source)
    fd = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as src:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Expected regular MKV sample")
        data = src.read(MAX_BYTES + 1)
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError("Sample outside capture size limit")
    target.write_bytes(data)
    return hashlib.sha256(data).hexdigest(), len(data)


def decode(source, output, options, *, seek=0, limit):
    command = ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-max_alloc", "67108864",
               "-filter_threads", "1", "-protocol_whitelist", "file", "-f", "matroska",
               "-threads", "1", "-ss", str(seek), "-i", str(source), "-t", str(MAX_SECONDS),
               *options, "-threads", "1", "-fs", str(limit), "-n", str(output)]
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=18, check=False)
        return result.returncode == 0 and output.is_file() and 0 < output.stat().st_size < limit
    except (OSError, subprocess.TimeoutExpired):
        return False


def review_audio(source, root, model_dir):
    wav = root / "audio.wav"
    ok = decode(source, wav, ["-map", "0:a:0", "-ac", "1", "-ar", "16000",
                              "-c:a", "pcm_s16le"], limit=512 * 1024)
    if ok:
        try:
            with wave.open(str(wav), "rb") as sound:
                ok = bool(sound.readframes(1))
        except (OSError, EOFError, wave.Error):
            ok = False
    if not ok:
        return False, {"status": "NO_DECODED_AUDIO"}
    if model_dir is None:
        return True, {"status": "ASR_NOT_REQUESTED"}
    if not Path(model_dir).is_dir():
        return True, {"status": "ASR_LOCAL_MODEL_UNAVAILABLE"}
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(str(Path(model_dir).resolve()), device="cpu", compute_type="int8",
                             cpu_threads=2, local_files_only=True)
        return True, transcribe_sample(wav, model)
    except (ImportError, OSError, ValueError, RuntimeError, TypeError, AttributeError):
        return True, {"status": "ASR_UNAVAILABLE"}


def review_picture(source, root):
    frames = 0
    completed = 0
    texts = 0
    hint = False
    tesseract = shutil.which("tesseract")
    for index in range(MAX_FRAMES):
        frame = root / f"caption-{index}.png"
        # Lower half of the picture. A news ticker can also appear here.
        options = ["-map", "0:v:0", "-vf", "scale=w='min(960,iw)':h=-2,crop=iw:ih/2:0:ih/2",
                   "-frames:v", "1"]
        if not decode(source, frame, options, seek=index * 2, limit=3 * 1024 * 1024):
            continue
        frames += 1
        if not tesseract:
            continue
        try:
            result = subprocess.run([tesseract, str(frame), "stdout", "-l", "tur", "--psm", "6"],
                                    capture_output=True, timeout=12, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode:
            continue
        completed += 1
        text = result.stdout.decode("utf-8", errors="replace").strip()
        if text:
            texts += 1
            row = inspect_text_observations([{"kind": "OCR", "text": text[:4096]}])
            hint |= row["observations"][0]["turkish_review_hint"]
    return {"frames_decoded": frames, "ocr_frames_completed": completed,
            "frames_with_text": texts, "turkish_visible_text_hint": hint}


def review_subtitles(source, root, tracks):
    prioritized = sorted(tracks, key=lambda row: not row["turkish_subtitle_track_hint"])
    results = []
    for track in prioritized[:MAX_TRACKS]:
        index = track["stream_index"]
        output = root / f"track-{index}.vtt"
        decoded = decode(source, output, ["-map", f"0:{index}", "-f", "webvtt"],
                         limit=MAX_VTT_BYTES)
        row = {"stream_index": index, "language_tag": track["language_tag"],
               "status": "UNAVAILABLE", "tag_and_text_turkish_hint": False}
        if decoded:
            try:
                cues = review_decoded_cues(output.read_text(encoding="utf-8"),
                                           track["language_tag"], MAX_SECONDS * 1000)
                row.update(cues, status="TIMED_CUES" if cues["cue_count"] else "NO_TIMED_CUES")
            except (ValueError, OSError):
                pass
        results.append(row)
    return results


def review_sample(source, model_dir=None, capture_receipt=None, origin_country=None):
    with tempfile.TemporaryDirectory(prefix="turkish-review-") as directory:
        root = Path(directory)
        local = root / "sample.mkv"
        digest, size = snapshot(source, local)
        url_sha = None
        if capture_receipt is not None:
            if (not isinstance(capture_receipt, dict)
                    or capture_receipt.get("status") != "SAMPLE_CAPTURED_UNVERIFIED"
                    or capture_receipt.get("sample_sha256") != digest
                    or capture_receipt.get("bytes") != size
                    or not re.fullmatch("[0-9a-f]{64}", str(capture_receipt.get("url_sha256", "")))):
                raise ValueError("Capture receipt does not match sample")
            captured_at = capture_receipt.get("captured_at_utc")
            if captured_at is not None:
                try:
                    parsed_capture_time = datetime.datetime.fromisoformat(
                        captured_at.replace("Z", "+00:00"))
                except (AttributeError, TypeError, ValueError) as exc:
                    raise ValueError("Capture timestamp must be ISO-8601") from exc
                if parsed_capture_time.tzinfo is None or parsed_capture_time.utcoffset() is None:
                    raise ValueError("Capture timestamp must include a timezone")
            url_sha = capture_receipt["url_sha256"]
        metadata = probe_local_sample(local)
        audio, speech = review_audio(local, root, model_dir)
        picture = review_picture(local, root)
        tracks = metadata.get("subtitle_tracks", [])
        subtitles = review_subtitles(local, root, tracks)

    spoken = speech.get("detected_language") if speech.get("speech_detected") else None
    subtitled = any(row["tag_and_text_turkish_hint"] for row in subtitles)
    video = picture["frames_decoded"] > 0
    triage = classify_channel("sample", origin_country=origin_country, spoken_language=spoken,
                              subtitle_language="tr" if subtitled else None, video_decoded=video,
                              audio_decoded=audio, stream_checked=audio or video)
    reviewed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    timed_subtitles = any(row.get("cue_count", 0) > 0 for row in subtitles)
    provenance = {
        "source_identity": "url_sha256" if url_sha else "local_file_unattributed",
        "url_sha256": url_sha,
        "sample_sha256": digest,
        "captured_at_utc": capture_receipt.get("captured_at_utc") if capture_receipt else None,
        "reviewed_at_utc": reviewed_at,
        "capture_method": "bounded_ffmpeg_http_capture" if capture_receipt else "local_file_unattributed",
        "av_method": "ffmpeg_local_audio_video_decode",
        "asr_method": "faster_whisper_local_cpu_int8" if speech.get("status") == "LANGUAGE_MODEL_HINT_ONLY" else speech.get("status"),
        "asr_confidence": speech.get("language_probability"),
        "ocr_method": "tesseract_tur_psm6" if picture["ocr_frames_completed"] else "not_completed",
        "ocr_confidence": None,
        "subtitle_method": "ffmpeg_webvtt_timed_cue_review" if timed_subtitles else "not_completed",
        "subtitle_confidence": None,
    }
    return {"sample_sha256": digest, "url_sha256": url_sha, "bytes": size,
            "video_decoded": video, "audio_decoded": audio, "speech": speech, "picture": picture,
            "track_probe_status": metadata["status"], "subtitle_tracks": subtitles,
            "unexamined_tracks": len(tracks) - len(subtitles), "triage": triage,
            "evidence_provenance": provenance,
            "non_turkish_speech_with_turkish_cues_hint":
                bool(spoken and not triage["turkish_spoken_hint"] and subtitled),
            "device_verified": False, "review_approved": False, "playlist_modified": False}


def archive_preview(report, *, archive, state_path, decision=None):
    """Resolve a capture receipt against the immutable archive and current batch."""
    source_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state["source_sha256"] != source_digest:
        raise ValueError("Archive snapshot mismatch")
    url_digest = report.get("url_sha256")
    if not url_digest:
        raise ValueError("Archive preview needs the original capture receipt")
    positions = [i for i, url in enumerate(urls(archive), 1) if sha(url) == url_digest]
    if len(positions) != 1:
        raise ValueError("Channel identity missing or ambiguous in archive")
    index = positions[0]
    current = state["status"].get(str(index), "ANA_ARSIV")
    result = {"source_sha256": source_digest, "source_ordinal": index,
              "current_group": current, "target": None, "applied": False}
    if decision is None:
        return result
    required = {"sample_sha256", "url_sha256", "target", "reviewed_by", "basis"}
    if not isinstance(decision, dict) or set(decision) != required:
        raise ValueError("Incomplete reviewer decision")
    if (decision["sample_sha256"] != report["sample_sha256"] or decision["url_sha256"] != url_digest
            or not isinstance(decision["reviewed_by"], str) or not decision["reviewed_by"].strip()
            or decision["target"] not in ("TURK", "YABANCI") or current != "TEST"):
        raise ValueError("Decision does not match an active channel and sample")
    if not (report["video_decoded"] and report["audio_decoded"]):
        raise ValueError("Review requires decoded video and audio")
    allowed = {"heard_turkish": "TURK", "saw_turkish_subtitles": "TURK",
               "heard_foreign_and_reviewed_subtitles": "YABANCI"}
    if allowed.get(decision["basis"]) != decision["target"]:
        raise ValueError("Reviewer observation and archive target disagree")
    result["target"] = decision["target"]
    return result


def read_small_json(path):
    with path.open("rb") as source:
        data = source.read(16385)
    if len(data) > 16384:
        raise ValueError("Oversized review input")
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--local-asr-model", type=Path)
    parser.add_argument("--capture-receipt", type=Path, help="JSON from the capture command")
    parser.add_argument("--origin-country", help="Optional publisher metadata for triage")
    parser.add_argument("--archive-preview", action="store_true", help="Look up the captured channel in YEDEKLER")
    parser.add_argument("--reviewer-decision", type=Path, help="Human observation of this exact sample")
    args = parser.parse_args()
    if args.reviewer_decision and not args.archive_preview:
        parser.error("A reviewer decision requires --archive-preview")
    receipt = read_small_json(args.capture_receipt) if args.capture_receipt else None
    report = review_sample(args.sample, args.local_asr_model, receipt, args.origin_country)
    if args.archive_preview:
        folder = Path(__file__).resolve().parent / "yedekler_batch"
        decision = read_small_json(args.reviewer_decision) if args.reviewer_decision else None
        report["archive"] = archive_preview(report, archive=folder / "YEDEKLER_ARCHIVE.m3u8",
                                            state_path=folder / "state.json", decision=decision)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
