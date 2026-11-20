"""Offline, authorized Turkish stream vault. Never logs or exports stream URLs."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from cryptography.fernet import Fernet, InvalidToken

VERSION = 1

def _now():
    return datetime.now(timezone.utc).isoformat()

def _digest(data):
    return hashlib.sha256(data).hexdigest()

class Vault:
    def __init__(self, path, key):
        self.path = Path(path)
        self.cipher = Fernet(key)

    def _read(self, path):
        if not path.exists():
            return {"version": VERSION, "entries": {}}
        raw = path.read_bytes()
        try:
            doc = json.loads(self.cipher.decrypt(raw))
        except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Vault integrity or decryption failure") from exc
        if doc.get("version") != VERSION or not isinstance(doc.get("entries"), dict):
            raise ValueError("Unsupported vault format")
        return doc

    def read(self):
        return self._read(self.path)

    def _write(self, doc):
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
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def add(self, channel_id, url, provenance, authorized, turkish, decision="approved"):
        if not (authorized is True and turkish is True):
            raise ValueError("Only authorized Turkish channels are accepted")
        if not all(isinstance(x, str) and x.strip() for x in (channel_id, url, provenance)):
            raise ValueError("Missing required metadata")
        if not url.startswith(("https://", "http://")):
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
        data = self.path.read_bytes()
        self._read(self.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return _digest(data)

    def restore(self, source, expected_sha256):
        raw = Path(source).read_bytes()
        if _digest(raw) != expected_sha256:
            raise ValueError("Backup checksum mismatch")
        doc = self._read(Path(source))
        if self.path.exists():
            raise ValueError("Refusing to overwrite existing vault")
        self._write(doc)

    def public_report(self):
        doc = self.read()
        return {"version": VERSION, "count": len(doc["entries"]),
                "channel_ids": sorted(doc["entries"])}
