# #17–18 gerçek AV doğrulaması — tekrar yapmadan devam

Tarih: 2026-11-18. Kaynak: `v2/tasks/state.json` ve `v2/reports/task17-18-20-bounded-retry-20261118.json`.

## Korunan tamamlanmış kanıtlar

- GitHub Actions 43608247496: şifreli kontrol noktasından 28.545 eski gözlem kullanıldı; **300 yeni gerçek AV kontrolü** yapıldı; **33 başarısız yayın kurtarıldı**. Bu işlemler yeniden yapılmayacak.
- Önceki 8.540 + 33 = **8.573** AV kanıtı; **20.272** AV kanıtı olmayan kayıt. Bunlar tarihsel kanıtlardır, anlık yayın garantisi değildir.
- 2026-11-18 tarihli sınırlı inceleme: **15 farklı URL, 17 girişim**; **1** TRT Kurdî gerçek ses+görüntü örneği, **8** HTTP 404 inceleme, **6** HTTP 503 tekrar deneme. Bunlar da yeniden sayılmayacak.
- 14 Kasım kapalı kurtarma kuyruğu: 20.148 satır; iki mevcut playlist ile **3.781 farklı SHA-256 URL kimliği** eşleşti. Önceki eylemler: CHECK_AV 689, RETRY 1.339, REVIEW 1.753.

## Yeni taramanın zorunlu sırası

1. Önce 43608247496 koşusunun **şifreli kontrol noktası** ve kurtarma artifact'ini indir; hash ve kayıt kimliklerini doğrula. Kontrol noktası yoksa eski denemeleri yeniden yaparak tamamlandı sayma.
2. 18 Kasım sınırlı incelemesindeki 15 kimliği ve tüm geçmiş doğrulanmış AV kayıtlarını SHA-256 üzerinden ayıkla; **yalnızca kanıtı eksik kalan** URL'leri yeni iş kuyruğuna al.
3. HTTP 404 için yayıncı endpoint incelemesi yap; kanıt olmadan URL değiştirme. HTTP 503 için kontrollü, sınırlı ve geri çekilmeli retry uygula. Kimlik doğrulamalı, geo-blocked, karantina ve özel URL'leri tarama.
4. İşleri küçük, kaldığı yerden devam edebilen gruplara ayır. Yeni denemeleri gerçek FFmpeg decoded video **ve** audio kanıtlarıyla ölç; HTTP 200 veya manifest tek başına PASS değildir.
5. Her yeni denemeyi URL SHA-256, deneme zamanı, kaynak run/artifact, audio/video decode sonucu, hata ve retry sayısıyla checkpoint'e ekle. Eski kayıtları yeni ölçüm diye sayma.
6. Tarama bitince tekrarların sıfırlandığını, önceki 300/33 sonuçlarının korunduğunu, kalan kuyruk ile tüm sayımların dengelendiğini doğrula. Güvenlik kapısı ve gerçek İBO Player cihaz kabulü olmadan #17–18'i kapatma.

## Değiştirilmeyecekler

- `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` ana playlisti, YEDEKLER/ANA ARŞİV/TURK/YABANCI ayrımı ve 48 karantina kanalı.
- Kanal taşıma ve 2.500'lük İBO Player test döngüsü bu AV kurtarma işinden ayrıdır.

## Durum

**#17 ve #18 açık.** Bu not bir canlı tarama sonucu değildir; geçmiş kanıtları koruyan, tekrar denemeyi önleyen operasyonel devirdir. Gerçek binlerce kanal taraması, şifreli checkpoint erişimi ve çalıştırılabilir GitHub Actions ortamında yapılmalıdır.

Kanıt: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43608247496 ; https://github.com/Madsc55/MADSC55-TV-V2/blob/main/v2/reports/task17-18-20-bounded-retry-20261118.json
