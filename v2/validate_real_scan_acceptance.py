#!/usr/bin/env python3
"""Fail-closed real scan acceptance gate for GitHub Actions.

An Actions step may finish successfully while its evidence report is
PARTIAL_DISCOVERY_EVIDENCE_ONLY. That must not appear green to operators.
This gate accepts a *complete read-only scan*, not A/B/C/D final acceptance.
"""
import argparse
import json
from pathlib import Path


class ScanIncomplete(ValueError):
    pass


def validate_report(report):
    """Return compact, non-secret evidence totals; raise for incomplete scans."""
    if not isinstance(report, dict):
        raise ScanIncomplete("Invalid scan report")
    if report.get("mock_data_used") is not False:
        raise ScanIncomplete("Real scan cannot claim mock or missing evidence")
    if report.get("full_discovery_acceptance") is not True:
        raise ScanIncomplete("Discovery is incomplete; scanned evidence preserved, full acceptance blocked")
    if report.get("configured_sources_complete") is not True:
        raise ScanIncomplete("Configured sources are not complete")
    if report.get("discovery_partial") is not False:
        raise ScanIncomplete("Discovered feeds include unresolved failures")
    for field in ("failed_sources", "source_drops", "mandatory_failed_sources",
                  "optional_failed_discovered_sources", "mandatory_source_drops",
                  "optional_discovery_source_drops"):
        if report.get(field) != []:
            raise ScanIncomplete("Failed or dropped feeds remain in report: " + field)
    if report.get("archive_restore_test_passed") is not True:
        raise ScanIncomplete("Encrypted archive roundtrip was not verified")
    if report.get("status") != "READY_FOR_DEVICE_TEST":
        raise ScanIncomplete("Real scan is not ready for separate device acceptance")

    numbers = ("source_count", "fetched_sources", "unique_new_candidates",
               "http_checked", "http_checked_this_run", "resumed_checkpoint_observations",
               "av_verified", "resumed_decoded_av_evidence", "av_verified_this_run",
               "unverified_or_failed_candidates")
    for field in numbers:
        if type(report.get(field)) is not int or report[field] < 0:
            raise ScanIncomplete("Invalid or absent count: " + field)
    if report["source_count"] < 1 or report["source_count"] != report["fetched_sources"]:
        raise ScanIncomplete("Not all configured and discovered feeds were read")
    if report["http_checked"] != report["unique_new_candidates"]:
        raise ScanIncomplete("Not all discovered stream candidates were examined")
    if report["http_checked"] != (report["http_checked_this_run"] +
                                  report["resumed_checkpoint_observations"]):
        raise ScanIncomplete("Resumed and current-run check counts do not balance")
    if report["av_verified"] < 1 or report["av_verified"] > report["http_checked"]:
        raise ScanIncomplete("No valid decoded AV evidence in real scan")
    if report["av_verified"] != (report["av_verified_this_run"] +
                                 report["resumed_decoded_av_evidence"]):
        raise ScanIncomplete("Resumed and current AV evidence counts do not balance")
    if report["unverified_or_failed_candidates"] != (report["http_checked"] -
                                                       report["av_verified"]):
        raise ScanIncomplete("Failed candidate count does not balance")

    inventory = report.get("candidate_inventory")
    if (not isinstance(inventory, str)
            or not inventory.endswith("/ibo-candidate-inventory.jsonl.enc")):
        raise ScanIncomplete("Only the complete authenticated inventory is acceptable")
    if not isinstance(report.get("written_parts"), list) or not report["written_parts"]:
        raise ScanIncomplete("No complete candidate test M3U parts were written")
    if report.get("playback_verified_on_device") is not False:
        raise ScanIncomplete("Real scan cannot assert unverified physical-device playback")
    return {
        "source_count": report["source_count"],
        "checked": report["http_checked"],
        "decoded_av_total": report["av_verified"],
        "decoded_av_previous_checkpoint": report["resumed_decoded_av_evidence"],
        "decoded_av_this_run": report["av_verified_this_run"],
        "status": "COMPLETE_REAL_SCAN_NOT_FINAL_DEVICE_ACCEPTANCE",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.report.is_symlink():
            raise ScanIncomplete("Refusing symlinked report")
        payload = json.loads(args.report.read_text(encoding="utf-8"))
        print(json.dumps(validate_report(payload), ensure_ascii=False, sort_keys=True))
    except (ScanIncomplete, OSError, ValueError, TypeError) as exc:
        parser.exit(1, "Real scan NOT fully accepted: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
