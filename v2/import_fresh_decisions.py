"""Attach the two reviewed November AV reports to the authenticated worldwide checkpoint."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from nonforeign_fresh_full import inventory
from scan_checkpoint import _read_progress_rows, save_progress
from secure_archive import atomic_write, decrypt, encrypt

PLAYLIST_SHA = "265f368758e75c5b18bc1b936a9792fef36528ba486288ddb35e4e7e23775ecf"
BASE_CIPHER_SHA = "7327c323864bbb991428bea609f3bf439968637a2d30a6215df50f2d242ecd32"
REPORTS = (
    ("2026-11-25", 45515390523, 15007854439, "nonforeign", 2390,
     "40ff3f514e4a41d806c37fa2b01175281a1077b365dd0c56711d72761cd7d17d"),
    ("2026-11-26", 45799091422, 15147217790, "yedekler", 1562,
     "dbdbdc6d1d19d343bdb1b7693649c83537d8ba40e9a6da7ad13e8374102ad99d"),
)
BASE = "before.enc"
CHECKPOINT = "ibo-scan-progress.enc"
OBSERVATIONS = "fresh-observations.zip.enc"
RECEIPT = "receipt.json"
ROW_COUNT = 28844


def digest(data):
    return sha256(data).hexdigest()


def read_reports(archive, playlist):
    if digest(playlist) != PLAYLIST_SHA:
        raise ValueError("Unexpected source playlist")
    observations = defaultdict(dict)
    with ZipFile(io.BytesIO(archive)) as source:
        if sorted(source.namelist()) != sorted(date + ".json" for date, *_ in REPORTS):
            raise ValueError("Unexpected report set")
        for date, run, artifact, scope, count, expected_hash in REPORTS:
            member = source.getinfo(date + ".json")
            if member.file_size > 10_000_000:
                raise ValueError("Oversized report")
            data = source.read(member)
            if digest(data) != expected_hash:
                raise ValueError("Unreviewed report bytes")
            report = json.loads(data)
            canonical = inventory(playlist, scope)
            results = report["results"]
            if (report.get("complete") is not True or report["playlist_sha256"] != PLAYLIST_SHA
                    or report.get("scope", "nonforeign") != scope
                    or len(results) != len(canonical) or report["total"] != len(results)
                    or len(results) != count):
                raise ValueError("Incomplete report coverage")
            for row, expected in zip(results, canonical):
                if any(row[k] != expected[k] for k in ("position", "category", "record_sha256", "url_sha256")):
                    raise ValueError("Observation does not match the source record")
                valid_round_counts = (3,) if date == "2026-11-26" else (1, 2, 3)
                if not row["url_sha256"] or len(row.get("rounds", ())) not in valid_round_counts:
                    raise ValueError("Missing URL identity or timed rounds")
                observation_key = f"{run}/{row['position']}"
                group = observations[row["url_sha256"]]
                if observation_key in group:
                    raise ValueError("Duplicate observation")
                group[observation_key] = {"date": date, "run_id": run, "artifact_id": artifact, "observation": row}
    return observations


def attach(rows, observations):
    """Keep the scanner's result, freshness, retries and older diagnostics verbatim."""
    result = dict(rows)
    applied = Counter()
    matched = set()
    for url, original in rows.items():
        identifier = original["url_sha256"]
        if identifier not in observations:
            continue
        if identifier in matched:
            raise ValueError("Ambiguous checkpoint URL hash")
        matched.add(identifier)
        diagnostics = original["diagnostics"]
        history = dict(diagnostics.get("fresh_av_history", {}))
        before = len(history)
        for key, value in observations[identifier].items():
            if key in history:
                if history[key] != value:
                    raise ValueError("Existing observation differs")
                continue
            history[key] = value
            applied[str(value["run_id"])] += 1
        if len(history) != before:
            result[url] = {**original, "diagnostics": {**diagnostics, "fresh_av_history": history}}
    return result, matched, dict(applied)


def verified_base(path, secret):
    if path.is_symlink() or digest(path.read_bytes()) != BASE_CIPHER_SHA:
        raise ValueError("Unexpected encrypted source")
    rows = _read_progress_rows(path, secret, worldwide=True)
    if len(rows) != ROW_COUNT:
        raise ValueError("Unexpected checkpoint row count")
    return rows


def evidence_receipt(before, observations, matched, added):
    return {
        "playlist_sha256": PLAYLIST_SHA, "source_checkpoint_sha256": BASE_CIPHER_SHA,
        "checkpoint_rows": len(before),
        "prior_positive_rows_preserved": sum(x["result"] is not None for x in before.values()),
        "source_observations": sum(map(len, observations.values())),
        "source_unique_urls": len(observations), "matched_checkpoint_urls": len(matched),
        "unmatched_unique_urls": len(observations) - len(matched),
        "attached_observations_by_run": added,
        "unmatched_observations_in_encrypted_ledger": sum(len(v) for k, v in observations.items() if k not in matched),
        "report_sha256": {str(run): sha for _,run,_,_,_,sha in REPORTS},
    }


def verify(bundle, playlist, secret):
    original = verified_base(bundle / BASE, secret)
    archive = decrypt((bundle / OBSERVATIONS).read_bytes(), secret)
    obs = read_reports(archive, playlist)
    expected, matched, added = attach(original, obs)
    actual = _read_progress_rows(bundle / CHECKPOINT, secret, worldwide=True)
    if expected != actual:
        raise ValueError("Independent restore mismatch")
    replay, _, changes = attach(actual, obs)
    if changes or replay != actual:
        raise ValueError("Replay changed authenticated history")
    receipt = evidence_receipt(original, obs, matched, added)
    receipt.update(
        checkpoint_sha256=digest((bundle / CHECKPOINT).read_bytes()),
        observations_sha256=digest((bundle / OBSERVATIONS).read_bytes()),
        restored_rows=len(actual), replay_insertions=0,
    )
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["build", "verify"])
    p.add_argument("--playlist", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--source", type=Path)
    p.add_argument("--reports", type=Path)
    args = p.parse_args()
    secret = os.environ.get("V2_ARCHIVE_PASSPHRASE")
    if not secret:
        p.error("Authenticated archive key is unavailable")
    raw = args.playlist.read_bytes()
    bundle = args.bundle
    if args.operation == "build":
        if not args.source or not args.reports:
            p.error("Build requires the encrypted source and both reports")
        before = verified_base(args.source, secret)
        buf = io.BytesIO()
        with ZipFile(buf, "w", compression=ZIP_DEFLATED) as out:
            for date, *_ in REPORTS:
                name = date + ".json"
                out.write(args.reports / name, name)
        data = buf.getvalue()
        rows, _, _ = attach(before, read_reports(data, raw))
        bundle.mkdir(mode=0o700)
        shutil.copyfile(args.source, bundle / BASE)
        atomic_write(bundle / OBSERVATIONS, encrypt(data, secret))
        if rows == before:
            shutil.copyfile(args.source, bundle / CHECKPOINT)
        else:
            save_progress(bundle / CHECKPOINT, secret, worldwide=True, rows=rows)
    receipt = verify(bundle, raw, secret)
    if args.operation == "build":
        atomic_write(bundle / RECEIPT, (json.dumps(receipt, indent=2) + "\n").encode())
    elif json.loads((bundle / RECEIPT).read_bytes()) != receipt:
        raise ValueError("Restore receipt mismatch")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
