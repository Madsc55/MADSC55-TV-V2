# FFmpeg AV eksik doğrulama ayrımı — 2026-11-21

## Farklı veri kümelerini karıştırma
- 14 Kasım tarihsel tarama: 28.844 aday; 8.696 ses+görüntü doğrulandı; 20.148 AV doğrulanamadı. **20.148 kesin bozuk demek değildir.** Özgün raporun satır bazında hata nedenleri olmadan alt sınıf sayıları çıkarılamaz.
- Dünya taraması run 42216075104: 35.327 aday, 13.884 AV decode; farklı kapsam, üstteki sayılara eklenmez.
- PR #585 18.074 başlangıç arşivi hash mutabakatı: 1.904 aynı dünya koşusunda AV decode, 10.947 yalnız önceki koşudan hash, 4.080 eşleşen ama AV kanıtı olmayan, 1.143 eşleşmeyen. Toplam 18.074.
- Güncel YEDEKLER 1.792 (#497): 1.107 tarihsel WORKING, 685 RECHECK_REQUIRED, 0 kesin FAILED. 685'in 20'sinde eski dünya AV kanıtı var; daha yeni belirsiz kararı otomatik değişmez.

## Satır bazında uygulanacak durumlar
- `AV_DECODED`: FFmpeg hem ses hem görüntü decode kanıtı.
- `VIDEO_ONLY`: yalnız görüntü kanıtı.
- `AUDIO_ONLY`: yalnız ses kanıtı.
- `DECODE_ERROR`: medya çözümlenemedi, kalıcı arıza hükmü değil.
- `TIMEOUT_OR_RATE_LIMIT`: timeout, 403/429 veya geçici erişim; retry.
- `UNSAFE_OR_UNSUPPORTED_TRANSPORT`: nested HLS/DASH/anahtar güvenli toplanamıyor; doğrudan network FFmpeg yasak.
- `HASH_ONLY_HISTORICAL`: hash veya metadata eşleşmesi, yeni AV PASS değil.
- `NOT_IN_REPORT`: raporda hash eşleşmesi yok.
- `PENDING_RETRY`: son kanıt belirsiz.
- `FAILED_CONFIRMED`: iki deterministik negatif deneme ve kimlik/zaman kanıtı gerekli.

## Açık kabul kapıları
- 685 canlı retry yapılmadı. #594 plan ve #596 verdict kodu PASS, canlı test kanıtı değil.
- Güvenli nested HLS/DASH segment/anahtar toplama ve gerçek yayıncı kabulü eksik; 18.074 tam canlı tarama tamamlanmış değil.
- 20.148 alt durum adetleri yalnız özgün satır raporu incelenince çıkarılabilir; uydurulmaz.
- Ana playlist, arşiv ve kategorilere dokunulmadı; yeni playlist yok.
