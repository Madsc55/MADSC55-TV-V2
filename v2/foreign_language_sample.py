"""Bounded local-only language observations; hints never authorize a move."""
import subprocess
import tempfile
from pathlib import Path
from v2.spoken_language_sample_review import transcribe_sample
from v2.turkish_asr_ocr_evidence import evaluate_observation
from v2.turkish_webvtt_evidence import review_decoded_cues
from v2.backup_text_evidence import inspect_text_observations

def sample(data, fmt, exe, model):
    if fmt not in ("mov","mpegts") or len(data)>72*1024*1024:
        raise ValueError("Invalid local sample")
    result={"asr":{"status":"UNAVAILABLE"},"ocr":{"status":"UNAVAILABLE"},
            "webvtt":{"status":"UNAVAILABLE"},"identity_verified":False}
    def decode(args):
        return subprocess.run([exe,"-nostdin","-hide_banner","-loglevel","error",
            "-threads","1","-protocol_whitelist","pipe","-f",fmt,"-i","pipe:0",
            *args],input=data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            timeout=45,check=False)
    try:
        audio=decode(["-map","0:a:0","-t","20","-ac","1","-ar","16000","-f","wav","pipe:1"])
        if audio.returncode==0 and 16000<len(audio.stdout)<1000000:
            with tempfile.TemporaryDirectory() as d:
                wav=Path(d)/"audio.wav"
                wav.write_bytes(audio.stdout)
                result["asr"]=transcribe_sample(wav,model)
                if result["asr"]["speech_detected"]:
                    result["asr"]["review"]=evaluate_observation("sample",{
                        "source":"asr","language":result["asr"]["detected_language"],"text":"speech detected"})
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired):
        result["asr"]={"status":"SAMPLE_ERROR"}
    try:
        frame=decode(["-map","0:v:0","-frames:v","1","-vf","scale=640:-2","-f","image2pipe","-vcodec","png","pipe:1"])
        if frame.returncode==0 and 0<len(frame.stdout)<4000000:
            ocr=subprocess.run(["tesseract","stdin","stdout","-l","tur+eng"],input=frame.stdout,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=25,check=False)
            if ocr.returncode==0:
                value=ocr.stdout.decode("utf-8",errors="replace")[:4096]
                result["ocr"]=inspect_text_observations([{"kind":"OCR","text":value}])
    except (OSError,ValueError,subprocess.TimeoutExpired):
        result["ocr"]={"status":"SAMPLE_ERROR"}
    try:
        subs=decode(["-map","0:s:0","-t","60","-c:s","webvtt","-f","webvtt","pipe:1"])
        if subs.returncode==0 and 0<len(subs.stdout)<=262144:
            result["webvtt"]=review_decoded_cues(subs.stdout.decode("utf-8",errors="replace"),"",60000)
    except (OSError,ValueError,subprocess.TimeoutExpired):
        result["webvtt"]={"status":"SAMPLE_ERROR"}
    return result
