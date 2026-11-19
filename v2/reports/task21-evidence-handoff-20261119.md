# Görev #21 — kaynak keşfi kanıt devri (19 Kasım 2026)

## Kapsam ve sınır
Bu belge mevcut kanıtların salt-okunur uzlaştırmasıdır; yeni kaynak taraması, AV testi, yayıncı kimliği onayı, üretim playlisti değişikliği veya görev kapanışı değildir. Kanonik görev durumu `v2/tasks/state.json` içinde **in_progress** kalır.

## Doğrulanmış tarihsel temel
- [14 Kasım gerçek tarama](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43608247496): 103/103 uygun M3U kaynağı; 28.845 aday URL; 8.573 toplam AV gözlemi (8.540 önceki kimliği doğrulanmış checkpoint, 33 o koşudaki yeni FFmpeg çözümlemesi); 20.272 AV kanıtı eksik.
- GitLab keşfi: 10/12 sorgu; kalan sorgular sağlayıcı hız sınırı nedeniyle eksik.
- Codeberg keşfi: 1/12 sorgu; kalan sorgular sağlayıcı hız sınırı nedeniyle eksik.
- YouTube: 353/353 `SIGN_IN_REQUIRED`, 0 doğrulanmış LIVE; doğrudan YouTube/resmî HLS çözümü 0/120. Bunlar doğrulanmış yayın olarak eklenemez.
- [18 Kasım DEVAM_NOTU](../../DEVAM_NOTU.md): GitHub tanılamasında 6 geçerli sorgu/103 ham aday satırı, GitLab'da 6 geçerli boş yanıt ve Codeberg'de ilk sorguda üç 429 sonrası beş atlanan sorgu. Türkiye/Azerbaycan örneklerinden 178/14 kayıt okundu. TRT Haber resmî yayınındaki tek HLS segmentinde FFmpeg görüntü ve ses çözümlemesi kaydedildi. Bu tekil kanıt küresel kabul değildir.

## Tamamlama kapıları (toplu işlem kontrol listesi)
1. Mevcut #21 ve #34 kaynak/adaptör kodunu, PR ve Actions kanıtlarını karşılaştır; zaten birleşmiş korumaları yeniden yazma.
2. GitHub/GitLab/Codeberg sorgularını hız sınırı, Retry-After, sağlayıcı devre kesicisi ve resume-plan tutarlılığı ile fail-closed tut; eksik sorguları tamamlanmış gibi sayma.
3. YouTube `SIGN_IN_REQUIRED` durumlarını atlatmaya çalışma veya yayın doğrulaması gibi gösterme. Yalnız izinli/resmî açık canlı HLS ve yayıncı sayfası kanıtını değerlendir.
4. Resmî yayıncı sahipliği, tam kaynak URL kimliği, güncel FFmpeg görüntü+ses kanıtı ve EPG kesin ID kanıtını ayrı alanlarda değerlendir. Ad eşleşmesi, HTTP başarı kodu veya ffprobe metadata tek başına kabul değildir.
5. Geçerli yeni kanıtlar için tekrarları kimlik/hash üzerinden ayıkla, başarısız/kanıtsızları karantinada tut, şifreli envanterin sırlarını veya yayın URL'lerini rapora yazma.
6. Offline regresyon, Production Security Gate ve gerekiyorsa izinli canlı Actions koşusu sonuçlarını kaydet; bütün kabul kapıları geçmeden `completed` işaretleme veya yayın listesi üretme.
7. İBO Player'ın ayrı 2.500'lük test/arşiv döngüsüne ve korunan ana İBO, YEDEKLER, YENİLER, FAVORİLER, EPG dosyalarına dokunma.

## Mevcut karar
**Açık / kanıt bekliyor.** Özellikle sağlayıcı keşfi, YouTube canlı metadata, doğrudan HLS ve bağımsız yayıncı doğrulaması tamamlanmadı. Bu belge canlı tarama başlatmaz ve 103/103 sayısını küresel kaynak tamamlanması olarak sunmaz.
