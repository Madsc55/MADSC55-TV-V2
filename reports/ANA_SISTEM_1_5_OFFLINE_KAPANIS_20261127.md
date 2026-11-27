# MADSC55 TV V2 — 1–5. maddeler offline kapanış raporu (27 Kasım 2026)

Kullanıcı onaylı kapsam: mevcut artifact ve repo testleriyle envanter mutabakatı ve dil/kimlik zincirinin offline kabulü. Canlı yayın taraması, playlist yazımı, kanal taşıma/silme, güvenlik değişikliği, eski 34 görev statüsünün değiştirilmesi yok.

## 1 — Büyük kanal envanteri: TAMAMLANDI (belirlenen tarihsel kapsam)

İndirilen iki özgün Actions ZIP dosyası doğrudan açıldı, SHA-256 doğrulandı; JSON içindeki URL SHA-256 değerlerinden benzersiz kümeler hesaplandı.

| Kaynak | Run / artifact | Benzersiz URL |
|---|---|---:|
| Dünya taraması | 42216075104 / 13524765368 | 35327 |
| Tarihsel arşiv crosswalk | 44891650993 / 14702541294 | 18074 |
| Kesişim | Tam URL SHA-256 | 16931 |
| Yalnız dünya | Küme farkı | 18396 |
| Yalnız arşiv | Küme farkı | 1143 |
| Birleşim | 35327 + 18074 - 16931 | 36470 |

ZIP SHA-256:
- 13524765368: 6bec426291330c6b4b305e2871b721a25c44583f892c14d893472cdc3e80f87d
- 14702541294: 5cbb1de6cb9fcd7b923080259a78d36dc950f1de9b3c1dced0a680ff067a9f0b

JSON SHA-256:
- final-worldwide-acceptance.json: 41d96419250fc466786753b7d889503d0d4fc83fceb562d47eaf614a99624f0d
- crosswalk.json: 59c7487afc37d77bd38c1fb3b5398162ce606cf598904bd7fd862319ffebdf6c

Dünya raporundaki 13884 AV olumlu kaydın 2118'i CURRENT_RUN_FFPROBE_FFMPEG, 11766'sı PRIOR_RUN_HASH_ONLY_NOT_FRESH. Önceki kanıt güncel test değildir.
DEVAM_NOTU.md içindeki önceki URL mutabakatı 7650/7650 ve 1110/1110 eski listenin o tarihteki YEDEKLER envanterinde mevcut olduğunu belgeliyor; bu iki listenin ham dosyaları bu oturumda yeniden hesaplanmadı ve 36470'e ayrıca eklenmedi. state.json #15 ve v2/reports/task15-historical-url-hash-recovery-20261118.json kayıtları 4949+6=4955 tarihsel kimlik mutabakatını belgeler; bu ayrı tarihi baseline birleşime otomatik eklenmez.
36470 yalnız iki doğrudan karşılaştırılan URL kümesinin birleşimidir, tüm geçmiş taramalar veya güncel çalışan TV kanalları sayısı değildir.

Kaynaklar: [dünya run](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42216075104), [crosswalk run](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44891650993), [PR #585](https://github.com/Madsc55/MADSC55-TV-V2/pull/585), [durum defteri](../v2/tasks/state.json), [devam notu](../DEVAM_NOTU.md).

## 2–5 — Dil ve kimlik zinciri: OFFLINE TAMAMLANDI

[v2/reports/turkish-sample-verification-20261119.json](../v2/reports/turkish-sample-verification-20261119.json) doğrudan okundu. İki yerel entegrasyon örneği: FLEURS gerçek insan konuşması, üretilmiş yazılı görüntü ve zamanlı Türkçe test altyazısı. Yayıncı veya cihaz örneği değildir.

| Madde | Mevcut kanıt | Offline durum |
|---|---|---|
| 2 ASR | tr 0.9579; en 0.9852; model hint only | TAMAMLANDI |
| 3 OCR | 2 örnekte 3+3 frame tamamlandı, Türkçe metin ipucu | TAMAMLANDI |
| 4 WebVTT | Her örnekte 1 zamanlı Türkçe cue; konuşmadan ayrı | TAMAMLANDI |
| 5 İsimden bağımsız kimlik inceleme | TURKISH_SPOKEN_REVIEW / TURKISH_SUBTITLED_REVIEW ayrımı; yabancı ad/ülke testleri | TAMAMLANDI |

Her iki örnekte audio_decoded ve video_decoded true; review_approved, language_evidence_verified, working_channel_verified, device_verified ve playlist_modified false. Model güveni doğrulanmış yayın dili veya yayıncı kimliği değildir. Yeni model inference yapılmadı; saklanmış örnek raporu ve mevcut CI logları incelendi.

26 Kasım Production Security Gate run 45871683359, job 140088410115 SUCCESS logunda doğrudan görülen testler:
- test_turkish_speech_without_turkish_name_abroad, test_foreign_channel_turkish_subtitle — ok (triage)
- test_asr_turkish_is_review_only, test_ocr_turkish_is_not_spoken_or_subtitle — ok
- test_turkish_header_only_creates_review — ok (WebVTT)
- test_real_decode_ocr_and_timed_track, test_foreign_speech_with_timed_turkish_cues, test_timing_metadata_and_text_are_separate, test_silence_and_invalid_language_probability, test_capture_receipt_and_archive_identity — ok (local integrated sample)
- test_ocr_turkish_letters_hint_only — ok.

Mevcut test kodları ve CI tanımı incelendi: v2/test_turkish_channel_triage.py (8 test), v2/test_turkish_asr_ocr_evidence.py (12 test), v2/test_turkish_webvtt_evidence.py (7 test), v2/test_turkish_sample_review.py. Bunlar mevcut offline kapsamı karşılıyor; yeni üretim kodu veya mükerrer test eklenmedi.
[CI job](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/45871683359/job/140088410115).

## Kapanış ve korumalar

1–5 maddeler sadece kullanıcı tarafından belirlenen offline kapsam için tamamlandı. Bu raporun main kabulü yeni PR'ın Offline CI ve Production Security Gate SUCCESS sonuçlarına ve merge doğrulamasına bağlıdır. Gerçek yayınların toplu ASR/OCR/WebVTT tespiti ve gerçek yayıncı kimliği kabulü bu raporla yapılmış sayılmaz. 685 SECURITY HOLD korunur; 34 eski görev yeniden açılmaz; yeni playlist veya canlı tarama yoktur. Sıradaki iş 6 — mevcut kalite karar motorunun gerçek kayıtlı ölçümlerle offline doğrulanması.
