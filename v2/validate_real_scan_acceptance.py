#!/usr/bin/env python3
"""Fail-closed real scan acceptance gate for GitHub Actions.

An Actions step may finish successfully while its evidence report is
PARTIAL_DISCOVERY_EVIDENCE_ONLY. That must not appear green to operators.
This gate accepts a *complete read-only scan*, not A/B/C/D final acceptance.
"""
import argparse
import json
from pathlib import Path

DISCOVERY_REPORTS = {
    "repositories": "discovery-34-candidates.json",
    "github_m3u": "github-source-discovery.json",
    "gitlab": "gitlab-m3u-source-discovery.json",
    "codeberg": "codeberg-m3u-source-discovery.json",
    "official": "official-tv-sites.json",
    "youtube": "youtube-live-candidates.json",
}


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
    parts = report.get("written_parts")
    if (not isinstance(parts, list) or not parts
            or any(not isinstance(part, str) or not part.endswith(".m3u8")
                   or not part.strip() or chr(0) in part for part in parts)
            or len(parts) != len(set(parts))):
        raise ScanIncomplete("Missing, malformed or duplicate candidate test M3U parts")
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


def require_complete_adapters(scan, reports):
    """Check live adapter evidence independently of the scanner's M3U coverage."""
    repositories = reports["repositories"]
    github_m3u = reports["github_m3u"]
    official = reports["official"]
    youtube = reports["youtube"]
    blocked = []
    if (repositories.get("mode") != "network" or repositories.get("errors") != []
            or not isinstance(repositories.get("candidates"), list)):
        blocked.append("repository search")
    if github_m3u.get("errors") != [] or not isinstance(github_m3u.get("sources"), list):
        blocked.append("GitHub playlist search")
    for name in ("gitlab", "codeberg"):
        provider = reports[name]
        total, checked, failed, skipped = (provider.get("queries_" + key)
                                           for key in ("total", "checked", "failed", "skipped"))
        if (provider.get("status") != "ok" or provider.get("rate_limited") is not False
                or provider.get("errors") != []
                or any(type(count) is not int for count in (total, checked, failed, skipped))
                or total <= 0 or checked != total or failed != 0 or skipped != 0):
            blocked.append(name)
    if (official.get("scope") != "WORLDWIDE" or not isinstance(official.get("channels"), list)
            or not official["channels"]):
        blocked.append("official broadcasters")
    checked, verified = youtube.get("videos_checked"), youtube.get("live_verified")
    if (youtube.get("metadata_verification_complete") is not True or youtube.get("errors") != []
            or type(checked) is not int or type(verified) is not int or not 0 < verified <= checked):
        blocked.append("YouTube live metadata")
    resolved = scan.get("resolved_direct_candidate_count")
    if type(resolved) is not int or resolved <= 0:
        blocked.append("official or YouTube direct streams")
    if blocked:
        raise ScanIncomplete("Worldwide adapter evidence incomplete: " + ", ".join(blocked))


def read_report(path):
    if path.is_symlink() or not path.is_file():
        raise ScanIncomplete("Missing or symlinked report: " + path.name)
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ScanIncomplete("Invalid JSON report: " + path.name)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--discovery-reports-dir", type=Path,
                        help="Require all worldwide adapter reports before accepting a package export")
    args = parser.parse_args()
    try:
        payload = read_report(args.report)
        totals = validate_report(payload)
        if args.discovery_reports_dir is not None:
            reports = {name: read_report(args.discovery_reports_dir / filename)
                       for name, filename in DISCOVERY_REPORTS.items()}
            require_complete_adapters(payload, reports)
            totals["worldwide_adapters_complete"] = True
        print(json.dumps(totals, ensure_ascii=False, sort_keys=True))
    except (ScanIncomplete, OSError, ValueError, TypeError) as exc:
        parser.exit(1, "Real scan NOT fully accepted: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
