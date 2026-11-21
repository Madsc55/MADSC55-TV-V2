# MADSC55 TV V2 — Stage 4 safe DNS capture implementation
Date: 2026-11-21

## Goal and hard limits
Enable **opt-in** bounded media sampling from ordinary DNS-hostname sources
without letting FFmpeg fetch arbitrary nested network URLs. This is a
**developer security implementation**, not an actual 18,074-channel scan or
evidence that any real channel is playing.

## Files
- `v2/turkish_safe_dns_capture.py`: strict URL parser; validate every DNS
  A/AAAA result; disallow private/link-local/multicast/reserved/IPv4-mapped
  addresses; use a vetted numeric IP for TCP; verify HTTPS certificate and
  SNI against the original hostname; reject redirects, invalid content,
  manifest bodies and oversized/timeout downloads.
- `v2/turkish_media_sample_capture.py`: DNS hostnames use the new pinned
  downloader; FFmpeg reads only a temporary private local file with
  `-protocol_whitelist file` and an explicit demuxer
  (MP4/Matroska/MPEG-TS); no output file is overwritten; language/device
  verdict always remains unverified.
- `v2/test_turkish_safe_dns_capture.py`: offline tests with fake resolver,
  fake HTTP response and mocked FFmpeg. No actual HTTP request.
- `v2/test_turkish_media_sample_capture.py`: retains existing IP-literal
  safety regressions and adds DNS syntax acceptance without DNS resolution.
- `.github/workflows/v2-main-production-safety-gate.yml`: tests included.

## Safeguards and acceptance
- All answers for one DNS lookup must be globally routable **unicast**, not
  just `is_global`. A single private or multicast answer fails closed.
- Connection goes to the pinned IP. No re-resolution on connect.
- HTTPS uses the original hostname for TLS/SNI and certificate checking.
- HTTP 30x is never followed. Credentials, ambiguous authority,
  backslashes, local-only hostnames, and URL fragments are rejected.
- Nested HLS/M3U8/DASH playlists, ffconcat scripts, HTML/text and unrecognized
  containers are rejected before FFmpeg.
- Download must respect byte budget and time limit.
- Decoding uses a private local input with only the `file` protocol;
  the output is linked exclusively to a new filename (no clobber).
- Keep `SAMPLE_CAPTURED_UNVERIFIED` separate from ASR/OCR, language approval
  and IBO Player device proof.

## Not yet completed
1. Adaptive HLS/DASH with separate segments or encryption is deliberately
   unsupported. It needs a per-resource validated egress proxy or a secure
   offline segment collector that checks **each** manifest, segment and key.
2. The pre-existing IP-literal FFmpeg transport is retained for compatibility,
   including its existing explicit protocol whitelist. That whitelist is **not
   an outbound firewall** and does not prove nested HLS segments are safe.
   It requires its own isolation/transport acceptance before declaring Stage
   4 globally complete.
3. No real IPTV stream capture, ASR/OCR/WebVTT language classification,
   685-channel retry, 18,074 full scan, archive transfer or playlist write
   has been performed by this PR.

## Repository invariants
Exactly one main IBO playlist is preserved, with no new playlist, no
re-adding 48 quarantined channels, no restoring the obsolete first-1,003
protection rule, no URL duplication and no changes to the user's channel
categories. Existing IBO 2,500-channel device test cycle remains separate.

## CI evidence
Production Security Gate will run the new offline regressions; use the
exact GitHub Actions run linked from PR #572 as the final acceptance record.
Passing offline tests will **not** be described as proof of a live stream.
