#!/usr/bin/env python3
"""#34: read-only source discovery; offline by default. No playlist writes."""
import argparse
import hashlib
import ipaddress
import json
import os
import re
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from discovery_provider_requests import (
    MAX_ATTEMPTS, REQUEST_ERRORS, RETRYABLE_CONNECTION, http_error_details, provider_rate_limited,
    retry_delay, retry_not_before, _indicates_throttling,
)

QUERIES = ("turkiye.m3u", "tr.m3u8", "turkish-iptv", "canli-tv", "yerel-tv", "iptv-turkiye")
SOURCES = ("github", "gitlab", "codeberg", "official", "youtube", "m3u")
REPOSITORY_SOURCES = ("github", "gitlab", "codeberg")
MAX_BYTES = 2_000_000

class ProviderThrottledEnvelope(ValueError):
    """Provider rate-limit JSON envelope returned with HTTP 200, not a successful result."""
    pass


def identity(source, url):
    if not isinstance(url, str) or "\\" in url or any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("Invalid URL characters")
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("https", "http") or not p.hostname:
        raise ValueError("Invalid public URL")
    if p.username or p.password:
        raise ValueError("Credential-bearing URL")
    try:
        port = p.port
    except ValueError as exc:
        raise ValueError("Invalid URL port") from exc
    host = p.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Private hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Non-public IP address")
    if source not in SOURCES:
        raise ValueError("Unknown adapter")
    expected_hosts = {"github": "github.com", "gitlab": "gitlab.com", "codeberg": "codeberg.org", "youtube": "www.youtube.com"}
    if source in expected_hosts and (p.scheme != "https" or host != expected_hosts[source]
                                     or port not in (None, 443) or p.fragment):
        raise ValueError("Unexpected source host, port, fragment or insecure scheme")
    authority = ("[" + host + "]" if ":" in host else host) + (":" + str(port) if port is not None else "")
    source_id = source + ":" + authority + p.path
    if source in ("official", "m3u") and p.query:
        source_id += "?sha256=" + hashlib.sha256(p.query.encode("utf-8")).hexdigest()
    return {"source": source, "source_id": source_id, "url": url, "verified_av": False}

def search_url(source, query):
    q = urllib.parse.quote(query, safe="")
    if source == "github":
        return "https://api.github.com/search/repositories?q=" + q + "&per_page=20"
    if source == "gitlab":
        return "https://gitlab.com/api/v4/projects?search=" + q + "&per_page=20"
    if source == "codeberg":
        return "https://codeberg.org/api/v1/repos/search?q=" + q + "&limit=20"
    raise ValueError("Adapter uses curated identifiers, not repository search")

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Block redirects before any follow-up request can be sent."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect refused")

def fetch_json(url):
    headers = {"User-Agent": "MADSC55-V2-Discovery/1.0", "Accept": "application/json"}
    if urllib.parse.urlsplit(url).hostname == "api.github.com":
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener(_NoRedirect).open(req, timeout=8) as res:
        if urllib.parse.urlsplit(res.url).hostname != urllib.parse.urlsplit(url).hostname:
            raise ValueError("Cross-host redirect refused")
        data = res.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Response too large")
    return json.loads(data)

def fetch_with_retry(url, fetch=None, sleep=None):
    """Bounded transient retry for the actual candidate collection CLI."""
    fetch = fetch or fetch_json
    sleep = sleep or time.sleep
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch(url)
        except RETRYABLE_CONNECTION as exc:
            delay = retry_delay(exc, attempt)
            if delay is None or attempt == MAX_ATTEMPTS:
                raise
            if isinstance(exc, urllib.error.HTTPError):
                exc.close()
            sleep(delay)

def repository_items(source, payload):
    if source == "github":
        if (not isinstance(payload, dict) or "message" in payload
                or not isinstance(payload.get("items"), list)):
            raise ValueError("Invalid GitHub repository API response")
        return payload["items"]
    if source == "gitlab":
        if not isinstance(payload, list):
            raise ValueError("Invalid GitLab repository API response")
        return payload
    if source == "codeberg":
        if (not isinstance(payload, dict) or payload.get("ok", True) is not True
                or "error" in payload or "message" in payload
                or not isinstance(payload.get("data"), list)):
            raise ValueError("Invalid Codeberg repository API response")
        return payload["data"]
    raise ValueError("Not a repository adapter")


def repository_candidates(source, payload):
    items = repository_items(source, payload)
    url_key = "web_url" if source == "gitlab" else "html_url"
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get(url_key, "")
        try:
            results.append(identity(source, url))
        except (ValueError, TypeError, AttributeError):
            continue
    return results


def incomplete_repository_response(source, payload):
    return source == "github" and payload.get("incomplete_results", False) is not False


def curated_candidates(source, records):
    """Official broadcaster URLs, YouTube watch IDs, and public M3U URLs.
    These are candidate identities only; never treat them as AV proof.
    """
    if source not in ("official", "youtube", "m3u"):
        raise ValueError("Not a curated adapter")
    out = []
    for item in records:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if source == "youtube":
            video_id = item.get("video_id", "")
            if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                continue
            url = "https://www.youtube.com/watch?v=" + video_id
        try:
            candidate = identity(source, url)
            if source == "youtube":
                candidate["source_id"] = "youtube:" + video_id
            out.append(candidate)
        except (ValueError, TypeError, AttributeError):
            continue
    return out

def load_resume(path, plan):
    """Carry forward public candidate identities and explicitly accounted queries."""
    with path.open("rb") as incoming:
        raw = incoming.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Resume report exceeds size limit")
    report = json.loads(raw)
    if (not isinstance(report, dict) or report.get("mode") != "network"
            or report.get("av_verified") != 0 or not isinstance(report.get("candidates"), list)
            or not isinstance(report.get("errors"), list)):
        raise ValueError("Resume requires a previous network candidate report")
    if "query_plan" in report and report["query_plan"] != plan:
        raise ValueError("Resume query plan differs from current discovery plan")
    candidates, failures, cooldowns = [], set(), {}
    seen_candidate_ids = set()
    for item in report["candidates"]:
        if (not isinstance(item, dict) or item.get("source") not in REPOSITORY_SOURCES
                or item.get("verified_av") is not False):
            raise ValueError("Invalid candidate in resume report")
        record = identity(item["source"], item.get("url"))
        if record["source_id"] != item.get("source_id"):
            raise ValueError("Candidate identity changed in resume report")
        if record["source_id"] in seen_candidate_ids:
            raise ValueError("Duplicate candidate identity in resume report")
        seen_candidate_ids.add(record["source_id"])
        candidates.append(record)
    for error in report["errors"]:
        if (not isinstance(error, dict) or error.get("source") not in REPOSITORY_SOURCES
                or not isinstance(error.get("query"), str) or not isinstance(error.get("error"), str)):
            raise ValueError("Invalid failure in resume report")
        source = error["source"]
        if error["query"] not in plan[source]:
            raise ValueError("Failure query outside discovery plan")
        failures.add((source, error["query"]))
        deadline = error.get("retry_not_before", 0)
        if type(deadline) is not int or deadline < 0:
            raise ValueError("Invalid cooldown in resume report")
        cooldowns[source] = max(cooldowns.get(source, 0), deadline)
    completed = set()
    if report.get("query_plan") == plan and "completed_queries" in report:
        checked = report["completed_queries"]
        if not isinstance(checked, dict) or checked.keys() != plan.keys():
            raise ValueError("Invalid completed-query record")
        for source, entries in checked.items():
            if (not isinstance(entries, list)
                    or any(not isinstance(query, str) or query not in plan[source] for query in entries)
                    or len(entries) != len(set(entries))):
                raise ValueError("Invalid completed-query record")
            completed.update((source, query) for query in entries)
        if completed & failures:
            raise ValueError("Conflicting completed and failed queries")
    return candidates, completed, cooldowns, hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", action="store_true", help="Explicit opt-in repository metadata queries")
    parser.add_argument("--output", type=Path, default=Path("v2/reports/discovery-34-candidates.json"))
    parser.add_argument("--resume", type=Path, help="Continue from a previous network candidate report")
    args = parser.parse_args()
    if args.resume and not args.network:
        parser.error("--resume requires --network")
    if args.output.exists() or args.output.is_symlink():
        parser.error("--output already exists")
    candidates, errors = [], []
    metadata = {}
    if args.network:
        # Fail closed before the first network request; offline mode stays available.
        from prescan_readiness_gate import require_readiness
        require_readiness()
        plan = {source: list(QUERIES) for source in REPOSITORY_SOURCES}
        completed, cooldowns = set(), {}
        if args.resume:
            try:
                candidates, completed, cooldowns, digest = load_resume(args.resume, plan)
            except (OSError, ValueError, TypeError) as exc:
                parser.exit(1, f"Invalid discovery resume report ({type(exc).__name__})\n")
            metadata["resumed_report_sha256"] = digest
        queries_reused = len(completed)
        queries_attempted = 0
        for source, terms in plan.items():
            pending = [query for query in terms if (source, query) not in completed]
            deadline = cooldowns.get(source, 0)
            if deadline > time.time():
                errors.extend({"source": source, "query": query, "error": "provider_cooldown_pending",
                               "retry_not_before": deadline} for query in pending)
                continue
            for index, query in enumerate(pending):
                queries_attempted += 1
                try:
                    payload = fetch_with_retry(search_url(source, query))
                    # Some provider APIs return a throttle envelope with HTTP 200.
                    # Keep the body private and stop this provider's remaining
                    # requests to avoid repeatedly hitting a throttled endpoint.
                    if (isinstance(payload, dict) and
                            any(_indicates_throttling(payload.get(key, ""))
                                for key in ("message", "error"))):
                        raise ProviderThrottledEnvelope()
                    candidates.extend(repository_candidates(source, payload))
                    if incomplete_repository_response(source, payload):
                        errors.append({"source": source, "query": query, "error": "incomplete_repository_response"})
                    else:
                        completed.add((source, query))
                except REQUEST_ERRORS as exc:
                    envelope_throttled = isinstance(exc, ProviderThrottledEnvelope)
                    error = {"source": source, "query": query,
                             "error": "provider_throttled_response" if envelope_throttled
                             else type(exc).__name__}
                    limited = envelope_throttled
                    if limited:
                        error["retry_not_before"] = retry_not_before({})
                    if isinstance(exc, urllib.error.HTTPError):
                        details = http_error_details(exc)
                        error["http_status"] = details["http_status"]
                        limited = provider_rate_limited(details)
                        if limited:
                            error["retry_not_before"] = retry_not_before(details)
                    errors.append(error)
                    # Provider-wide rate limits must not trigger five more API calls.
                    # Preserve skipped terms as incomplete rather than empty results.
                    if limited:
                        errors.extend({"source": source, "query": term,
                                       "error": "provider_rate_limit_skipped"}
                                      for term in pending[index + 1:])
                        break
        metadata.update(query_plan=plan, queries_reused=queries_reused,
                        queries_attempted_this_run=queries_attempted,
                        completed_queries={
                            source: [query for query in queries if (source, query) in completed]
                            for source, queries in plan.items()})
    unique = {item["source_id"]: item for item in candidates}
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    # Preserve earlier evidence even when repeated jobs target the same report.
    with output.open("x", encoding="utf-8") as report:
        report.write(json.dumps({"mode": "network" if args.network else "offline",
                                 "candidates": list(unique.values()), "errors": errors,
                                 "av_verified": 0, **metadata}, indent=2) + "\n")
    print("Candidate identities:", len(unique), "Errors:", len(errors))
    # Persist partial evidence, but never report a failed live scan as success.
    if errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
