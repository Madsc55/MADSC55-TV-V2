# MADSC55 TV V2 — 10 maddelik ana sistem offline final kabulü — 27 Kasım 2026

Kapsam: proje sahibinin 27 Kasım talimatı, mevcut modüller, kayıtlı kanıtlar ve offline regresyonlar. Canlı kanal taraması, playlist yazımı veya yeni kanal/varlık ataması yok. Nihai 10/10 kabulü bu PR'ın Offline CI ve Production Security Gate SUCCESS sonuçları ve merge doğrulaması koşuluna bağlıdır.

| No | Madde | Kanıt / offline kabul |
|---:|---|---|
| 1 | Envanter | #793: iki kümenin 36470 URL birleşimi; 7650/7650, 1110/1110, 4955/4955 tarihsel mutabakat. Tüm tarihsel taramaların toplamı değildir. |
| 2 | ASR | #793: FLEURS yerel Türkçe/İngilizce örnek, model güveni 0.9579/0.9852, yalnız ipucu. |
| 3 | OCR | #793: 6/6 yerel örnek frame, Türkçe metin ipucu. |
| 4 | WebVTT | #793: iki zamanlı Türkçe cue, konuşmadan ayrı. |
| 5 | Kimlik | #793: yabancı ad/ülke, konuşma/altyazı ayrımı, fail-closed. |
| 6 | Kalite | #784/#785 ölçülen çözünürlük ve bitrate, bağımsız kimlik ve AV; #789 ayrı başlangıç/istikrar testi. |
| 7 | Logo/EPG | #785 kesin kimlik ve doğrulanmış varlık girdisi; #792 gerçek envanter aday raporu. |
| 8 | Kaynak erişimi | #784 GitLab/Codeberg 429 sınırları, Retry-After ve devre kesici regresyonları. |
| 9 | Karar hafızası | #786 sentetik AES-256-GCM restore; run 44429064188 gerçek 28844 kayıtlı checkpoint import; #787/#788 kullanıcı onayı ve ters işlem SHA kilidi. |
| 10 | Final kabul | Bu rapor, önceki kanıtlar ve iki yeni CI kapısı; merge sonrası yalnız belirlenmiş offline teslim kapsamı kapanır. |

## Önceki PR kanıtları

| PR | Offline CI run | Production Security Gate run | Merge |
|---|---:|---:|---|
| 784 | 45574375452 | 45574375379 | b4c5bda1563d7198c689c302774f8c78405b27ac |
| 785 | 45575191193 | 45575191143 | d0f7ec99082ca1ae90128251ef2763346c9e5999 |
| 786 | 45583956793 | 45583956760 | abab59a5aece98080bebcec3a2493300da6a2764 |
| 787 | 45700670542 | 45700670504 | 27838a8d11179e87dd2d17498a493d061022fd1c |
| 788 | 45709361771 | 45709361784 | 1a350aaf67690577475e4945714b5af1287eabfc |
| 789 | 45729120272 | 45729120267 | b666a0b6fdc39c7787b4782f03e008821a5b5dcb |
| 792 | 45871683327 | 45871683359 | a4e0dc1410c5c82336e097dd87cf834fa57792b6 |
| 793 | 45911528890 | 45911528852 | 2e853cc46b5e201dd9e7f7939dade4c686daad40 |

Tüm tabloda listelenen önceki iki CI sonucu GitHub API üzerinden completed/success, PR'lar merged=true doğrulandı. Run bağlantısı: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/<run-id>. İlk beş ayrıntısı: [önceki kapanış](ANA_SISTEM_1_5_OFFLINE_KAPANIS_20261127.md).

## 6–8 ayrıntıları

- v2/stream_quality_decision.py ve v2/package2_evidence.py doğrudan okundu: tam kanal ID + URL hash join, duplicate evidence reddi, bağımsız observed ID, decoded audio/video ve pozitif ölçülen height/width/bitrate koşulları. Sıralama height, width, bitrate; eşitlikte hash. Açılış süresi bu sıralamanın girdisi değil, #789 ayrı kalite/istikrar sınıflandırmasıdır. 180 sn başlangıç toleransı, 60 sn örnek, 3 tur, 120 sn ara, geç açılış eşiği 15 sn. Run 45799091422 completed/success, 32 paket artifact ve final artifact 15147217790 mevcut; yeni canlı ölçüm veya kalite kazananı atanmadı.
- #785 assets: exact observed ID, doğrulanmış EPG ve HTTPS kaynak, logo için official_origin_verified + content_verified + HTTPS resmî kaynak + SHA-256. #792 raporunda 697 logosuz, 1187 boş TVG-ID, 3 metadata logo adayı, 5 tarihsel tam EPG-ID eşleşmesi; resmî yeni logo/EPG ataması sıfır. Aday eşleşme resmî onay değildir. [Rapor](YEDEKLER_KURTARMA_OZETI.md).
- v2/discovery_provider_requests.py: 429 bounded Retry-After, reset ve backoff, 120 sn üst sınır; 403 devre kesici. 139068536714 job logunda test_http_429_honors_bounded_retry_after, test_http_429_honors_http_date_retry_after, test_http_429_uses_rate_limit_reset_header, test_http_429_without_header_uses_exponential_backoff, test_query_matrix_opens_circuit_after_provider_429, test_network_cli_stops_codeberg_fanout_after_429, test_provider_429_retries_then_skips_remaining_terms ok. Canlı GitLab/Codeberg erişiminin düzeldiği iddia edilmez.
- Mevcut v2/test_stream_quality_decision.py ve v2/test_package2_evidence.py kodları doğrudan incelendi; Makefile run hedefinde bu iki özel test açıkça yoktu. Final PR sadece mevcut testleri offline test hedefinde çağırır; üretim kodu/güvenlik workflow'u değişmez. Yeni final Offline CI sonucu bu testlerin yeni çalıştırma kanıtıdır.

## 9 ayrıntıları

- #786 job 139100675922 logu: PASS: independent ephemeral AES-256-GCM restore and SHA-256 parity. Ayrı geçici üretici/kurtarma dizinleri, üretici silindikten sonra byte/hash eşitliği, yanlış anahtar/bozuk tag reddi. Gerçek harici üretim kasası restore iddiası yok.
- Run 44429064188 job 135241423030 logu: existing_rows=28844; dry_run eligible_updates=15 applied=0; gerçek import applied=15; ikinci import eligible_updates=0 applied=0. state.json #17/#18/#20 kayıtları readback ve byte-identical backup kanıtını belgeliyor. Bu, tüm yeni kullanıcı kararlarının üretim kasasına aktarıldığı iddiası değildir.
- #787 commit'indeki v2/ibo_authorized_change.json base SHA 265f368758e75c5b18bc1b936a9792fef36528ba486288ddb35e4e7e23775ecf ve result SHA 414300c76946ace6e969efa69ec4c9155926fcf50541d350c6476ae7d6e78603; owner move manifesti. #788 geri alma manifesti aynı iki SHA'yı tersine çeviriyor. v2/reports/green-vitrine-revert-20261125.json: 562 geri taşınan, 1562 YEDEKLER, 18330 toplam, deleted=0. Güncel parts manifest SHA ilk değerle eşit. Onaylı tarihsel işlemin yeniden uygulanması yok.
- Kanonik playlist blob başlangıç: cb49c9f5a9224c4fd8fde0bbace64c8f20b0466f. Bu PR playlist ve onay manifestine dokunmaz.

## Teslim sınırı

Bu rapor 10 maddelik offline altyapı ve kayıtlı kanıt kabulüdür; gerçek yayın dili, tüm logo/EPG eksikleri, canlı sağlayıcı erişimi, cihaz oynatması veya bütün üretim akışının yeni canlı kabulü değildir. 34 eski görev ve 685 SECURITY HOLD korunur. İBO Player #693 ayrı aşamadır. Nihai ifade ancak bu PR iki CI PASS ve merge sonrasında geçerli: **10/10 TAMAMLANDI — ANA SİSTEM %100 TESLİM EDİLDİ (belirlenen offline kapsam).**
