#!/usr/bin/env python3
"""Read-only, non-publishing Stage A progress audit of real GitHub Actions evidence.

A successful real IPTV scan is NOT proof that all publisher identities, retry
queues, EPG mappings, or worldwide discovery adapters have been accepted.
This report intentionally never changes task status, playlists, or archives.
"""
import argparse
import json
from pathlib import Path

TASK_IDS = (15, 17, 18, 19, 20, 21)


class InvalidEvidence(ValueError):
    pass


def number(doc, key):
    val = doc.get(key)
    if type(val) is not int or val < 0:
        raise InvalidEvidence("Missing or invalid nonnegative count: " + key)
    return val


def audit(scan, epg, epg_integrity, youtube, gitlab, codeberg):
    if not all(isinstance(doc, dict) for doc in (
            scan, epg, epg_integrity, youtube, gitlab, codeberg)):
        raise InvalidEvidence("All six evidence inputs must be JSON objects")
    if scan.get("mock_data_used") is not False:
        raise InvalidEvidence("Mock or missing real-scan marker")
    if scan.get("archive_restore_test_passed") is not True:
        raise InvalidEvidence("Encrypted inventory archive not restored successfully")
    checked = number(scan, "http_checked")
    if checked < 1 or checked != number(scan, "unique_new_candidates"):
        raise InvalidEvidence("Inconsistent real candidate count")
    verified = number(scan, "av_verified")
    current_av = number(scan, "av_verified_this_run")
    previous_av = number(scan, "resumed_decoded_av_evidence")
    rechecked = number(scan, "http_checked_this_run")
    resumed = number(scan, "resumed_checkpoint_observations")
    unverified = number(scan, "unverified_or_failed_candidates")
    retried = number(scan, "retried_failed_checkpoint_urls")
    recovered = number(scan, "recovered_av_from_failed_checkpoint")
    if (verified != current_av + previous_av or checked != rechecked + resumed
            or verified + unverified != checked or retried > rechecked
            or previous_av > resumed or current_av > rechecked
            or recovered > retried or recovered > current_av):
        raise InvalidEvidence("AV recovery and checkpoint counts do not balance")

    source_count = number(scan, "source_count")
    fetched = number(scan, "fetched_sources")
    core_source_complete = (
        scan.get("status") == "READY_FOR_DEVICE_TEST"
        and scan.get("configured_sources_complete") is True
        and scan.get("full_discovery_acceptance") is True
        and scan.get("discovery_partial") is False
        and source_count == fetched
        and source_count > 0
        and scan.get("failed_sources") == []
        and scan.get("source_drops") == [])
    valid_epg_sources = epg_integrity.get("status_counts", {}).get("XMLTV_VALID", 0)
    if type(valid_epg_sources) is not int or valid_epg_sources < 0:
        raise InvalidEvidence("Invalid XMLTV source audit")
    exact_epg = number(epg, "verified_exact_id_channels")
    name_hints = number(epg, "name_hint_channels_not_exact_evidence")
    programmes = number(epg, "programmes")
    if epg.get("candidate_only") is not True or epg.get("status") != "EPG_CANDIDATE_FOR_REVIEW":
        raise InvalidEvidence("Only isolated, non-publishing XMLTV is accepted as an EPG review input")
    if exact_epg > number(epg, "channels"):
        raise InvalidEvidence("Exact EPG identity count exceeds available guide channels")
    yt_checked = number(youtube, "videos_checked")
    yt_verified = number(youtube, "live_verified")
    if yt_verified > yt_checked:
        raise InvalidEvidence("YouTube live verification exceeds checked count")
    yt_reasons = youtube.get("verification_failure_categories", {})
    if not isinstance(yt_reasons, dict) or any(
            type(v) is not int or v < 0 for v in yt_reasons.values()):
        raise InvalidEvidence("Invalid YouTube metadata failure categories")
    adapters = {
        "gitlab": {
            "status": gitlab.get("status", "unknown"),
            "rate_limited": gitlab.get("rate_limited") is True,
            "queries_checked": number(gitlab, "queries_checked"),
            "queries_skipped": number(gitlab, "queries_skipped"),
        },
        "codeberg": {
            "status": codeberg.get("status", "unknown"),
            "rate_limited": codeberg.get("rate_limited") is True,
            "queries_checked": number(codeberg, "queries_checked"),
            "queries_skipped": number(codeberg, "queries_skipped"),
        },
    }
    adapters_complete = all(
        item["status"] == "ok" and not item["rate_limited"]
        and item["queries_skipped"] == 0
        for item in adapters.values())
    youtube_complete = (
        youtube.get("metadata_verification_complete") is True
        and yt_verified > 0)
    recovery_open = unverified > 0
    # No evidence input independently authenticates broadcaster ownership.
    # A scan/playlist/provider correlation can NEVER close historical identity #15.
    blockers = {
        15: ["INDEPENDENT_BROADCASTER_OWNERSHIP_NOT_VERIFIED"],
        17: (["RECOVERY_QUEUE_STILL_OPEN"] if recovery_open else
             ["FULL_INDEPENDENT_RECOVERY_ACCEPTANCE_NOT_DOCUMENTED"]),
        18: ["CURRENT_AV_AND_PUBLISHER_PROVENANCE_NOT_FULLY_ACCEPTED"],
        19: (["NO_EXACT_XMLTV_CHANNEL_ID_EVIDENCE"] if exact_epg == 0 else
             ["EPG_GAPS_AND_PUBLISHER_LINKAGE_NOT_FULLY_CLOSED"]),
        20: (["RECOVERY_RECHECKS_REMAIN"] if recovery_open else
             ["INDEPENDENT_PLAYBACK_ACCEPTANCE_NOT_DOCUMENTED"]),
        21: ([] if core_source_complete else ["CORE_M3U_SOURCE_COVERAGE_INCOMPLETE"])
            + ([] if adapters_complete else ["GITLAB_CODEBERG_ADAPTERS_INCOMPLETE"])
            + ([] if youtube_complete else ["YOUTUBE_LIVE_METADATA_INCOMPLETE"])
            + (["NO_RESOLVED_OFFICIAL_OR_YOUTUBE_HLS"] if
               number(scan, "resolved_direct_candidate_count") == 0 else []),
    }
    if not blockers[21]:
        blockers[21] = ["WORLDWIDE_PROVIDER_PUBLISHER_ACCEPTANCE_NOT_INDEPENDENTLY_VERIFIED"]
    return {
        "schema": 1,
        "stage": "A",
        "status": "OPEN_REQUIRES_REAL_WORLD_ACCEPTANCE",
        "task_status_changes": False,
        "protected_playlists_modified": False,
        "final_acceptance": False,
        "scan_workflow_success_is_not_stage_A_acceptance": True,
        "scan": {
            "core_configured_sources_complete": core_source_complete,
            "sources_fetched": fetched,
            "sources_required": source_count,
            "candidates_checked": checked,
            "av_decoded_total": verified,
            "av_decoded_previous_checkpoint": previous_av,
            "av_decoded_this_run": current_av,
            "recovery_url_probes_this_run": retried,
            "av_recovered_from_previous_failures": recovered,
            "candidates_without_decoded_av": unverified,
        },
        "epg": {
            "valid_xmltv_source_files": valid_epg_sources,
            "exact_id_channels": exact_epg,
            "name_only_review_channels": name_hints,
            "candidate_programmes_not_published": programmes,
        },
        "discovery": {
            "youtube_metadata_checked": yt_checked,
            "youtube_live_verified": yt_verified,
            "youtube_failure_categories": yt_reasons,
            "provider_adapters": adapters,
            "full_worldwide_coverage_accepted": False,
        },
        "tasks": {
            str(task): {"status": "in_progress", "blockers": blockers[task]}
            for task in TASK_IDS
        },
    }


def main():
    parser = argparse.ArgumentParser()
    for name in ("scan", "epg", "epg-integrity", "youtube", "gitlab", "codeberg", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        inputs = []
        for path in (args.scan, args.epg, args.epg_integrity, args.youtube,
                     args.gitlab, args.codeberg):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_000_000:
                raise InvalidEvidence("Missing, symlinked, or oversized public evidence report")
            inputs.append(json.loads(path.read_text(encoding="utf-8")))
        report = audit(*inputs)
        if (args.output.is_symlink() or args.output.suffix != ".json"
                or "reports" not in args.output.parts):
            raise InvalidEvidence("Unsafe audit output")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps({"stage": "A", "status": report["status"],
                          "current_av": report["scan"]["av_decoded_this_run"],
                          "open_tasks": list(report["tasks"])}, sort_keys=True))
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, "Stage A evidence audit failed closed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
