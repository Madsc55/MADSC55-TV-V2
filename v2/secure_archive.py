#!/usr/bin/env python3
"""Authenticated encryption and verified restoration for private V2 inventories.

Requires cryptography. V2_ARCHIVE_PASSPHRASE must be supplied as a runner secret.
Encrypted output must be copied to durable private storage outside the repository.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b'MADSC55-V2-ARCHIVE\x01'
MAX_INPUT = 512 * 1024 * 1024

def _key(passphrase, salt):
    if not isinstance(passphrase, str) or len(passphrase) < 16:
        raise ValueError('Archive passphrase must contain at least 16 characters')
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())

def encrypt(data, passphrase):
    if type(data) is not bytes:
        raise ValueError("Archive input must be bytes")
    if len(data) > MAX_INPUT:
        raise ValueError('Archive input exceeds maximum size')
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    header = MAGIC + salt + nonce
    return header + AESGCM(_key(passphrase, salt)).encrypt(nonce, data, header)

def decrypt(blob, passphrase):
    if type(blob) is not bytes:
        raise ValueError("Encrypted archive must be bytes")
    minimum = len(MAGIC) + 16 + 12 + 16
    if len(blob) < minimum or len(blob) > MAX_INPUT + minimum or not blob.startswith(MAGIC):
        raise ValueError('Invalid encrypted archive format')
    offset = len(MAGIC)
    salt = blob[offset:offset + 16]
    nonce = blob[offset + 16:offset + 28]
    header = blob[:offset + 28]
    return AESGCM(_key(passphrase, salt)).decrypt(nonce, blob[len(header):], header)

def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.v2-archive-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def backup(source, destination, passphrase):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Source and destination must differ')
    if source.stat().st_size > MAX_INPUT:
        raise ValueError('Archive input exceeds maximum size')
    raw = source.read_bytes()
    blob = encrypt(raw, passphrase)
    atomic_write(destination, blob)
    restored = decrypt(Path(destination).read_bytes(), passphrase)
    if restored != raw:
        raise RuntimeError('Archive restore verification failed')
    return {'encrypted': True, 'restore_test_passed': True,
            'archive_sha256': hashlib.sha256(blob).hexdigest(),
            'restored_sha256': hashlib.sha256(restored).hexdigest(),
            'durability': 'local-fsynced; external backup must be verified separately',
            'bytes': len(raw)}

def restore(source, destination, passphrase):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Source and destination must differ')
    if source.stat().st_size > MAX_INPUT + len(MAGIC) + 16 + 12 + 16:
        raise ValueError('Encrypted archive exceeds maximum size')
    raw = decrypt(source.read_bytes(), passphrase)
    atomic_write(destination, raw)
    return hashlib.sha256(Path(destination).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['backup', 'restore'])
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        parser.error('Source and destination must differ')
    secret = os.environ.get('V2_ARCHIVE_PASSPHRASE', '')
    if args.operation == 'backup':
        print(json.dumps(backup(args.source, args.destination, secret), sort_keys=True))
    else:
        print(json.dumps({'restored_sha256': restore(args.source, args.destination, secret)}))

if __name__ == '__main__':
    main()
