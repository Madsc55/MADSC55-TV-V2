#!/usr/bin/env python3
"""Read-only TR/AZ M3U candidate video+audio acceptance.

Filters only metadata or approved TR/AZ source hints; this cannot prove
spoken language and is NOT complete worldwide discovery. URLs appear
only inside RSA-encrypted .sealed artifacts, never in public JSON.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import time

from final_batch_acceptance import (
    ROOT, LIVE, LIVE_BLOB, HISTORY, HISTORY_SHA, REPORTS,
    sha, gitblob, sources, fetch_one, route, probe, report,
)
from stage3_sealed_export import seal_rows

KEY = ROOT / "v2/config/stage5_recovery_public.pem"
OUTPUT = REPORTS / "targeted-tr-az-acceptance.json"
HASH = re.compile(r"[0-9a-f]{64}\Z")
SEALED = re.compile(r"target-traz-[0-9]{3}\.sealed\Z")


def target_hint(item):
    """Only source scope or explicit channel metadata; not spoken-language proof."""
    scopes = item["scopes"]
    if "TR" in scopes or "AZ" in scopes:
        return True
    return route(item["meta"], scopes) in ("TR_METADATA_HINT", "AZ_METADATA_HINT")


def selected_inventory(inventory):
    """Preserve SHA identities; don't rewrite source provenance or remove history."""
    return {digest: item for digest, item in inventory.items() if target_hint(item)}


def build_inventory(outputs, all_sources):
    scopes = {s["id"]: s.get("scope", "candidate") for s in all_sources}
    inventory = {}
    for sid, rows, status in outputs:
        if status != "FETCHED":
            continue
        for row in rows:
            url = row["url"]
            digest = sha(url)
            old = inventory.setdefault(digest, {
                "url": url, "meta": row, "source_ids": set(),
                "scopes": set()})
            if old["url"] != url:
                raise ValueError("URL_SHA256_COLLISION")
            old["source_ids"].add(sid)
            old["scopes"].add(scopes[sid])
    return inventory


def validate(path, require_complete=False):
    """Verify anonymous JSON and encrypted file manifest, not media playback."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or data.get("kind") != "V2_TR_AZ_METADATA_SCOPED_AV":
        raise ValueError("INVALID_TARGET_REPORT_SCHEMA")
    for label, expect in {
        "protected_main_playlist_modified": False,
        "ibo_player_verified": False,
        "spoken_language_verified": 0,
        "plaintext_url_in_public_report": False,
        "selection_is_spoken_language_proof": False,
    }.items():
        if type(expect) is bool:
            valid = data.get(label) is expect
        else:
            valid = data.get(label) == expect
        if not valid:
            raise ValueError("UNSUPPORTED_AV_OR_LANGUAGE_CLAIM_" + label)
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("MISSING_TARGET_CANDIDATES")
    n = data.get("target_url_candidates")
    total = data.get("total_discovered_url_candidates")
    if type(n) is not int or type(total) is not int or n <= 0 or n > total:
        raise ValueError("INVALID_TARGET_COUNTS")
    if len(candidates) != n or data.get("excluded_from_target_scope") != total-n:
        raise ValueError("INVALID_TARGET_CANDIDATE_COUNT")
    hashes = set()
    decoded = 0
    unprobed = 0
    statuses = Counter()
    for row in candidates:
        h = row.get("url_sha256")
        if not isinstance(h, str) or not HASH.fullmatch(h) or h in hashes:
            raise ValueError("INVALID_OR_REPEATED_TARGET_HASH")
        hashes.add(h)
        if any(key in row for key in ("url", "stream_url", "raw_url", "href")):
            raise ValueError("PLAINTEXT_URL_FIELD")
        if "://" in json.dumps(row, ensure_ascii=False):
            raise ValueError("PLAINTEXT_URL_IN_REPORT")
        if row.get("ibo_player_verified") is not False or row.get("spoken_language_verified") is not False:
            raise ValueError("FALSE_PLAYBACK_OR_LANGUAGE_PROOF")
        if (not isinstance(row.get("source_ids"),list) or not row["source_ids"] or
                not isinstance(row.get("language_route"),str) or
                not row["language_route"] or
                any(type(row.get(k)) is not bool for k in ("video","audio","decoded"))):
            raise ValueError("INVALID_CANDIDATE_EVIDENCE")
        st = row.get("status")
        if st == "NOT_PROBED_BUDGET":
            unprobed += 1
        else:
            if not isinstance(st, str) or not st:
                raise ValueError("EMPTY_PROBE_STATUS")
            statuses[st] += 1
        if row.get("decoded") is True:
            if row.get("video") is not True or row.get("audio") is not True or st != "VIDEO_AUDIO_DECODED":
                raise ValueError("FALSE_DECODE_PROOF")
            decoded += 1
    if (data.get("probed") != n-unprobed or data.get("unprobed") != unprobed or
            data.get("audio_video_decoded") != decoded or
            data.get("av_status_counts") != dict(statuses)):
        raise ValueError("INVALID_PROBE_AGGREGATES")
    manifest = data.get("sealed_artifacts")
    if not isinstance(manifest, list) or len(manifest) != (n+3999)//4000:
        raise ValueError("MISSING_ENCRYPTED_MANIFEST")
    names = set()
    count = 0
    for chunk in manifest:
        name, digest, size = chunk.get("name"), chunk.get("sha256"), chunk.get("count")
        if (not isinstance(name, str) or not SEALED.fullmatch(name)
                or name in names or not isinstance(digest, str)
                or not HASH.fullmatch(digest) or type(size) is not int
                or not 0 < size <= 4000):
            raise ValueError("INVALID_ENCRYPTED_CHUNK")
        names.add(name)
        file = path.parent / name
        if not file.is_file() or sha(file.read_bytes()) != digest:
            raise ValueError("INVALID_ENCRYPTED_CHECKSUM")
        try:
            envelope=json.loads(file.read_text(encoding="utf-8"))
        except (ValueError,UnicodeError):
            raise ValueError("INVALID_ENCRYPTED_ENVELOPE") from None
        if (not isinstance(envelope,dict) or envelope.get("schema")!=1 or
                envelope.get("kind")!="RSA_OAEP_SHA256_AES256_GCM_ZLIB" or
                envelope.get("records_encrypted")!=size or
                not all(isinstance(envelope.get(k),str) and envelope.get(k)
                        for k in ("nonce","wrapped_key","ciphertext"))):
            raise ValueError("INVALID_ENCRYPTED_ENVELOPE")
        count += size
    if count != n or data.get("sealed_url_count") != n:
        raise ValueError("ENCRYPTED_URL_COVERAGE_MISMATCH")
    if type(data.get("source_fetch_failures")) is not int or data["source_fetch_failures"] < 0:
        raise ValueError("INVALID_SOURCE_FAILURE_COUNT")
    if require_complete and (unprobed or data["source_fetch_failures"]):
        raise ValueError("INCOMPLETE_TARGET_SOURCE_OR_PROBE_COVERAGE")
    complete = not unprobed and data["source_fetch_failures"] == 0
    return {
        "status": ("TARGET_METADATA_SCOPE_PROBE_COMPLETE" if complete
                   else "TARGET_METADATA_SCOPE_PARTIAL"),
        "total_discovered_urls": total,
        "included_target_urls": n,
        "excluded_without_tr_az_metadata_or_source_hint": total-n,
        "unprobed": unprobed,
        "decoded_video_audio": decoded,
        "source_coverage_complete": data["source_fetch_failures"] == 0,
        "rsa_encrypted_urls_preserved": count,
        "ibo_device_verified": False, "spoken_language_verified": False,
    }


def scan(workers=32, budget_seconds=7200, require_public_sources=True):
    if sha(HISTORY.read_bytes()) != HISTORY_SHA or gitblob(LIVE.read_bytes()) != LIVE_BLOB:
        raise ValueError("PROTECTED_DATA_FINGERPRINT_CHANGED")
    started = time.monotonic()
    all_sources, configured, historic = sources(
        require_public_reports=require_public_sources)
    with ThreadPoolExecutor(max_workers=12) as executor:
        outputs = list(executor.map(fetch_one, all_sources))
    all_inventory = build_inventory(outputs, all_sources)
    target = selected_inventory(all_inventory)
    if not target:
        raise ValueError("NO_TARGET_METADATA_HINT_CANDIDATES")
    checks = {}
    expired = False
    items = sorted(target.items())
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for offset in range(0, len(items), 128):
            if time.monotonic() - started >= budget_seconds:
                expired = True
                break
            batch = [(digest, item["url"]) for digest, item in items[offset:offset+128]]
            for proof in pool.map(probe, batch):
                checks[proof["url_sha256"]] = proof
            if offset % 1280 == 0:
                print("TR_AZ_TARGET_AV_PROBED", len(checks), "/", len(items), flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    encrypted = []
    for index, offset in enumerate(range(0, len(items), 4000), 1):
        chunk = items[offset:offset+4000]
        rows = []
        for digest, item in chunk:
            status = checks.get(digest, {
                "status": "NOT_PROBED_BUDGET",
                "video": False, "audio": False, "decoded": False,
            })
            rows.append({
                "url": item["url"], "url_sha256": digest,
                "source_ids": sorted(item["source_ids"]),
                "metadata_route": route(item["meta"], item["scopes"]),
                "video_stream": status["video"], "audio_stream": status["audio"],
                "av_decode_verified": status["decoded"], "probe_status": status["status"]})
        out = REPORTS / ("target-traz-%03d.sealed" % index)
        seal_rows(rows, KEY, out)
        encrypted.append({"name": out.name, "count": len(rows),
                          "sha256": sha(out.read_bytes())})
    result = report(outputs, target, checks, configured=configured,
                    historic=historic, expired=expired,
                    elapsed=time.monotonic()-started)
    result["kind"] = "V2_TR_AZ_METADATA_SCOPED_AV"
    result["target_url_candidates"] = len(target)
    result["total_discovered_url_candidates"] = len(all_inventory)
    result["excluded_from_target_scope"] = len(all_inventory)-len(target)
    result["selection_is_spoken_language_proof"] = False
    result["selection_policy"] = "TR_AZ_CONFIG_SOURCE_SCOPE_OR_EXPLICIT_METADATA_HINT"
    result["source_fetch_failures"] = sum(r[2] != "FETCHED" for r in outputs)
    result["sealed_url_count"] = sum(item["count"] for item in encrypted)
    result["sealed_artifacts"] = encrypted
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print("TR_AZ_TARGET_SUMMARY", json.dumps({key: result[key] for key in (
        "target_url_candidates","total_discovered_url_candidates",
        "excluded_from_target_scope","probed","unprobed","source_fetch_failures",
        "audio_video_decoded","sealed_url_count")}, sort_keys=True))
    return validate(OUTPUT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--budget-seconds", type=int, default=7200)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        result = validate(OUTPUT, require_complete=args.require_complete)
    else:
        if not 1 <= args.workers <= 32 or not 60 <= args.budget_seconds <= 14400:
            parser.error("Unsafe AV scan limits")
        result = scan(workers=args.workers, budget_seconds=args.budget_seconds)
        if args.require_complete:
            result = validate(OUTPUT, require_complete=True)
    print("TR_AZ_TARGET_ACCEPTANCE", json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
