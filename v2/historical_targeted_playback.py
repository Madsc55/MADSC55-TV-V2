#!/usr/bin/env python3
"""Bounded, read-only video/audio diagnosis of exact historical SHA identities.

Only hashes missing from the verified current M3U content audit may be probed.
Plaintext historical URLs exist only in private process memory. This tool never
publishes URLs, attempts playlist updates, or claims IBO device compatibility.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import subprocess
from urllib.parse import urlsplit

from historical_url_recovery import validate_url
from stage3_git_history_forensics import candidate_blobs, git, iter_url_entries

ORIGINAL_INDEX_SHA256 = "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27"


def load_missing_report(path, historical_index):
    baseline = Path(historical_index).read_bytes()
    if hashlib.sha256(baseline).hexdigest() != ORIGINAL_INDEX_SHA256:
        raise ValueError("Immutable original 4955 identities unavailable")
    original = {json.loads(line)["url_sha256"] for line in baseline.splitlines() if line.strip()}
    if len(original) != 4955:
        raise ValueError("Incomplete original historical baseline")
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    a = report.get("source_content_audit", {})
    candidates = a.get("historical_identifiers_absent_sha256_sample", [])
    reported = a.get("historical_identifiers_absent_from_current_sources")
    if (not isinstance(candidates, list) or type(reported) is not int
            or reported > 30 or reported != len(candidates)
            or len(candidates) != len(set(candidates))
            or not set(candidates) <= original):
        raise ValueError("Unverified or truncated absent-historical-URL report")
    return set(candidates)


def find_exact_urls(missing):
    """Only repository-local historic blobs; no arbitrary new-source searches."""
    found = {}
    blobs, skipped = candidate_blobs()
    for sha, path in blobs:
        if len(found) == len(missing):
            break
        raw = git(["cat-file", "blob", sha])
        for item in iter_url_entries(path, raw):
            url = item["url"]
            if not validate_url(url):
                continue
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            if digest in missing and digest not in found:
                found[digest] = url
    return found, {"git_blobs_inspected_or_available": len(blobs),
                   "oversized_git_blobs_skipped": skipped}


def public_dns(url, lookup=socket.getaddrinfo):
    """Restrict source URL DNS resolution to globally routable addresses."""
    if not validate_url(url):
        return False
    p = urlsplit(url)
    try:
        infos = lookup(p.hostname, p.port or (443 if p.scheme == "https" else 80),
                       type=socket.SOCK_STREAM)
        return bool(infos) and all(ipaddress.ip_address(row[4][0]).is_global
                                   for row in infos)
    except (OSError, ValueError, IndexError, TypeError):
        return False


def classify_probe_failure(stderr):
    """Return a fixed safe category; never return URL-bearing ffmpeg stderr."""
    s = str(stderr or "").casefold()
    if "unrecognized option" in s or "option not found" in s:
        return "FFPROBE_OPTION_UNSUPPORTED"
    if "401" in s or "unauthorized" in s:
        return "AUTH_REQUIRED"
    if "403" in s or "forbidden" in s:
        return "HTTP_FORBIDDEN"
    if "404" in s or "not found" in s:
        return "HTTP_NOT_FOUND"
    if "redirect" in s or "302" in s or "301" in s:
        return "REDIRECT_REQUIRED_OR_BLOCKED"
    if "protocol" in s and "whitelist" in s:
        return "PROTOCOL_DISALLOWED_BY_SAFETY"
    if "timed out" in s or "timeout" in s:
        return "NETWORK_TIMEOUT"
    if "name resolution" in s or "resolve host" in s:
        return "DNS_RESOLUTION_ERROR"
    if "server returned" in s or "http error" in s:
        return "HTTP_RESPONSE_ERROR"
    if "invalid data" in s or "could not find codec" in s:
        return "MEDIA_FORMAT_UNSUPPORTED"
    return "UNKNOWN_NETWORK_OR_MEDIA_ERROR"


def probe_one(item, runner=subprocess.run, resolver=public_dns):
    digest, url = item
    if not resolver(url):
        return {"url_sha256": digest, "status": "UNSAFE_OR_UNRESOLVABLE_HOST",
                "video_stream": False, "audio_stream": False}
    # Strict no-redirect and protocol constraints; no subprocess output or URL
    # is forwarded to the Actions logs. A failure is not proof of a dead stream.
    command = [
        "ffprobe", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-rw_timeout", "5000000",
        "-protocol_whitelist", "http,https,tcp,tls,crypto",
        "-analyzeduration", "2000000", "-probesize", "65536",
        "-show_entries", "stream=codec_type", "-of", "json", url,
    ]
    try:
        proc = runner(command, capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            return {"url_sha256": digest, "status": "PROBE_FAILED_NOT_PROVEN_DEAD",
                    "diagnostic_category": classify_probe_failure(proc.stderr),
                    "video_stream": False, "audio_stream": False}
        streams = json.loads(proc.stdout).get("streams", [])
        video = any(s.get("codec_type") == "video" for s in streams)
        audio = any(s.get("codec_type") == "audio" for s in streams)
        return {"url_sha256": digest,
                "status": "VIDEO_STREAM_OBSERVED" if video else
                          "AUDIO_ONLY_OBSERVED" if audio else
                          "NO_AUDIO_VIDEO_STREAM_OBSERVED",
                "video_stream": video, "audio_stream": audio}
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return {"url_sha256": digest, "status": "PROBE_FAILED_NOT_PROVEN_DEAD",
                "video_stream": False, "audio_stream": False}


def audit(missing, recovered, *, runner=subprocess.run, resolver=public_dns, workers=4):
    if not 1 <= workers <= 8:
        raise ValueError("Invalid parallel probe size")
    valid = [(digest, recovered[digest]) for digest in sorted(missing)
             if digest in recovered]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(
            lambda item: probe_one(item, runner=runner, resolver=resolver), valid))
    not_found = sorted(missing - set(recovered))
    return {"schema": 1, "kind": "BOUNDED_HISTORICAL_ONLY_FFPROBE_NOT_IBO",
            "requested_historical_url_sha256": len(missing),
            "exact_git_history_urls_recovered": len(valid),
            "not_found_in_git_history_count": len(not_found),
            "not_found_sha256": not_found,
            "status_counts": dict(sorted(Counter(item["status"] for item in results).items())),
            "diagnostic_counts": dict(sorted(Counter(
                item.get("diagnostic_category", "NONE") for item in results).items())),
            "results": results, "no_plaintext_stream_urls": True,
            "main_playlist_modified": False, "ibo_device_verified": False,
            "not_current_source_feed_evidence": True}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--missing-report", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink():
        p.error("Refusing to overwrite report")
    missing = load_missing_report(args.missing_report, args.baseline)
    recovered, scan = find_exact_urls(missing)
    result = audit(missing, recovered)
    result["git_history"] = scan
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, sort_keys=True, indent=2)
        file.write("\n")
    print("Historical-only guarded playback audit:", result["requested_historical_url_sha256"],
          "requested,", result["exact_git_history_urls_recovered"], "recovered,",
          "FFprobe status counts:", result["status_counts"])


if __name__ == "__main__":
    main()
