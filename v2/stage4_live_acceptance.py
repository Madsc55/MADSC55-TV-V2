"""Create and verify the receipt for the live Stage 4 Actions archive."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys

from encrypted_archive import archive_manifest, restore_verified
from historical_url_recovery import read_records
from live_archive_key import resolve_key

HISTORY = Path("v2/history/stage3-4955-hash-only.jsonl")
HISTORY_SHA = "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def acceptance_key():
    key, _ = resolve_key(os.environ.pop("CONFIGURED_ARCHIVE_KEY", ""),
                         os.environ.pop("CONFIGURED_ARCHIVE_PASSPHRASE", ""))
    context = f"stage4-24:{os.environ['GITHUB_REPOSITORY_ID']}:{os.environ['GITHUB_RUN_ID']}"
    return hmac.new(bytes.fromhex(key), context.encode(), hashlib.sha256).hexdigest()


def build(target, key):
    require(hashlib.sha256(HISTORY.read_bytes()).hexdigest() == HISTORY_SHA,
            "Historical baseline digest mismatch")
    result = subprocess.run(
        [sys.executable, "v2/master_engine.py", "--history", str(HISTORY),
         "--archive", str(target / "inventory.enc"), "--out", str(target / "output"),
         "--archive-only", "--workers", "16", "--max-seconds", "5400"],
        env={**os.environ, "V2_ARCHIVE_KEY_HEX": key},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6100,
    )
    report_path = target / "output/report.json"
    if not report_path.is_file():
        raise ValueError(f"Live Master emitted no report (exit {result.returncode})")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    print(json.dumps({k: report[k] for k in (
        "status", "configured_sources", "fetched_sources", "unique_candidates",
        "media_decoded", "verification_unfinished", "ffmpeg_failure_categories",
    )}, sort_keys=True))
    require(result.returncode == 0, f"Live Master failed (exit {result.returncode})")
    gates = report["acceptance_gates"]
    for gate in ("source_fetch_complete", "av_verification_complete",
                 "historical_baseline_4955_present", "encrypted_archive_roundtrip"):
        require(gates[gate] is True, f"Master acceptance gate failed: {gate}")
    for field in ("protected_playlist_unchanged", "verification_complete", "checkpoint_encrypted"):
        require(report[field] is True, f"Master verification failed: {field}")
    for field in ("budget_exhausted", "plaintext_playlist_written", "approved", "device_verified"):
        require(report[field] is False, f"Unexpected Master result: {field}")
    require(report["verification_unfinished"] == 0, "Unfinished AV verification")
    require(report["media_decoded"] > 0, "No decoded video and audio")
    receipt = {
        "run_id": os.environ["GITHUB_RUN_ID"],
        "engine_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "archive": archive_manifest(target / "inventory.enc", key),
        "candidates": report["unique_candidates"],
        "all_regions_av": report["all_regions_media_decoded"],
        "tr_az_av": report["media_decoded"],
        "sources_fetched": report["fetched_sources"],
        "historical_records": report["historical_raw_records_preserved"],
        "engine_playlist_sha256": report["protected_playlist_sha256_after"],
    }
    require(receipt["sources_fetched"] > 0, "No real sources fetched")
    (target / "receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as out:
        digest = hashlib.sha256((target / "receipt.json").read_bytes()).hexdigest()
        out.write(f"receipt_digest={digest}\n")


def verify(target, key):
    receipt_bytes = (target / "receipt.json").read_bytes()
    require(hashlib.sha256(receipt_bytes).hexdigest() == os.environ["EXPECTED_RECEIPT"],
            "Downloaded receipt differs from producer receipt")
    receipt = json.loads(receipt_bytes)
    require(receipt["run_id"] == os.environ["GITHUB_RUN_ID"], "Archive belongs to another Actions run")
    archive = target / "inventory.enc"
    archive.chmod(0o600)
    rows = restore_verified(archive, receipt["archive"], key)
    history, candidates = [], []
    for row in rows:
        if row.get("kind") == "raw_historical_evidence":
            history.extend(row["records"])
        else:
            candidates.append(row)
    require(len(history) == receipt["historical_records"] == 4955
            and history == list(read_records(HISTORY)), "Original history was not restored exactly")
    require(len(candidates) == receipt["candidates"], "Candidate count changed on restore")
    require(all(row.get("verification_status") == "CHECKED"
                and type(row.get("media_decoded")) is bool
                and row.get("device_verified") is False for row in candidates),
            "Restored candidate has incomplete or invalid evidence")
    decoded = [row for row in candidates if row["media_decoded"]]
    require(all(row.get("network_status") == "HLS_MANIFEST_REACHABLE" for row in decoded)
            and len(decoded) == receipt["all_regions_av"]
            and sum(row.get("region_candidate") in ("TR", "AZ") for row in decoded)
                == receipt["tr_az_av"] > 0, "Restored AV evidence differs from Master results")
    receipt["restored_from"] = "github-actions-artifact-independent-runner"
    receipt["restored_records"] = len(rows)
    (target / "accepted.json").write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    try:
        mode, directory = sys.argv[1:]
        {"build": build, "verify": verify}[mode](Path(directory), acceptance_key())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"Stage 4 acceptance blocked: {exc}") from None
