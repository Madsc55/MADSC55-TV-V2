# Stage 5 real-production evidence audit — 2026-11-12

Source: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` on repository default branch.
Source Git blob SHA: `165c726cd9211f9f51c31f1c718e0911bab79e1b`.

| Check | Observed |
| --- | ---: |
| EXTINF records | 876 |
| Stream URL lines | 876 |
| Distinct stream URLs | 452 |
| Additional repeated URL occurrences | 424 |
| Nonempty tvg-id occurrences | 589 |
| Distinct nonempty tvg-id values | 140 |

These are **inventory counts only**. Neither URL uniqueness nor tvg-id uniqueness demonstrates actual AV playback or unique channel identity. No evidence of 1000/2000 distinct real AV-proven channels was established by this audit.

## Acceptance gate

- #28 remains OPEN until 1000 distinct channel identities have verifiable real video+audio evidence, with integrity-checked evidence records and an exported, independently validated M3U.
- #29 remains OPEN until the same is true for 2000 channels; 2000 must include the accepted first 1000.
- #30 remains OPEN until real exported packages pass M3U parsing, unique-identity/URL checks, evidence-to-entry reconciliation, and protected-playlist hash comparison.
- Synthetic fixtures and HTTP-only checks cannot be counted as real production evidence.
- Protected original IBO playlist was read, not modified. No production export or successful Actions acceptance was claimed.
