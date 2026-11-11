# Task #13 — Google Drive independent restore acceptance

Owner decision (2026-11-11): Google Drive replaces AWS S3 as the required **independent storage provider** for task #13. This does not waive authenticated decryption or real restore requirements.

Acceptance requires all of:
1. Independent retrieval of the original production encrypted archive from the designated Drive folder; record Drive file ID, exact byte count and pinned SHA-256.
2. Authenticated AES-256-GCM decryption with the **original matching private key metadata**, and verification of all 4,955 historical identities and 107 orphan candidates against the original hashes. Run the strict verification path in `v2/verify_drive_sealed_evidence.py` and `v2/production_full_stage5_archive.py`.
3. A successful, reproducible GitHub Actions restore job, using secure secret injection. Do not expose secrets or decrypted URL content in logs, artifacts, commits or chat.
4. Only after real proof: update canonical `state.json`, derived `v2/tasks/state.json`, and `DEVAM_NOTU.md` with run links; #14 can then be assessed.

A checksum-only Drive readback, a mock restore, an absent key, a skipped job, or a newly generated unrelated key **must fail production acceptance**. Historical S3 attempts remain historical failed evidence; S3 is no longer a mandatory provider for #13 following the owner's decision.

Current acceptance: BLOCKED — independently stored ciphertext and checksums verified; original-key AES authenticated restore and successful production Actions run not yet proven. Main IBO playlist must remain unchanged.
