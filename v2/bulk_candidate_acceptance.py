#!/usr/bin/env python3
"""Offline acceptance of authenticated API AV evidence into encrypted test batches.

No sources are fetched or streams re-probed. Plaintext URLs and M3U contents
exist only in memory; all source rows are retained in the original sealed file.
Metadata gaps remain explicit and do not become broadcaster/device approval.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric import rsa

from av_verified_sealed_ibo_export import select
from discover import ROOT
from epg_integrity import parse_xmltv_time
from stage3_sealed_export import open_rows, seal_rows
from validate_export_m3u import validate_m3u

CID = re.compile(r"[\w.+@()-]{1,160}\Z")
MAX_REPORT_BYTES = 20_000_000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_file(path, limit=MAX_REPORT_BYTES):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Missing, unsafe or oversized acceptance input")
    return path.read_bytes()


def xmltv_evidence(path):
    """Exact local snapshot IDs/intervals are mapping evidence, not identity proof."""
    if path is None:
        return {}, None
    raw = read_file(path)
    root = ET.fromstring(raw)
    if root.tag != "tv":
        raise ValueError("Expected an XMLTV snapshot")
    ids = Counter(node.get("id") for node in root.findall("channel") if node.get("id"))
    programmes = Counter()
    for node in root.findall("programme"):
        try:
            start = parse_xmltv_time(node.get("start", ""))
            stop = parse_xmltv_time(node.get("stop", ""))
        except ValueError:
            continue
        if stop > start:
            programmes[node.get("channel")] += 1
    return {cid: (count == 1 and programmes[cid] > 0) for cid, count in ids.items()}, sha(raw)


def measured_quality(public, private):
    """Accept dimensions only when bound to the same authenticated AV record."""
    left, right = public.get("video_streams"), private.get("video_streams")
    if left is None and right is None:
        return None
    if (left != right or not isinstance(left, list) or len(left) > 16
            or public.get("video_measurement_origin") != "FFPROBE_STREAM_METADATA"
            or private.get("video_measurement_origin") != "FFPROBE_STREAM_METADATA"):
        raise ValueError("Conflicting measured video metadata")
    measured = []
    for item in left:
        if (not isinstance(item, dict) or set(item) != {"width", "height", "codec_name"}
                or any(type(item[k]) is not int or not 0 < item[k] <= 16384 for k in ("width", "height"))
                or not isinstance(item["codec_name"], str)
                or not re.fullmatch(r"[A-Za-z0-9_]{1,40}", item["codec_name"])
                or item["codec_name"] == "unknown"):
            raise ValueError("Invalid measured video metadata")
        measured.append(dict(item))
    return max(measured, key=lambda item: (item["height"], item["width"])) if measured else None


def accept(report, rows, epg=None):
    """Validate all public/private identities, then losslessly partition outcomes."""
    # Reuse the established exact URL/SHA/channel-ID/decoded-video+audio gate.
    _, selected = select(report, rows)
    n = report.get("unique_url_candidates")
    if type(n) is not int or not 0 < n <= 4955:
        raise ValueError("Invalid real candidate inventory count")
    public = {item["url_sha256"]: item for item in report["streams"]}
    for name in ("spoken_language_verified", "sweden_access_verified"):
        if report.get(name) is not False:
            raise ValueError("Unsupported language or geographic verification claim")
    statuses = Counter(item.get("status") for item in public.values())
    unprobed = statuses["NOT_PROBED_BUDGET"]
    decoded = statuses["VIDEO_AUDIO_DECODED"]
    if (type(report.get("probed")) is not int or type(report.get("unprobed")) is not int
            or type(report.get("video_audio_decoded")) is not int
            or not isinstance(report.get("status_counts"), dict)
            or any(type(value) is not int or value < 0 for value in report["status_counts"].values())
            or report["probed"] != n - unprobed or report["unprobed"] != unprobed
            or report.get("video_audio_decoded") != decoded or report.get("status_counts") != dict(statuses)):
        raise ValueError("Inconsistent archived AV summary")
    eligible, outcomes = [], []
    epg = {} if epg is None else epg
    for row in rows:
        proof = public[row["url_sha256"]]
        ids = proof.get("channel_ids")
        if (not isinstance(ids, list) or not ids or len(set(ids)) != len(ids)
                or any(not isinstance(cid, str) or not CID.fullmatch(cid) for cid in ids)
                or row.get("channel_ids") != ids):
            raise ValueError("Invalid or conflicting exact channel IDs")
        if (any(type(proof.get(k)) is not bool or type(row.get(k)) is not bool
                or proof[k] != row[k] for k in ("video", "audio", "decoded"))
                or row.get("probe_status") != proof.get("status")):
            raise ValueError("Inconsistent authenticated AV flags")
        status = proof["status"]
        expected = {"VIDEO_AUDIO_DECODED": (True, True, True),
                    "VIDEO_AUDIO_STREAMS_ONLY": (True, True, False),
                    "VIDEO_ONLY": (True, False, False), "AUDIO_ONLY": (False, True, False),
                    "NO_AV": (False, False, False)}
        flags = tuple(proof[k] for k in ("video", "audio", "decoded"))
        if status in expected:
            valid = flags == expected[status]
        else:
            valid = (isinstance(status, str) and bool(re.fullmatch(
                r"PROBE_FAILED_[A-Z_]+|NOT_PROBED_BUDGET|PROBE_UNCONFIRMED|UNSAFE_OR_UNRESOLVED_HOST|UNVERIFIED", status))
                and flags == (False, False, False))
        if not valid:
            raise ValueError("Invalid archived AV status")
        quality = measured_quality(proof, row)
        outcome = ("PENDING_AV" if not proof["decoded"] else
                   "PENDING_AMBIGUOUS_IDENTITY" if len(ids) != 1 else "ELIGIBLE_PRIVATE_AV_TEST")
        pending = []
        if len(ids) != 1:
            pending.append("AMBIGUOUS_EXACT_CHANNEL_ID")
        if not proof["decoded"]:
            pending.append("VIDEO_AUDIO_DECODE_UNVERIFIED")
        # Matching API IDs are exact source metadata, never independent proof
        # of broadcaster ownership, spoken language or correct live content.
        pending.append("INDEPENDENT_BROADCASTER_IDENTITY_UNVERIFIED")
        if len(ids) != 1 or epg.get(ids[0]) is not True:
            pending.append("EXACT_XMLTV_ID_AND_PROGRAMMES_UNVERIFIED")
        if quality is None:
            pending.append("MEASURED_VIDEO_QUALITY_UNAVAILABLE")
        pending.append("PRODUCTION_CATEGORY_ASSIGNMENT_UNREVIEWED")
        outcomes.append({"url_sha256": row["url_sha256"], "channel_ids": ids,
                         "classification": outcome, "pending": pending,
                         "exact_authenticated_channel_ids_bound": True,
                         "measured_video": quality, "broadcaster_identity_verified": False,
                         "spoken_language_verified": False, "ibo_device_verified": False})
        if outcome == "ELIGIBLE_PRIVATE_AV_TEST":
            eligible.append(dict(row, export_channel_id=ids[0]))
    if len(eligible) != selected["verified_entries"] or len(outcomes) != n:
        raise ValueError("Lossless AV partition disagrees with existing export gate")
    eligible.sort(key=lambda row: (row["export_channel_id"], row["url_sha256"]))
    counts = dict(Counter(row["classification"] for row in outcomes))
    return eligible, {"candidate_count": n, "classification_counts": counts,
                      "eligible_unique_av_urls": len(eligible), "all_input_identities_preserved": True,
                      "metadata_acceptance_complete": False,
                      "pending_counts": dict(Counter(reason for item in outcomes for reason in item["pending"])),
                      "candidates": sorted(outcomes, key=lambda row: row["url_sha256"])}


def render(rows):
    lines = ["#EXTM3U"]
    for row in rows:
        cid = row["export_channel_id"]
        if not CID.fullmatch(cid):
            raise ValueError("Invalid export channel identity")
        lines.extend([f'#EXTINF:-1 tvg-id="{cid}" group-title="V2 PRIVATE AV TEST",{cid}', row["url"]])
    content = "\n".join(lines) + "\n"
    if validate_m3u(content):
        raise ValueError("M3U syntax/category/duplicate acceptance failed")
    return content


def export_batches(report_path, sealed_path, private_key, output, xmltv=None, require_complete=False):
    """Write new encrypted 1000/2000-record batches; never overwrite prior work."""
    output = Path(output)
    target = output.resolve(strict=False)
    reports = (ROOT / "v2/reports").resolve()
    if (output.exists() or output.is_symlink() or not output.name.startswith("private-")
            or (ROOT.resolve() in target.parents and reports not in target.parents)):
        raise ValueError("Output must be a new separate private export directory")
    raw_report, payload = read_file(report_path), read_file(sealed_path, 120_000_000)
    key_bytes = read_file(private_key, 64_000)
    key = serialization.load_pem_private_key(key_bytes, password=None)
    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 3072:
        raise ValueError("RSA-3072 or stronger acceptance key required")
    data = json.loads(raw_report)
    if not isinstance(data, dict):
        raise ValueError("Invalid accepted API report")
    manifest = data.get("encrypted_evidence", {})
    if (manifest.get("sha256") != sha(payload)
            or manifest.get("records") != data.get("unique_url_candidates")):
        raise ValueError("Archived report/sealed manifest mismatch")
    restored = open_rows(sealed_path, private_key)
    epg, epg_sha = xmltv_evidence(xmltv)
    eligible, summary = accept(data, restored, epg)
    if not eligible:
        raise ValueError("No individually decoded unambiguous AV candidates; refusing empty packages")
    if require_complete and not summary["metadata_acceptance_complete"]:
        raise ValueError("Metadata acceptance remains pending; refusing a complete-acceptance claim")
    summary.update({"schema": 1, "kind": "V2_ACCEPTED_ARCHIVE_ENCRYPTED_AV_TEST_BATCHES",
                    "status": "AV_TEST_BATCHES_READY_METADATA_PENDING",
                    "input_report_sha256": sha(raw_report), "input_sealed_sha256": sha(payload),
                    "xmltv_snapshot_sha256": epg_sha, "network_requests": 0,
                    "prior_av_reused_not_fresh": True, "plaintext_playlist_written": False,
                    "protected_playlist_modified": False, "ibo_device_verified": False,
                    "packages": [], "full_packages_by_size": {"1000": 0, "2000": 0}})
    # Build in an isolated sibling and publish the complete output directory once.
    # A readback/decryption verifies each package's real row count and exact M3U.
    with tempfile.TemporaryDirectory(prefix=".private-av-batches-", dir=output.parent) as temporary:
        stage = Path(temporary)
        public_path = stage / "recipient-public.pem"
        public_path.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                               serialization.PublicFormat.SubjectPublicKeyInfo))
        original = stage / "all-original-candidates.sealed"
        original.write_bytes(payload)
        original.chmod(0o600)
        for size in (1000, 2000):
            for part, offset in enumerate(range(0, len(eligible), size), 1):
                batch = eligible[offset:offset + size]
                content = render(batch)
                path = stage / f"ibo_{size}_PART{part:03d}.m3u.sealed"
                seal_rows(batch, public_path, path)
                opened = open_rows(path, private_key)
                if opened != batch or render(opened) != content:
                    raise ValueError("Encrypted package restore mismatch")
                full_size = len(batch) == size
                summary["full_packages_by_size"][str(size)] += int(full_size)
                summary["packages"].append({"name": path.name, "batch_size": size,
                    "records": len(batch), "full_size": full_size, "sealed_sha256": sha(path.read_bytes()),
                    "plaintext_m3u_sha256": sha(content.encode("utf-8")),
                    "restore_verified": True, "m3u_structure_verified": True})
        public_path.unlink()
        (stage / "acceptance.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if output.exists() or output.is_symlink():
            raise ValueError("Refuse to replace an output created during acceptance")
        stage.rename(output)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--sealed", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--xmltv", type=Path)
    parser.add_argument("--require-complete-metadata", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = export_batches(args.report, args.sealed, args.private_key, args.out,
                                args.xmltv, args.require_complete_metadata)
    except (ValueError, OSError, KeyError, TypeError, ET.ParseError, InvalidTag) as exc:
        # Never include exception text: parsers can echo private input contents.
        parser.exit(2, "Accepted archive batch validation failed: " + type(exc).__name__ + "\n")
    print(json.dumps({key: result[key] for key in ("status", "candidate_count", "eligible_unique_av_urls",
        "classification_counts", "pending_counts", "packages", "full_packages_by_size",
        "plaintext_playlist_written")}, sort_keys=True))


if __name__ == "__main__":
    main()
