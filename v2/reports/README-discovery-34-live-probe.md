# Discovery #34 live metadata probe

A merge commit containing the literal marker `#34 live probe` on `main` triggers the guarded `live-discovery-diagnostic` job in `v2-main-production-safety-gate.yml`.

The job queries six search terms across GitHub, GitLab and Codeberg, records read-only metadata diagnostics as the `v2-discovery-34-live-diagnostic` Actions artifact, and does not update playlists or certify decoded video/audio.

A provider rate limit or missing evidence must remain incomplete; a green production security gate is not itself live discovery acceptance.

Trigger verification: the **actual main commit message**, not merely the PR title or body, must contain `#34 live probe`. Check the resulting main-branch workflow run and its diagnostic artifact before claiming any API calls occurred.
