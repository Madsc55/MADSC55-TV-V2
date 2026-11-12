# Stage 4 / #24 — evidence audit (2026-11-12)

Scope: isolated Stage 4 acceptance; do not modify main IBO playlist or Stage 2/3 branches. This report is **not** an acceptance certificate.

## Verified historical GitHub Actions evidence

| Run | Artifact | GitHub artifact SHA-256 | Logged result |
|---|---|---|---|
| [41742204286](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/41742204286) | 13282545632, `stage5-encrypted-archive-batch.log` | `ddd35329a57bf9a17e3b8d3ea8748dedb4b5f25d88bccf1e91b3fc1a71c8f1ce` | `Ran 38 tests ... OK` |
| [41742204320](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/41742204320) | 13282561013, `stage5-final-archive-regressions.log` | `a49d28b4abb90913bd9a1fbfd0e5f2328ddfc157c18ac382eec769a7905d7dd2` | `Ran 49 tests ... OK` |

Both Actions jobs concluded success. Artifacts were available and ZIP logs were inspected on 2026-11-12. These are historical Stage 5 **regression** results, not a fresh Stage 4 end-to-end run. A mock remote-store test does not demonstrate independent production S3/Drive restoration.

## #24 fail-closed acceptance ledger

- [ ] #9 real discovery prerequisite: independently confirmed run and proof artifact.
- [ ] #13 real offsite backup **download and restore** prerequisite: independently confirmed with original encrypted archive and secret, without exposing credentials.
- [ ] #23 live Master Engine prerequisite: independently confirmed run and proof artifact.
- [ ] Live discovery → recovery → FFmpeg video **and** audio proof for accepted channels, with immutable artifact digests.
- [ ] Encrypted archive → external storage → independent restoration and content hash match.
- [ ] One grouped Stage 4 end-to-end acceptance run with authenticated GitHub Actions artifacts.
- [ ] Confirm main IBO playlist blob unchanged before/after acceptance.

The Stage 4 gate currently rejects even structurally complete manifests until independent evidence verification exists. This is intentional fail-closed behavior, **not** a passing acceptance test. Do not close #24 or merge Stage 4 changes as accepted until all checks are proven.

## Separation and safety

This report is committed only to `stage4-24-independent-acceptance`. No Stage 2/3 branches, production playlist, secrets, or protected branch are changed.

## Independent ZIP integrity verification (2026-11-12)

Downloaded artifacts 13282545632 and 13282561013 were inspected as ZIP files locally. Independently computed SHA-256 values exactly match the two GitHub artifact digests recorded above. The ZIP members contain `stage5-encrypted-archive-batch.log` (`Ran 38 tests ... OK`) and `stage5-final-archive-regressions.log` (`Ran 49 tests ... OK`) respectively. This verifies **artifact byte integrity and logged regression outcomes only**. No Stage 4 live run or offsite production restore was performed by this verification.

## Live grouped result — 2026-11-12

[Run 43194979636](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43194979636) passed on isolated commit `3905016b305ddf8a579d7bc2122a6af1591c355a`. The production gate and pinned request verified the protected IBO blob. The live Master discovered and checked 7769 candidates from 46 sources, with 803 true FFmpeg AV results. A separate Actions runner downloaded artifact 13934099792 and authenticated and restored 7819 encrypted entries, including all 4955 exact historical rows. The restore receipt is artifact 13934324379. Both ZIP digests and the inner archive digest were independently recomputed.

The #9, #13 and #23 prerequisite Actions runs are confirmed. The new archive was restored from remote GitHub Actions artifact storage. Same-run Drive restoration of the new archive remains open under the current task ledger. The production Drive service account is a reader in the existing backup folder. #24 remains open.

## Current grouped live result — 2026-11-12, run 43220496123

[Run 43220496123](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43220496123) completed all four jobs successfully on commit `ab520452553034bb959ff426c12281c93a53de4c`. Production security and protected IBO invariant passed. The live engine fetched 46/46 sources, examined 7,769 candidates, and reported 798 FFmpeg video+audio verifications (797 TR/AZ), with zero unfinished checks. An independent Actions runner restored 7,819 records, including 4,955 historical records, from the exact encrypted Actions artifact.

- [Encrypted archive artifact 13949375384](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43220496123/artifacts/13949375384), ZIP SHA-256 `81e35b84eb22a9ea04c9ff73f86c674689d9ec1a730f61163c48e5942b4acb17`; matching digest logged by downloader.
- [Independent restore receipt artifact 13947883316](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43220496123/artifacts/13947883316), ZIP SHA-256 `ad3274f25e79bf3e09070bcbf153da51156b5fc840e2b844bb0c7633ff380094`.
- Inner encrypted archive SHA-256 `5be3e93559d3a946ae2265e5a960873b26940e4605966ef872b0b8b7ab1dbff0`.

**Acceptance boundary:** This confirms remote GitHub Actions artifact restoration, not S3 or Drive restoration of this exact archive. Do not treat the previous external backup prerequisite #13 as proof that this new archive was restored offsite. #24 stays open until the required independent offsite storage restore and all ledger gates are verified. Do not modify the main IBO playlist.
