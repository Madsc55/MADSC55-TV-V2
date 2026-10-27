# MADSC55 TV V2

Independent V2. The existing IBO playlist remains unchanged and is the only live playlist.

- Playlist: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`
- EPG: existing `https://madsc55.github.io/madsc-tv/madsc-epg.xml` (not migrated yet).
- Logos: existing `tvg-logo` URLs preserved; 194 unique URLs inventoried in `yedekler/logo-kaynaklari.md`. Image bytes not yet mirrored.
- Worldwide discovery: `v2/discover.py`, source list `v2/config/sources.json`; report only, no automatic additions.
- GitHub Actions: manual trigger or twice-daily scheduled discovery; candidate report is an artifact, not a live update.

**Do not delete legacy EPG repo** until a new EPG URL is created, verified on IBO and playlist header is migrated. Do not delete legacy playlist repo until backups are independently verified and any remaining external dependencies are checked.
