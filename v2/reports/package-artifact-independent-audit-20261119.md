# Independent package artifact audit — 2026-11-19

Scope: existing immutable GitHub Actions artifact only; no new discovery, AV probe, device playback, playlist write, archive mutation or restore execution.

- Source: Actions run https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43412576224, artifact ID `14033805492` (`v2-real-scan-evidence`).
- Downloaded ZIP SHA-256: `139c8a0868f35d4b64cd55a17bcbd56325d8e3c87b5d07295028bb4d56e832a6`, equal to GitHub artifact digest.
- Independent ZIP read found 14 entries. 1000-series contains five files with channel counts `1000,1000,1000,1000,301`. 2000-series contains three files with counts `2000,2000,301`.
- Every package has the `#EXTM3U` header; each file's URL count equals its `#EXTINF` count; no file exceeds its declared chunk size.
- Each series has 4,301 URL entries, 4,301 distinct URL strings. The concatenated URL sequences of the two series are identical **in order**, not just as sets.
- Embedded `ibo-real-scan-report.json` records `http_hls_ok=4301`, `av_verified=4301`, `archive_restore_test_passed=true`, `mock_data_used=false`, `playback_verified_on_device=false`, `status=READY_FOR_DEVICE_TEST`.
- Important evidence boundary: the JSON values are **claims in the existing run's report**, not newly repeated HTTP/FFmpeg checks or independently observed production restore. This audit independently validates package structure and archive integrity only. The report's restore-test flag does not establish an independent production restore acceptance.
- No device/IBO playback was observed. Do **not** close tasks 28–33 or claim final production acceptance on this audit alone.

Next acceptance gates: separately verified IBO device playback for the actual packages, independent production restore with matching evidence, and provenance/AV acceptance per policy. Preserve the protected main playlist and the excluded 48 entries; do not create new playlists or start a channel search until system completion.
