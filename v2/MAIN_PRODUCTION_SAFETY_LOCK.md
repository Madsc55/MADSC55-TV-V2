# MADSC55 TV V2 — Main Production Actions File Lock

The production workflow files were put into a fail-closed state without changing
the canonical MADSC55_TV_IBO_CALISANLAR_TEST.m3u8 playlist.

- Original 19 contents-write production workflows are suspended as manual,
  read-only audit jobs. Their original sources remain recoverable from Git history;
  they must not be reactivated without reviewed playlist-owner authorization.
- Other original workflows are now manual-only; the read-only playlist safety
  check remains activated by relevant pushes.
- A dedicated main safety workflow runs when main is pushed or a PR targets
  main. It checks all registered workflow files, privilege scopes, trigger events,
  writer suspension and the immutable main playlist Git blob.
- This checked-in lock cannot replace a server-side GitHub branch rule. The
  GitHub managed app lacks administration write access and cannot create rules.
- A repository administrator must enable a main branch ruleset with mandatory
  PR approval, no admin bypass, no force pushes/deletion and required status
  check from V2 Main Production Security Gate.

Settings: https://github.com/Madsc55/MADSC55-TV-V2/settings/rules

Do not merge PR #9 or alter the playlist while applying the platform rules.
