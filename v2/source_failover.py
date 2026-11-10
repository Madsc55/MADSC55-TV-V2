#!/usr/bin/env python3
"""Offline-safe source-level failover; never promotes cached data to fresh coverage."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 16 * 1024 * 1024
DELAYS = (2, 4, 8)
RETRYABLE = {408, 429, 500, 502, 503, 504}
ALTERNATIVES = {
    "iptv-org-region-south-america": ("https://iptv-org.github.io/iptv/regions/latam.m3u", "https://iptv-org.github.io/iptv/regions/amer.m3u"),
    "iptv-org-region-middle-east": ("https://iptv-org.github.io/iptv/regions/mena.m3u", "https://iptv-org.github.io/iptv/regions/asia.m3u"),
    "iptv-org-region-eastern-europe": ("https://iptv-org.github.io/iptv/regions/eur.m3u", "https://iptv-org.github.io/iptv/regions/emea.m3u"),
    "iptv-org-region-southern-europe": ("https://iptv-org.github.io/iptv/regions/eur.m3u", "https://iptv-org.github.io/iptv/index.m3u"),
}


class FetchFailure(Exception):
    def __init__(self, category, retryable=False):
        super().__init__(category)
        self.category = category
        self.retryable = retryable


def safe_url(url):
    try:
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment or p.port not in (None, 443):
            return False
        if p.hostname.lower() in ("localhost", "localhost.localdomain") or p.hostname.endswith((".local", ".internal")):
            return False
        try:
            return ipaddress.ip_address(p.hostname).is_global
        except ValueError:
            return "." in p.hostname
    except (ValueError, TypeError):
        return False


def validate_m3u(data):
    if not data or len(data) > MAX_BYTES:
        raise FetchFailure("INVALID_SIZE")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FetchFailure("INVALID_UTF8") from exc
    if not text.lstrip("\r\n\t ").startswith("#EXTM3U") or "\x00" in text:
        raise FetchFailure("INVALID_M3U")
    return text


def fetch_once(url, timeout=12):
    if not safe_url(url):
        raise FetchFailure("UNSAFE_URL")
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            target = urljoin(req.full_url, newurl)
            if not safe_url(target):
                raise FetchFailure("UNSAFE_REDIRECT")
            return super().redirect_request(req, fp, code, msg, headers, target)
    opener = urllib.request.build_opener(SafeRedirect())
    req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-Failover/1.0"})
    try:
        with opener.open(req, timeout=timeout) as response:
            data = response.read(MAX_BYTES + 1)
            return validate_m3u(data)
    except urllib.error.HTTPError as exc:
        raise FetchFailure("HTTP_" + str(exc.code), exc.code in RETRYABLE) from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise FetchFailure(type(exc).__name__, True) from exc


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".failover-")
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class SourceCache:
    def __init__(self, directory, max_age_seconds=86400):
        self.directory = Path(directory)
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        self.max_age_seconds = max_age_seconds

    def _paths(self, source_id):
        key = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
        return self.directory / (key + ".m3u"), self.directory / (key + ".meta")

    def get(self, source_id):
        data_path, meta_path = self._paths(source_id)
        try:
            if data_path.is_symlink() or meta_path.is_symlink():
                return None
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            age = time.time() - float(meta["timestamp"])
            if meta["source_id"] != source_id or age < 0 or age > self.max_age_seconds:
                return None
            if data_path.stat().st_size > MAX_BYTES:
                return None
            raw = data_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                return None
            return validate_m3u(raw)
        except (OSError, KeyError, ValueError, TypeError, FetchFailure):
            return None

    def set(self, source_id, content):
        raw = content.encode("utf-8")
        validate_m3u(raw)
        data_path, meta_path = self._paths(source_id)
        atomic_write(data_path, raw)
        meta = {"source_id": source_id, "timestamp": time.time(), "sha256": hashlib.sha256(raw).hexdigest()}
        atomic_write(meta_path, (json.dumps(meta, sort_keys=True) + "\n").encode("utf-8"))


def recover_source(source, cache, fetcher=fetch_once, sleep=time.sleep, *, deadline=None, clock=time.monotonic):
    if deadline is not None and (type(deadline) not in (int, float) or not __import__('math').isfinite(deadline)):
        raise ValueError('deadline must be a finite numeric timestamp')
    source_id = source["id"]
    urls = tuple(dict.fromkeys((source["url"], *ALTERNATIVES.get(source_id, ()))))
    failures = []
    for index, url in enumerate(urls):
        if deadline is not None and clock() >= deadline:
            if not failures or failures[-1].get("category") != "RETRY_BUDGET_EXHAUSTED":
                failures.append({"category": "RETRY_BUDGET_EXHAUSTED"})
            break
        for attempt in range(len(DELAYS) + 1):
            if deadline is not None and clock() >= deadline:
                failures.append({'category': 'RETRY_BUDGET_EXHAUSTED'})
                break
            try:
                if fetcher is fetch_once and deadline is not None:
                    remaining = deadline - clock()
                    if remaining <= 0:
                        failures.append({"category": "RETRY_BUDGET_EXHAUSTED"})
                        break
                    text = fetcher(url, timeout=min(12, remaining))
                else:
                    text = fetcher(url)
                if index == 0:
                    try:
                        cache.set(source_id, text)
                    except (OSError, ValueError, FetchFailure) as exc:
                        failures.append({"category": "CACHE_WRITE_FAILED", "reason": type(exc).__name__})
                # A substitute feed must never masquerade as the original source.
                return text, {"id": source_id,
                              "status": "PRIMARY_OK" if index == 0 else "FALLBACK_OK",
                              "upstream_source_identity_preserved": index == 0,
                              "used_url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                              "attempts": len(failures) + 1,
                              "failures": failures, "fresh": True}
            except FetchFailure as exc:
                failures.append({"url_sha256": hashlib.sha256(url.encode()).hexdigest(), "category": exc.category, "attempt": attempt + 1})
                if not exc.retryable or attempt == len(DELAYS):
                    break
                delay = DELAYS[attempt]
                if deadline is not None:
                    remaining = deadline - clock()
                    if remaining <= 0 or delay > remaining:
                        failures.append({'category': 'RETRY_BUDGET_EXHAUSTED'})
                        break
                sleep(delay)
            except Exception as exc:
                failures.append({"url_sha256": hashlib.sha256(url.encode()).hexdigest(), "category": type(exc).__name__, "attempt": attempt + 1})
                break
    cached = cache.get(source_id)
    return cached, {"id": source_id, "status": "CACHE_RECOVERED" if cached is not None else "UNAVAILABLE", "attempts": len(failures), "failures": failures, "fresh": False}


def execute_pipeline(sources, cache, fetcher=fetch_once, sleep=time.sleep):
    results = []
    for source in sources:
        try:
            content, audit = recover_source(source, cache, fetcher, sleep)
        except Exception as exc:
            content, audit = None, {"id": source["id"], "status": "UNEXPECTED_ERROR", "fresh": False, "failures": [{"category": type(exc).__name__}]}
        results.append((source, content, audit))
    return results
