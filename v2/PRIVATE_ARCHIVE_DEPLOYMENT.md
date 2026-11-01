# V2 encrypted archive deployment

The private archive module is tested in GitHub Actions. **This does not
establish durable backup storage.** No private inventory or encryption key
should be committed to this public repository.

## Required deployment configuration

- A separate private storage destination with retention and versioning.
- A 32-byte random encryption key stored as a protected secret named
  `V2_ARCHIVE_KEY_B64` (base64 encoded), never in repository files.
- A private execution environment with `cryptography` installed.
- A scheduled encrypted backup and an independent restore job that fetches
  the archive from private storage.
- Verified checksums and evidence produced from the independent restore.

## Commands in the private environment

```sh
python v2/private_archive.py backup --source /private/inventory.jsonl --destination /private/backups/inventory.v2enc
python v2/private_archive.py verify --source /private/backups/inventory.v2enc
python v2/private_archive.py restore --source /private/backups/inventory.v2enc --destination /private/restore/inventory.jsonl
```

The backup command can emit evidence using `--evidence`, but its
`durable` field deliberately remains false. Do not manually change it
to true without independently confirming retention, versioning, and a
restore from remote private storage.

## Safety rules

Never publish stream inventories, plaintext backups, archive keys or
restore files as public GitHub Actions artifacts. Never overwrite the
protected main IBO playlist or YEDEKLER while testing backup operations.
If private storage or secrets are unavailable, stop rather than claiming
that a durable encrypted backup exists.
