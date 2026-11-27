# MADSC55 TV V2 — MASTER_TODO

27 Kasım 2026 | Ana kaynak snapshot: `bc93dc7811ae8976f097c6b5e9addb5e6db67045`. Bu dosya tek merkezî görev/not indeksidir; yürütme yetkisi değildir. Ana playlist, kanallar, kategoriler, eski 34 görev ve 685 SECURITY HOLD kilidi değişmez. #794 ile kapanan 10/10 offline kapsam korunur. Tarihsel notlar kendi tarihindeki ifadeleri taşır; eski talimatlar otomatik olarak yeniden yürürlüğe girmez. Aynı talep farklı kaynakta kaydedilmişse kaynak kayıtları ayrı tutulur. Bir kaynak satırında birden fazla şart bulunuyorsa özgün bağlam korunur. Akış adresleri/olası sırlar burada yeniden yayımlanmaz; tam kaynak konumu gösterilir.

Durum sözlüğü: **Güncel** = halen geçerli koruma veya açık kayıt; **Tarihsel** = kaynak tarihindeki not/iş, son durum ayrıca doğrulanmalı; **Arşiv/kapsam dışı** = önceki sahibi onaylı kapanış; **Offline kabul** = #794 kapsamı, gerçek cihaz/yayın kabulü değildir; **Bekliyor** = kaynakta açık veya doğrulanmamış, otomatik uygulama yok.

Tarama kapsamı: main ağacındaki tüm .md/.txt/.json/.yml/.yaml dosyaları, açık Issue ve açık PR'lar; açık PR'ların değişen not dosyaları ayrıca. Dosya bazlı tarama fihristi en altta. Makine verilerindeki kanal başına URL/logo/pozisyon satırları ayrı kullanıcı görevi değildir; görev, not, açıklama, durum ve kural alanları indekslenir. Sadece aynı kaynak içindeki yapı satırları (örneğin JSON parantezleri) ayıklanır.

## A) Kullanıcı Tarafından Kaydettirilmiş Özel Notlar ve İstekler

- **.github/workflows/build_playlist_from_parts.yml:L66** — [Tarihsel yapılandırma kaydı] # Owner command remains on one isolated branch, never staging through main.
- **.github/workflows/build_playlist_from_parts.yml:L79** — [Tarihsel yapılandırma kaydı] - name: Allow only a new owner command against current main
- **.github/workflows/ci.yml:L22** — [Tarihsel yapılandırma kaydı] - name: Detect exact owner move-only PR (trusted base verifier)
- **.github/workflows/ci.yml:L71** — [Tarihsel yapılandırma kaydı] # Only the explicitly tagged owner-requested squash merge on main runs
- **.github/workflows/ci.yml:L109** — [Tarihsel yapılandırma kaydı] # One owner-requested, reviewed merge only; never from untrusted PRs.

<!-- A-END -->

## B) Yarım Kalmış / Beklemeye Alınmış Teknik ve Kurtarma İşleri

- **.github/workflows/alphabetize-yeni-turk.yml:L1** — [Tarihsel yapılandırma kaydı] name: Alphabetize YENI TURK (production writer suspended)
- **.github/workflows/alphabetize-yeni-turk.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/autonomous_discovery_readonly.yml:L1** — [Tarihsel yapılandırma kaydı] name: Autonomous Discovery Read Only
- **.github/workflows/autonomous_discovery_readonly.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/autonomous_discovery_readonly.yml:L6** — [Tarihsel yapılandırma kaydı] description: 'Approved HTTPS M3U feed URL; empty means inventory-only report'
- **.github/workflows/autonomous_discovery_readonly.yml:L10** — [Tarihsel yapılandırma kaydı] description: 'Optional reviewed 685-entry manifest path in repository'
- **.github/workflows/autonomous_discovery_readonly.yml:L14** — [Tarihsel yapılandırma kaydı] description: 'Maximum bounded candidate checks'
- **.github/workflows/autonomous_discovery_readonly.yml:L28** — [Tarihsel yapılandırma kaydı] - name: Install local-only AV tools
- **.github/workflows/autonomous_discovery_readonly.yml:L30** — [Tarihsel yapılandırma kaydı] - name: Download historical 685 manifest using GitHub Actions artifact service
- **.github/workflows/autonomous_discovery_readonly.yml:L33** — [Tarihsel yapılandırma kaydı] name: v2-497-existing-audit-preview
- **.github/workflows/autonomous_discovery_readonly.yml:L37** — [Tarihsel yapılandırma kaydı] - name: Verify immutable historical 685 manifest
- **.github/workflows/autonomous_discovery_readonly.yml:L55** — [Tarihsel yapılandırma kaydı] - name: Run bounded candidate discovery in disposable directory
- **.github/workflows/autonomous_discovery_readonly.yml:L104** — [Tarihsel yapılandırma kaydı] - name: Publish discovery results only
- **.github/workflows/autonomous_discovery_readonly.yml:L105** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/autonomous_discovery_readonly.yml:L108** — [Tarihsel yapılandırma kaydı] name: discovery-results
- **.github/workflows/backups-logo-audit.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/build_playlist_from_parts.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/build_playlist_from_parts.yml:L17** — [Tarihsel yapılandırma kaydı] if: "github.ref == 'refs/heads/main' && !contains(github.event.head_commit.message, '[skip ci]')"
- **.github/workflows/build_playlist_from_parts.yml:L38** — [Tarihsel yapılandırma kaydı] - name: Create validated proposal branch (never push main)
- **.github/workflows/build_playlist_from_parts.yml:L58** — [Tarihsel yapılandırma kaydı] # Repository settings forbid GitHub Actions bots from creating PRs.
- **.github/workflows/build_playlist_from_parts.yml:L59** — [Tarihsel yapılandırma kaydı] # Leave a validated, isolated proposal branch and report it explicitly;
- **.github/workflows/build_playlist_from_parts.yml:L60** — [Tarihsel yapılandırma kaydı] # an authorized GitHub identity can open a PR with required checks.
- **.github/workflows/build_playlist_from_parts.yml:L99** — [Tarihsel yapılandırma kaydı] - name: Apply and validate authorized command
- **.github/workflows/build_playlist_from_parts.yml:L106** — [Tarihsel yapılandırma kaydı] - name: Push validated proposal to SAME command branch
- **.github/workflows/ci.yml:L1** — [Tarihsel yapılandırma kaydı] name: Offline CI
- **.github/workflows/ci.yml:L5** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/ci.yml:L17** — [Tarihsel yapılandırma kaydı] # The default shallow checkout omits those Git objects.
- **.github/workflows/ci.yml:L41** — [Tarihsel yapılandırma kaydı] - name: Install full-suite offline dependencies
- **.github/workflows/ci.yml:L42** — [Tarihsel yapılandırma kaydı] if: steps.move_scope.outputs.eligible != 'true'
- **.github/workflows/ci.yml:L44** — [Tarihsel yapılandırma kaydı] - name: Run full offline regression suite
- **.github/workflows/ci.yml:L45** — [Tarihsel yapılandırma kaydı] if: steps.move_scope.outputs.eligible != 'true'
- **.github/workflows/ci.yml:L47** — [Tarihsel yapılandırma kaydı] - name: Verify deep AV decision lock
- **.github/workflows/ci.yml:L49** — [Tarihsel yapılandırma kaydı] - name: Verify system FFmpeg quality fixtures before merge
- **.github/workflows/ci.yml:L50** — [Tarihsel yapılandırma kaydı] if: steps.move_scope.outputs.eligible != 'true'
- **.github/workflows/ci.yml:L59** — [Tarihsel yapılandırma kaydı] - name: Install move-only YAML audit dependency
- **.github/workflows/ci.yml:L60** — [Tarihsel yapılandırma kaydı] if: steps.move_scope.outputs.eligible == 'true'
- **.github/workflows/ci.yml:L63** — [Tarihsel yapılandırma kaydı] if: steps.move_scope.outputs.eligible == 'true'
- **.github/workflows/ci.yml:L70** — [Tarihsel yapılandırma kaydı] name: Read-only bounded shared URL evidence
- **.github/workflows/ci.yml:L72** — [Tarihsel yapılandırma kaydı] # public-network sampling. Never run from untrusted PRs or on a schedule.
- **.github/workflows/ci.yml:L73** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[shared-url-safe-review]')
- **.github/workflows/ci.yml:L86** — [Tarihsel yapılandırma kaydı] - name: Reuse SHA-bound preceding evidence (skip already audited URLs)
- **.github/workflows/ci.yml:L91** — [Tarihsel yapılandırma kaydı] - name: Verify public-IP pinning, HLS bounds and offline PSI fixtures
- **.github/workflows/ci.yml:L95** — [Tarihsel yapılandırma kaydı] - name: Bounded read-only shared URL sample
- **.github/workflows/ci.yml:L98** — [Tarihsel yapılandırma kaydı] - name: Upload no-token evidence (never upload stream URLs)
- **.github/workflows/ci.yml:L99** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L102** — [Tarihsel yapılandırma kaydı] name: shared-url-safe-live-review
- **.github/workflows/ci.yml:L127** — [Tarihsel yapılandırma kaydı] - name: Validate safe read-only probe and shard invariants
- **.github/workflows/ci.yml:L130** — [Tarihsel yapılandırma kaydı] - name: Audit at most 500 unique URLs in this shard
- **.github/workflows/ci.yml:L133** — [Tarihsel yapılandırma kaydı] - name: Save no-token, checkpointed evidence
- **.github/workflows/ci.yml:L134** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L143** — [Tarihsel yapılandırma kaydı] name: Verify complete URL coverage and save summary
- **.github/workflows/ci.yml:L158** — [Tarihsel yapılandırma kaydı] - name: Download shard reports from this run only
- **.github/workflows/ci.yml:L163** — [Tarihsel yapılandırma kaydı] - name: Refuse missing, stale, or duplicate URL results
- **.github/workflows/ci.yml:L166** — [Tarihsel yapılandırma kaydı] - name: Publish completeness result, even on partial scan
- **.github/workflows/ci.yml:L167** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L176** — [Tarihsel yapılandırma kaydı] name: Local decoded A/V review ${{ matrix.shard }}
- **.github/workflows/ci.yml:L177** — [Tarihsel yapılandırma kaydı] # A single approved main merge; no schedule, PR network probes or publisher.
- **.github/workflows/ci.yml:L196** — [Tarihsel yapılandırma kaydı] - name: Install pinned self-contained FFmpeg binary
- **.github/workflows/ci.yml:L200** — [Tarihsel yapılandırma kaydı] - name: Verify FFmpeg and local-only decoded A/V safety
- **.github/workflows/ci.yml:L203** — [Tarihsel yapılandırma kaydı] - name: Retrieve SHA-bound prior metadata evidence
- **.github/workflows/ci.yml:L210** — [Tarihsel yapılandırma kaydı] - name: Decode bounded local MPEG-TS sample for every URL
- **.github/workflows/ci.yml:L213** — [Tarihsel yapılandırma kaydı] - name: Upload checkpoint for this shard
- **.github/workflows/ci.yml:L214** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L223** — [Tarihsel yapılandırma kaydı] name: Validate 100% of URL decode attempts
- **.github/workflows/ci.yml:L238** — [Tarihsel yapılandırma kaydı] - name: Download results from this same workflow run
- **.github/workflows/ci.yml:L243** — [Tarihsel yapılandırma kaydı] - name: Fail if any URLs are missing or prior SHA differs
- **.github/workflows/ci.yml:L246** — [Tarihsel yapılandırma kaydı] - name: Save verified coverage and separated A/V outcomes
- **.github/workflows/ci.yml:L247** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L275** — [Tarihsel yapılandırma kaydı] - name: Validate public IP pinning, pipe-only decode and failure policy
- **.github/workflows/ci.yml:L282** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L309** — [Tarihsel yapılandırma kaydı] - name: Validate exact coverage and report markable positions
- **.github/workflows/ci.yml:L312** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L347** — [Tarihsel yapılandırma kaydı] - name: Test local decoder and bounded public network safety
- **.github/workflows/ci.yml:L354** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L390** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L430** — [Tarihsel yapılandırma kaydı] - name: Ensure system FFmpeg is installed
- **.github/workflows/ci.yml:L436** — [Tarihsel yapılandırma kaydı] - name: Verify existing safe probe and actual synthetic local media quality
- **.github/workflows/ci.yml:L443** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L485** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L519** — [Tarihsel yapılandırma kaydı] - name: Ensure system FFmpeg is installed
- **.github/workflows/ci.yml:L525** — [Tarihsel yapılandırma kaydı] - name: Verify offline safety and decoder
- **.github/workflows/ci.yml:L530** — [Tarihsel yapılandırma kaydı] - name: Targeted evidence review
- **.github/workflows/ci.yml:L533** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L608** — [Tarihsel yapılandırma kaydı] - name: Ensure system FFmpeg is installed
- **.github/workflows/ci.yml:L614** — [Tarihsel yapılandırma kaydı] - name: Verify offline safety and decoder
- **.github/workflows/ci.yml:L619** — [Tarihsel yapılandırma kaydı] - name: Targeted evidence review
- **.github/workflows/ci.yml:L622** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L690** — [Tarihsel yapılandırma kaydı] - name: Ensure system FFmpeg
- **.github/workflows/ci.yml:L696** — [Tarihsel yapılandırma kaydı] - name: Verify safety and decoder fixtures
- **.github/workflows/ci.yml:L701** — [Tarihsel yapılandırma kaydı] - name: Fresh bounded quality test
- **.github/workflows/ci.yml:L704** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L766** — [Tarihsel yapılandırma kaydı] - name: Ensure system FFmpeg
- **.github/workflows/ci.yml:L772** — [Tarihsel yapılandırma kaydı] - name: Verify safety and decoder fixtures
- **.github/workflows/ci.yml:L777** — [Tarihsel yapılandırma kaydı] - name: Fresh bounded quality test
- **.github/workflows/ci.yml:L780** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L855** — [Tarihsel yapılandırma kaydı] name: Nonforeign all-category fresh quality shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L874** — [Tarihsel yapılandırma kaydı] - name: Ensure system FFmpeg
- **.github/workflows/ci.yml:L880** — [Tarihsel yapılandırma kaydı] - name: Verify safety and decoder fixtures
- **.github/workflows/ci.yml:L892** — [Tarihsel yapılandırma kaydı] - name: Fresh bounded quality test
- **.github/workflows/ci.yml:L895** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/ci.yml:L897** — [Tarihsel yapılandırma kaydı] name: nonforeign-fresh-${{ matrix.shard }}
- **.github/workflows/ci.yml:L903** — [Tarihsel yapılandırma kaydı] name: Nonforeign all-category fresh coverage
- **.github/workflows/ci.yml:L925** — [Tarihsel yapılandırma kaydı] name: nonforeign-fresh-summary
- **.github/workflows/full-turkish-backups-audit.yml:L1** — [Tarihsel yapılandırma kaydı] name: Full Turkish backups audit (production writer suspended)
- **.github/workflows/full-turkish-backups-audit.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/full_autonomous_pipeline.yml:L1** — [Tarihsel yapılandırma kaydı] name: Full Autonomous Discovery and Acceptance
- **.github/workflows/full_autonomous_pipeline.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/full_autonomous_pipeline.yml:L6** — [Tarihsel yapılandırma kaydı] description: 'Approved public M3U/M3U8 feed URL (optional)'
- **.github/workflows/full_autonomous_pipeline.yml:L10** — [Tarihsel yapılandırma kaydı] description: 'Maximum new candidates per run'
- **.github/workflows/full_autonomous_pipeline.yml:L20** — [Tarihsel yapılandırma kaydı] if: ${{ false }} # SECURITY HOLD: network/AV and PR writer require separate approval
- **.github/workflows/full_autonomous_pipeline.yml:L25** — [Tarihsel yapılandırma kaydı] - name: Install bounded local-media dependencies
- **.github/workflows/full_autonomous_pipeline.yml:L33** — [Tarihsel yapılandırma kaydı] - name: Upload evidence (never publish stream URLs)
- **.github/workflows/full_autonomous_pipeline.yml:L34** — [Tarihsel yapılandırma kaydı] if: always()
- **.github/workflows/full_autonomous_pipeline.yml:L37** — [Tarihsel yapılandırma kaydı] name: autonomous-acceptance-evidence
- **.github/workflows/ibo-authorized-500.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/ibo-authorized-500.yml:L13** — [Tarihsel yapılandırma kaydı] - name: Download scan artifact
- **.github/workflows/ibo-authorized-500.yml:L19** — [Tarihsel yapılandırma kaydı] - name: Extract all scan candidates and import legacy archive
- **.github/workflows/ibo-authorized-500.yml:L33** — [Tarihsel yapılandırma kaydı] - name: Create protected-branch PR
- **.github/workflows/ibo-real-scan.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/ibo-single-playlist-transfer-offline.yml:L24** — [Tarihsel yapılandırma kaydı] - name: Offline archive transfer regression
- **.github/workflows/import-backup-candidates.yml:L1** — [Tarihsel yapılandırma kaydı] name: Backup candidates import (production writer suspended)
- **.github/workflows/import-backup-candidates.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/issue-489-historical-audit.yml:L7** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/move-turkish-backups.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/repair-playlist-grouping.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/run_move_685.yml:L1** — [Tarihsel yapılandırma kaydı] name: Manual 685 archive move PR publisher
- **.github/workflows/run_move_685.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/run_move_685.yml:L16** — [Tarihsel yapılandırma kaydı] - name: Download historical 685 identity manifest
- **.github/workflows/run_move_685.yml:L19** — [Tarihsel yapılandırma kaydı] name: v2-497-existing-audit-preview
- **.github/workflows/run_move_685.yml:L39** — [Tarihsel yapılandırma kaydı] - name: Open reviewed 685 migration PR (never write main)
- **.github/workflows/run_pass1_cleanup.yml:L1** — [Tarihsel yapılandırma kaydı] name: Pass 1 cleanup (read-only artifact)
- **.github/workflows/run_pass1_cleanup.yml:L3** — [Tarihsel yapılandırma kaydı] workflow_dispatch:
- **.github/workflows/run_pass1_cleanup.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Offline regression test
- **.github/workflows/run_pass1_cleanup.yml:L16** — [Tarihsel yapılandırma kaydı] - name: Run offline cleanup
- **.github/workflows/run_pass1_cleanup.yml:L21** — [Tarihsel yapılandırma kaydı] name: pass1-cleanup-results

<!-- B-END -->

## C) Kanal Testi, Taşıma ve Kategori Düzenleme İşleri

- **.github/workflows/alphabetize-yeni-turk.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Verify protected IBO playlist without changing it
- **.github/workflows/backups-logo-audit.yml:L1** — [Tarihsel yapılandırma kaydı] name: Alphabetize backups and audit logos (production writer suspended)
- **.github/workflows/backups-logo-audit.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Verify protected IBO playlist without changing it
- **.github/workflows/build_playlist_from_parts.yml:L1** — [Tarihsel yapılandırma kaydı] name: Build canonical IBO playlist from parts
- **.github/workflows/build_playlist_from_parts.yml:L29** — [Tarihsel yapılandırma kaydı] - name: Apply reviewed channel command and validate canonical inventory
- **.github/workflows/build_playlist_from_parts.yml:L67** — [Tarihsel yapılandırma kaydı] if: "startsWith(github.ref, 'refs/heads/command/ibo-') && github.actor == 'Madsc55'"
- **.github/workflows/ci.yml:L16** — [Tarihsel yapılandırma kaydı] # Playlist invariants read immutable historical blobs with git cat-file.
- **.github/workflows/ci.yml:L62** — [Tarihsel yapılandırma kaydı] - name: Test channel move invariants and workflow security only
- **.github/workflows/ci.yml:L108** — [Tarihsel yapılandırma kaydı] name: Full playlist read-only sample ${{ matrix.shard }}
- **.github/workflows/ci.yml:L110** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[full-ibo-url-audit]')
- **.github/workflows/ci.yml:L137** — [Tarihsel yapılandırma kaydı] name: full-ibo-audit-${{ matrix.shard }}
- **.github/workflows/ci.yml:L145** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[full-ibo-url-audit]')
- **.github/workflows/ci.yml:L170** — [Tarihsel yapılandırma kaydı] name: full-ibo-audit-summary
- **.github/workflows/ci.yml:L178** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[full-ibo-av-decode]')
- **.github/workflows/ci.yml:L208** — [Tarihsel yapılandırma kaydı] name: full-ibo-audit-${{ matrix.shard }}
- **.github/workflows/ci.yml:L217** — [Tarihsel yapılandırma kaydı] name: full-ibo-decode-${{ matrix.shard }}
- **.github/workflows/ci.yml:L225** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[full-ibo-av-decode]')
- **.github/workflows/ci.yml:L250** — [Tarihsel yapılandırma kaydı] name: full-ibo-av-summary
- **.github/workflows/ci.yml:L256** — [Tarihsel yapılandırma kaydı] name: YEDEKLER decoded AV shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L257** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-av-20261124]')
- **.github/workflows/ci.yml:L279** — [Tarihsel yapılandırma kaydı] - name: Decode only YEDEKLER, retry unresolved
- **.github/workflows/ci.yml:L284** — [Tarihsel yapılandırma kaydı] name: yedekler-av-20261124-${{ matrix.shard }}
- **.github/workflows/ci.yml:L290** — [Tarihsel yapılandırma kaydı] name: YEDEKLER complete coverage and confirmed failures
- **.github/workflows/ci.yml:L292** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-av-20261124]')
- **.github/workflows/ci.yml:L314** — [Tarihsel yapılandırma kaydı] name: yedekler-av-20261124-summary
- **.github/workflows/ci.yml:L320** — [Tarihsel yapılandırma kaydı] name: YEDEKLER deep review shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L321** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-deep-review-20261124]')
- **.github/workflows/ci.yml:L344** — [Tarihsel yapılandırma kaydı] name: yedekler-av-20261124-summary
- **.github/workflows/ci.yml:L351** — [Tarihsel yapılandırma kaydı] - name: Review only prior unresolved channels with alternate segments
- **.github/workflows/ci.yml:L356** — [Tarihsel yapılandırma kaydı] name: yedekler-deep-review-${{ matrix.shard }}
- **.github/workflows/ci.yml:L362** — [Tarihsel yapılandırma kaydı] name: YEDEKLER deep review coverage and outcomes
- **.github/workflows/ci.yml:L364** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-deep-review-20261124]')
- **.github/workflows/ci.yml:L382** — [Tarihsel yapılandırma kaydı] name: yedekler-av-20261124-summary
- **.github/workflows/ci.yml:L392** — [Tarihsel yapılandırma kaydı] name: yedekler-deep-review-summary
- **.github/workflows/ci.yml:L398** — [Tarihsel yapılandırma kaydı] name: YEDEKLER quality review shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L399** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-quality-20261124]')
- **.github/workflows/ci.yml:L422** — [Tarihsel yapılandırma kaydı] name: yedekler-av-20261124-summary
- **.github/workflows/ci.yml:L428** — [Tarihsel yapılandırma kaydı] name: yedekler-deep-review-summary
- **.github/workflows/ci.yml:L440** — [Tarihsel yapılandırma kaydı] - name: Review 1209 unresolved channels with duration and quality evidence
- **.github/workflows/ci.yml:L445** — [Tarihsel yapılandırma kaydı] name: yedekler-quality-${{ matrix.shard }}
- **.github/workflows/ci.yml:L451** — [Tarihsel yapılandırma kaydı] name: YEDEKLER quality review complete coverage
- **.github/workflows/ci.yml:L453** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-quality-20261124]')
- **.github/workflows/ci.yml:L471** — [Tarihsel yapılandırma kaydı] name: yedekler-av-20261124-summary
- **.github/workflows/ci.yml:L477** — [Tarihsel yapılandırma kaydı] name: yedekler-deep-review-summary
- **.github/workflows/ci.yml:L487** — [Tarihsel yapılandırma kaydı] name: yedekler-quality-summary
- **.github/workflows/ci.yml:L493** — [Tarihsel yapılandırma kaydı] name: YEDEKLER targeted recheck shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L494** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-targeted-20261124]')
- **.github/workflows/ci.yml:L517** — [Tarihsel yapılandırma kaydı] name: yedekler-quality-summary
- **.github/workflows/ci.yml:L535** — [Tarihsel yapılandırma kaydı] name: yedekler-targeted-${{ matrix.shard }}
- **.github/workflows/ci.yml:L541** — [Tarihsel yapılandırma kaydı] name: YEDEKLER targeted complete coverage
- **.github/workflows/ci.yml:L543** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-targeted-20261124]')
- **.github/workflows/ci.yml:L561** — [Tarihsel yapılandırma kaydı] name: yedekler-quality-summary
- **.github/workflows/ci.yml:L570** — [Tarihsel yapılandırma kaydı] name: yedekler-targeted-summary
- **.github/workflows/ci.yml:L576** — [Tarihsel yapılandırma kaydı] name: YEDEKLER 448 follow-up recheck shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L577** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-448-20261124]')
- **.github/workflows/ci.yml:L600** — [Tarihsel yapılandırma kaydı] name: yedekler-quality-summary
- **.github/workflows/ci.yml:L606** — [Tarihsel yapılandırma kaydı] name: yedekler-targeted-summary
- **.github/workflows/ci.yml:L624** — [Tarihsel yapılandırma kaydı] name: yedekler-followup-${{ matrix.shard }}
- **.github/workflows/ci.yml:L630** — [Tarihsel yapılandırma kaydı] name: YEDEKLER 448 follow-up complete coverage
- **.github/workflows/ci.yml:L632** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-448-20261124]')
- **.github/workflows/ci.yml:L650** — [Tarihsel yapılandırma kaydı] name: yedekler-quality-summary
- **.github/workflows/ci.yml:L656** — [Tarihsel yapılandırma kaydı] name: yedekler-targeted-summary
- **.github/workflows/ci.yml:L665** — [Tarihsel yapılandırma kaydı] name: yedekler-followup-summary
- **.github/workflows/ci.yml:L672** — [Tarihsel yapılandırma kaydı] name: YEDEKLER full 1562 fresh quality shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L673** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-full-1562-20261124]')
- **.github/workflows/ci.yml:L706** — [Tarihsel yapılandırma kaydı] name: yedekler-fresh-${{ matrix.shard }}
- **.github/workflows/ci.yml:L712** — [Tarihsel yapılandırma kaydı] name: YEDEKLER full 1562 fresh coverage
- **.github/workflows/ci.yml:L714** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-full-1562-20261124]')
- **.github/workflows/ci.yml:L734** — [Tarihsel yapılandırma kaydı] name: yedekler-fresh-summary
- **.github/workflows/ci.yml:L740** — [Tarihsel yapılandırma kaydı] name: YEDEKLER 1562 reason quality shard ${{ matrix.shard }}
- **.github/workflows/ci.yml:L741** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-reasons-1562-20261124]')
- **.github/workflows/ci.yml:L764** — [Tarihsel yapılandırma kaydı] name: yedekler-fresh-summary
- **.github/workflows/ci.yml:L782** — [Tarihsel yapılandırma kaydı] name: yedekler-reason-${{ matrix.shard }}
- **.github/workflows/ci.yml:L788** — [Tarihsel yapılandırma kaydı] name: YEDEKLER 1562 reason coverage
- **.github/workflows/ci.yml:L790** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-reasons-1562-20261124]')
- **.github/workflows/ci.yml:L808** — [Tarihsel yapılandırma kaydı] name: yedekler-fresh-summary
- **.github/workflows/ci.yml:L817** — [Tarihsel yapılandırma kaydı] name: yedekler-reason-summary
- **.github/workflows/ci.yml:L824** — [Tarihsel yapılandırma kaydı] name: YEDEKLER 1562 official source directory research
- **.github/workflows/ci.yml:L825** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[yedekler-source-directory-20261124]')
- **.github/workflows/ci.yml:L843** — [Tarihsel yapılandırma kaydı] name: yedekler-reason-summary
- **.github/workflows/ci.yml:L849** — [Tarihsel yapılandırma kaydı] name: yedekler-source-directory
- **.github/workflows/ci.yml:L856** — [Tarihsel yapılandırma kaydı] if: github.event_name == 'push' && github.ref == 'refs/heads/main' && (contains(github.event.head_commit.message, '[nonforeign-av-20261125]') || contains(github.event.head_commit.message, '[yedekler-startup-20261126]'))
- **.github/workflows/ci.yml:L890** — [Tarihsel yapılandırma kaydı] name: yedekler-fresh-summary
- **.github/workflows/ci.yml:L905** — [Tarihsel yapılandırma kaydı] if: always() && github.event_name == 'push' && github.ref == 'refs/heads/main' && (contains(github.event.head_commit.message, '[nonforeign-av-20261125]') || contains(github.event.head_commit.message, '[yedekler-startup-20261126]'))
- **.github/workflows/full-turkish-backups-audit.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Verify protected IBO playlist without changing it
- **.github/workflows/full_autonomous_pipeline.yml:L27** — [Tarihsel yapılandırma kaydı] - name: Verify existing playlist and safely discover/validate
- **.github/workflows/ibo-authorized-500.yml:L1** — [Tarihsel yapılandırma kaydı] name: One-time authorized IBO complete old and V2 archives transfer
- **.github/workflows/ibo-real-scan.yml:L1** — [Tarihsel yapılandırma kaydı] name: V2 Real IBO Candidate Scan (production writer suspended)
- **.github/workflows/ibo-real-scan.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Verify protected IBO playlist without changing it
- **.github/workflows/ibo-single-playlist-transfer-offline.yml:L1** — [Tarihsel yapılandırma kaydı] name: IBO single-playlist archive transfer offline acceptance
- **.github/workflows/ibo-single-playlist-transfer-offline.yml:L28** — [Tarihsel yapılandırma kaydı] - name: Verify existing main playlist unchanged
- **.github/workflows/import-backup-candidates.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Verify protected IBO playlist without changing it
- **.github/workflows/issue-489-historical-audit.yml:L18** — [Tarihsel yapılandırma kaydı] - name: Compare historical and current inventories without changing playlists
- **.github/workflows/move-turkish-backups.yml:L1** — [Tarihsel yapılandırma kaydı] name: Move Turkish backup channels (production writer suspended)
- **.github/workflows/move-turkish-backups.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Verify protected IBO playlist without changing it
- **.github/workflows/repair-playlist-grouping.yml:L1** — [Tarihsel yapılandırma kaydı] name: Repair playlist grouping and counts (production writer suspended)
- **.github/workflows/repair-playlist-grouping.yml:L14** — [Tarihsel yapılandırma kaydı] - name: Verify protected IBO playlist without changing it
- **.github/workflows/run_move_685.yml:L23** — [Tarihsel yapılandırma kaydı] - name: Generate proposed playlist in temporary directory only
- **.github/workflows/run_move_685.yml:L33** — [Tarihsel yapılandırma kaydı] - name: Publish proposed playlist and move report
- **.github/workflows/run_move_685.yml:L36** — [Tarihsel yapılandırma kaydı] name: move-685-playlist-preview
- **.github/workflows/run_pass1_cleanup.yml:L18** — [Tarihsel yapılandırma kaydı] - name: Upload proposed playlist and report

<!-- C-END -->

## D) Açık Kalan GitHub Issue'ları ve Doğrulanmamış Maddeler

- **.github/workflows/issue-489-historical-audit.yml:L1** — [Tarihsel yapılandırma kaydı] name: Issue 489 historical inventory audit
- **.github/workflows/issue-489-historical-audit.yml:L22** — [Tarihsel yapılandırma kaydı] name: issue-489-inventory-audit

<!-- D-END -->

### Dosya tarama fihristi ve kapsam denetimi

Her satırda snapshot/PR referansı, kaynak, okuma sonucu ve çıkarılan kayıt sayısı bulunur. Bu fihrist, dosya okunmadığı halde tamamlandı denmesini önler.

- main `.github/workflows/alphabetize-yeni-turk.yml` — OK; 644/644 bayt, 3 yapılandırma/not satırı; blob `ff5b417cbe09d0dc4970b6a1ef90b9625dd6fd2d`.
- main `.github/workflows/autonomous_discovery_readonly.yml` — OK; 4887/4887 bayt, 13 yapılandırma/not satırı; blob `ccc784333ed118e3b0d50ea18df8497627647a00`.
- main `.github/workflows/backups-logo-audit.yml` — OK; 658/658 bayt, 3 yapılandırma/not satırı; blob `c1fbf8423b7fe72a7db3d69d86a03fdf5c2542ab`.
- main `.github/workflows/build_playlist_from_parts.yml` — OK; 6126/6126 bayt, 13 yapılandırma/not satırı; blob `6d34d0acbe7ce0abf5ee0cda53e4f77ccb6193cc`.
- main `.github/workflows/ci.yml` — OK; 37382/37382 bayt, 160 yapılandırma/not satırı; blob `a2e5badd24dea1320797df7696139033e68f5637`.
- main `.github/workflows/full-turkish-backups-audit.yml` — OK; 649/649 bayt, 3 yapılandırma/not satırı; blob `32dd86bd5ff5695aa7c3a408d1d61bf90d59d7e8`.
- main `.github/workflows/full_autonomous_pipeline.yml` — OK; 1233/1233 bayt, 10 yapılandırma/not satırı; blob `863399a9b322b10042707c57c2d51679ec70e775`.
- main `.github/workflows/ibo-authorized-500.yml` — OK; 2485/2485 bayt, 5 yapılandırma/not satırı; blob `d097c99cfe703d66cfec04ae61846f0d6825f1aa`.
- main `.github/workflows/ibo-real-scan.yml` — OK; 649/649 bayt, 3 yapılandırma/not satırı; blob `23fcc8ffd968e197f22b323a68b4cfb5e0728609`.
- main `.github/workflows/ibo-single-playlist-transfer-offline.yml` — OK; 1214/1214 bayt, 3 yapılandırma/not satırı; blob `903ba6c3feab4a4f169eb822952eb22d34a107ef`.
- main `.github/workflows/import-backup-candidates.yml` — OK; 647/647 bayt, 3 yapılandırma/not satırı; blob `7e22613257807f18724d28391ccdf1c660df083e`.
- main `.github/workflows/issue-489-historical-audit.yml` — OK; 728/728 bayt, 4 yapılandırma/not satırı; blob `74a7be5ed22e4fc86de0c55b2007881ab01ec661`.
- main `.github/workflows/move-turkish-backups.yml` — OK; 651/651 bayt, 3 yapılandırma/not satırı; blob `5511428247de8b362d8a4abae85f99053b9c401f`.
- main `.github/workflows/repair-playlist-grouping.yml` — OK; 658/658 bayt, 3 yapılandırma/not satırı; blob `248a10135fe7f46bc67a2a7e23cd629c33589969`.
- main `.github/workflows/run_move_685.yml` — OK; 2511/2511 bayt, 8 yapılandırma/not satırı; blob `1a063b634af06267595097915b875ac7c7161ac8`.
- main `.github/workflows/run_pass1_cleanup.yml` — OK; 836/836 bayt, 6 yapılandırma/not satırı; blob `157fe44762f30c8c7e0589f92ef52b227ba3eb6f`.
<!-- COVERAGE-END -->
