# MADSC55 TV V2 — Operational status

## Run
```bash
python3 master.py --run
```

GitHub Actions runs the read-only audit twice daily. Reports are uploaded as a workflow artifact (not committed into the live playlist).

## Reports
- `turkish-tv-health.json`: live playlist network probes, responsive Turkish candidates, YouTube metadata, and sampled ffprobe codec checks.
- `assets-health.json`: EPG/logo HTTP reachability.
- `epg-integrity.json`: bounded XMLTV structural checks and programme counts.
- `logo-attribution.json`: source domains and unverified ownership.
- `master-summary.json`: consolidated results and verification limitations.

## Decoder coverage
The default `MADSC55_DECODER_SAMPLE=30` tests a rotating subset of responsive entries. For a **manual** full-sample run, set `MADSC55_DECODER_SAMPLE=1039` before `python3 master.py --run`. A full run may take hours, so it is **not** used in the 25-minute scheduled GitHub workflow. ffprobe stream identification does **not** prove continuous audio/video playback.

## Protection and outstanding verification
All audits are read-only against `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`. Master compares SHA-256 before and after. No candidate is automatically added to IBO or favorites. Remote HTTP responses, XMLTV validity and logo reachability do not establish playback continuity, channel mapping, or official logo ownership. Those require independent, per-channel evidence.

## Full decoder workflow
The GitHub Actions workflow `V2 Full Decoder Verification (manual, read-only)` uses `MADSC55_DECODER_SAMPLE=1039` and allows up to 180 minutes. It also runs automatically every Sunday at 02:15 UTC. To start immediately, use **Actions → V2 Full Decoder Verification → Run workflow**. It checks decodability for all *responsive* entries (not all entries if unreachable). Reports remain evidence of codec detection, not sustained playback or official logo provenance.
