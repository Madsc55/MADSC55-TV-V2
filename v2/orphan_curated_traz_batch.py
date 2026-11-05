#!/usr/bin/env python3
"""One read-only batch: exact old 50 IDs vs 2 pinned TR/AZ public M3U feeds.

Only new, hash-validated exact source matches are FFprobed and FFmpeg-decoded.
Neither prior failed URLs nor source-level coincidences count as playable.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from orphan_baseline_guard import load_immutable_baseline, reconcile_immutable_sources
from orphan_m3u_recovery import (
    ORIGINALS, ONUR_SOURCES, _read_document, _hash, evaluate,
    find_existing_exact_identity, restore_exact_original_metadata_from_official_alternates,
)
from orphan_curated_traz_sources import pinned_traz_candidate_references
from stage3_sealed_export import seal_rows

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "history/m3u-orphan-50-hash-baseline.json"
KEY = ROOT / "config/stage3_transit_public.pem"


def original_targets(baseline, documents):
    if set(documents) != set(baseline["sources"]):
        raise ValueError("Four original source documents are required")
    evidence = reconcile_immutable_sources(baseline, documents)
    if evidence["original_source_occurrences"] != 55:
        raise ValueError("Wrong historical occurrences")
    targets = {}
    occurrences = 0
    for sid, expected in baseline["sources"].items():
        available = {}
        for raw in documents[sid].splitlines():
            extinf = raw.strip()
            if extinf.startswith("#EXTINF:"):
                digest = _hash(extinf)
                if digest in expected:
                    available[digest] = extinf
        if set(available) != set(expected):
            raise ValueError("Missing original source metadata in current published feeds")
        occurrences += len(expected)
        for digest in sorted(expected):
            old = targets.setdefault(digest, {"source_id": sid,
                "extinf_sha256": digest, "extinf": available[digest],
                "candidates": {}})
            if old["extinf"] != available[digest]:
                raise ValueError("Contradictory exact original channel metadata")
    if occurrences != 55 or len(targets) != 50:
        raise ValueError("Immutable 55 records and 50 distinct channels required")
    return [targets[h] for h in sorted(targets)]


def source_documents(baseline, reader=_read_document):
    docs = {}
    for sid, repo, path in ORIGINALS:
        docs[sid] = reader("https://raw.githubusercontent.com/" +
                           repo + "/main/" + quote(path, safe="/"))
    for sid, url in ONUR_SOURCES:
        try:
            content = reader(url)
            if not content.lstrip("\ufeff\r\n\t ").startswith(("#EXTM3U", "#EXTINF:")):
                raise ValueError("Publisher did not return M3U content")
            docs[sid] = content
        except (OSError, TypeError, ValueError):
            docs[sid] = restore_exact_original_metadata_from_official_alternates(
                sid, baseline, reader=reader)
    return docs


def inspect_new_sources(targets, *, matcher=find_existing_exact_identity,
                        prober=evaluate):
    refs = pinned_traz_candidate_references()
    matched, scan = matcher(targets, refs)
    expected = {row["extinf_sha256"] for row in targets}
    if not set(matched).issubset(expected):
        raise ValueError("Candidate source returned an unrelated identity")
    relevant = []
    for row in targets:
        candidates = matched.get(row["extinf_sha256"], {})
        if not isinstance(candidates, dict):
            raise ValueError("Invalid candidate source record")
        if not candidates:
            continue
        for digest, value in candidates.items():
            if (not isinstance(value, dict) or
                    not isinstance(value.get("url"), str) or
                    hashlib.sha256(value["url"].encode("utf-8")).hexdigest() != digest):
                raise ValueError("New URL did not match exact SHA256 proof")
        relevant.append({**row, "candidates": candidates})
    if relevant:
        checks, successes, owners = prober(relevant)
    else:
        checks, successes, owners = [], [], {}
    verified = {x["url_sha256"] for x in checks
                if x.get("ffmpeg_video_audio_decoded") is True}
    if (len(verified) != len(successes) or
            any(x["url_sha256"] not in owners for x in successes)):
        raise ValueError("New real video/audio proof and SHA owners disagree")
    status_counts = Counter(x["status"] for x in checks)
    successes_by_identity = set()
    for sha in verified:
        successes_by_identity.update(x["extinf_sha256"] for x in owners[sha])
    report = {
        "schema": 1, "kind": "V2_ORPHAN_50_TWO_NEW_PINNED_TRAZ_SOURCES",
        "source_references_checked": len(refs),
        "original_occurrences_preserved": 55,
        "original_channel_identities_preserved": 50,
        "distinct_original_identities_with_new_exact_source_candidates": len(relevant),
        "new_unique_exact_candidate_stream_urls": len(checks),
        "new_candidate_stream_urls_real_ffmpeg_decoded": len(verified),
        "original_identities_with_new_real_av_evidence": len(successes_by_identity),
        "still_without_new_exact_source_candidate": 50-len(relevant),
        "candidate_status_counts": dict(sorted(status_counts.items())),
        "new_exact_identity_hashes": sorted(matched),
        "new_av_verified_identity_hashes": sorted(successes_by_identity),
        "candidate_url_hashes": sorted(x["url_sha256"] for x in checks),
        "source_document_errors": scan.get("source_documents_unavailable_count"),
        "new_source_metadata_not_playback_proof": True,
        "old_125_candidates_not_reprobed": True,
        "main_playlist_modified": False, "ibo_device_verified": False,
        "plaintext_stream_urls_exposed": False,
        "all_50_recovered": False,
    }
    # An isolated incremental scan is not a 50/50 acceptance gate.
    # Existing four AV successes cannot be added without exact SHA crosscheck.
    if "://" in json.dumps(report):
        raise ValueError("Public report contains media address")
    sealed = []
    for sha in sorted(owners):
        found = owners[sha][0]["candidates"][sha]
        sealed.append({"url": found["url"], "url_sha256": sha,
                       "orphan_extinf_sha256": sorted({x["extinf_sha256"] for x in owners[sha]}),
                       "ffmpeg_video_audio_decoded": sha in verified,
                       "probe_status": next(x["status"] for x in checks if x["url_sha256"] == sha)})
    return report, sealed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--sealed", type=Path, required=True)
    a = p.parse_args()
    if (a.report.exists() or a.sealed.exists() or a.report.is_symlink()
            or a.sealed.is_symlink() or a.report.resolve() == a.sealed.resolve()):
        p.error("Refuse overwriting or overlapping anonymous/encrypted evidence")
    original = load_immutable_baseline(BASELINE)
    docs = source_documents(original)
    targets = original_targets(original, docs)
    result, sealed = inspect_new_sources(targets)
    if sealed:
        seal_rows(sealed, KEY, a.sealed)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    with a.report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print("ORPHAN_TWO_NEW_TRAZ_AV", json.dumps({
        k: v for k, v in result.items() if k not in
        ("new_exact_identity_hashes", "new_av_verified_identity_hashes",
         "candidate_url_hashes", "candidate_status_counts")
    }, sort_keys=True))


if __name__ == "__main__":
    main()
