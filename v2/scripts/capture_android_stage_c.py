#!/usr/bin/env python3
"""Collect real Android/IBO device diagnostics through ADB without claiming AV acceptance.

Requires a locally attached, authorized Android device and adb. Does not edit
playlists or change task state. Audio/video playback must be reviewed separately.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

def run(*args):
    return subprocess.run(["adb", *args], capture_output=True, text=True, timeout=30, check=True).stdout.strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument("--channel-id", required=True)
    args = parser.parse_args()
    devices = [line.split()[0] for line in run("devices").splitlines()[1:] if line.endswith("\tdevice")]
    if len(devices) != 1:
        raise SystemExit(f"Exactly one authorized physical Android device required; found {len(devices)}")
    serial = devices[0]
    model = run("-s", serial, "shell", "getprop", "ro.product.model")
    emulator = run("-s", serial, "shell", "getprop", "ro.kernel.qemu")
    if emulator == "1" or serial.startswith("emulator-"):
        raise SystemExit("Emulator is not accepted for Stage C")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    capture = args.output_dir / "android-screen.png"
    with capture.open("wb") as out:
        subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"],
                       stdout=out, check=True, timeout=30)
    digest = hashlib.sha256(capture.read_bytes()).hexdigest()
    receipt = {
        "schema": 1, "environment": "physical_android", "mock": False,
        "passed": False, "device_id": hashlib.sha256(serial.encode()).hexdigest()[:16],
        "device_model": model, "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "channel_id": args.channel_id,
        "capture": {"path": capture.name, "sha256": digest},
        "video_ok": None, "audio_ok": None, "same_session": None,
        "note": "Screenshot alone cannot prove audio or continuous playback; independent human/device review required."
    }
    (args.output_dir / "android-capture-receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"capture": str(capture), "receipt": str(args.output_dir / "android-capture-receipt.json"),
                      "accepted": False}, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        sys.exit(f"ADB capture failed: {exc}")
