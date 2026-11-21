"""Offline, authorized Turkish stream vault. Never logs or exports stream URLs."""
from __future__ import annotations
import hashlib
import json
import os
import stat
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit
from cryptography.fernet import Fernet, InvalidToken

VERSION = 1
MAX_VAULT_BYTES = 512 * 1024 * 1024

def _private_bytes(path):
    """Open a private regular vault by descriptor; reject symlink swaps and oversize."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("Vault must be a private regular file")
        if info.st_size > MAX_VAULT_BYTES:
            raise ValueError("Vault exceeds maximum size")
        with os.fdopen(fd, "rb", closefd=False) as source:
            data = source.read(MAX_VAULT_BYTES + 1)
        if len(data) > MAX_VAULT_BYTES:
            raise ValueError("Vault exceeds maximum size")
        return data
    finally:
        os.close(fd)

def _now():
    return datetime.now(timezone.utc).isoformat()

def _valid_url(url):
    if not isinstance(url, str) or any(ord(ch) < 33 or ord(ch) == 127 for ch in url):
        return False
    try:
        parts = urlsplit(url)
        return (parts.scheme in ("http", "https") and bool(parts.hostname)
                and parts.username is None and parts.password is None
                and parts.port != 0)
    except ValueError:
        return False

def _digest(data):
    return hashlib.sha256(data).hexdigest()

class Vault:
    def __init__(self, path, key):
        self.path = Path(path)
        self.cipher = Fernet(key)

    def _decode(self, raw):
        try:
            doc = json.loads(self.cipher.decrypt(raw))
        except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Vault integrity or decryption failure") from exc
        if doc.get("version") != VERSION or not isinstance(doc.get("entries"), dict):
            raise ValueError("Unsupported vault format")
        for channel_id, entry in doc["entries"].items():
            if not isinstance(channel_id, str) or not isinstance(entry, dict):
                raise ValueError("Invalid vault entry")
            url = entry.get("url")
            if (entry.get("authorized") is not True or entry.get("turkish") is not True
                or not _valid_url(url) or entry.get("fingerprint") != _digest(url.encode())
                or not isinstance(entry.get("history"), list)
                or not isinstance(entry.get("provenance"), str)):
                raise ValueError("Vault policy or fingerprint validation failure")
        return doc

    def _read(self, path):
        raw = _private_bytes(path)
        if raw is None:
            return {"version": VERSION, "entries": {}}
        return self._decode(raw)

    def read(self):
        return self._read(self.path)

    def _write(self, doc, *, exclusive=False):
        if self.path.is_symlink():
            raise ValueError("Symlink vault path forbidden")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.cipher.encrypt(json.dumps(doc, ensure_ascii=False, sort_keys=True).encode())
        fd, temp = tempfile.mkstemp(dir=self.path.parent, prefix=".vault-")
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if exclusive:
                os.link(temp, self.path)  # atomic no-clobber restore
                os.unlink(temp)
            else:
                os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def add(self, channel_id, url, provenance, authorized, turkish, decision="approved"):
        if not (authorized is True and turkish is True):
            raise ValueError("Only authorized Turkish channels are accepted")
        if not all(isinstance(x, str) and x.strip() for x in (channel_id, url, provenance)):
            raise ValueError("Missing required metadata")
        if not _valid_url(url):
            raise ValueError("Only HTTP(S) URLs are accepted")
        doc = self.read()
        entries = doc["entries"]
        fingerprint = _digest(url.encode())
        if any(e["fingerprint"] == fingerprint and cid != channel_id for cid, e in entries.items()):
            raise ValueError("Duplicate stream URL")
        old = entries.get(channel_id)
        now = _now()
        entries[channel_id] = {
            "url": url, "fingerprint": fingerprint, "provenance": provenance,
            "first_seen": old["first_seen"] if old else now, "last_seen": now,
            "history": (old["history"] if old else []) + [{"at": now, "decision": decision}],
            "authorized": True, "turkish": True
        }
        self._write(doc)

    def backup(self, destination):
        destination = Path(destination)
        if destination.exists() or destination.is_symlink():
            raise ValueError("Backup destination already exists")
        data = _private_bytes(self.path)
        if data is None:
            raise ValueError("Missing vault source")
        self._decode(data)  # Validate the exact bytes copied, not a second open.
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return _digest(data)

    def restore(self, source, expected_sha256):
        source = Path(source)
        raw = _private_bytes(source)
        if raw is None:
            raise ValueError("Missing backup source")
        if _digest(raw) != expected_sha256:
            raise ValueError("Backup checksum mismatch")
        doc = self._decode(raw)  # Same validated bytes are restored.
        self._write(doc, exclusive=True)

    def public_report(self):
        doc = self.read()
        return {"version": VERSION, "count": len(doc["entries"]),
                "channel_ids": sorted(doc["entries"])}
