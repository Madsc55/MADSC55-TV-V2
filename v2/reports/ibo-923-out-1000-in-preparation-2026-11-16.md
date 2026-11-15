# İBO ana listeye aktarım hazırlığı — 16 Kasım 2026

**Durum:** HAZIRLIK; ana oynatma listesine henüz uygulanmadı. Kullanıcı ayrı player listesi istemiyor.

- Ana dosya: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`
- Korunan 923 kanal: `v2/arsiv/yabanci_yedekler_2026-11-16_positions_84-1006_923.m3u8` (PR #286 ile main'e alındı)
- Korunan 3964 yabancı kanal: `v2/arsiv/yabanci_yedekler_2026-11-02_3964.m3u8`; kaynak blob SHA: `c54272e97f711c3074303cec74739d6d0ec806b2`
- Ana listede mevcut kayıt: 1925; YEDEKLER: 1087.
- Eski YEDEKLER 84–1006 arası 923 kanal arşivlenmiş, ancak ana listeden henüz çıkarılmamış.
- 3964 arşiv kaydının tamamı farklı yayın URL'sine sahip; ana listedeki URL'lerle tam eşleşme 0, aynı isim eşleşmesi 170.
- Öngörülen ilk paket: arşivdeki sıralı ilk 1000 URL; mevcut ana listedeki URL'lerden farklı. Bu adaylar İBO Player'da henüz görüntü/ses açısından test edilmedi.
- İstenen nihai YEDEKLER: 1087 − 923 + 1000 = 1164. Ana liste toplamı: 1925 − 923 + 1000 = 2002.

## Güvenli uygulama sınırı

Ana listeye değişiklik yapılırken yalnız YEDEKLER'in 84–1006 arası kayıtları çıkarılacak ve 1000 farklı URL YEDEKLER'e eklenecek. İlk 83 ve eski 1007–1087 kayıtları, diğer kategoriler, favoriler, URL'ler ve playlist başlığı korunacak. Korunan arşiv dosyaları değiştirilmeyecek. GitHub güvenlik kapısı için tam kaynak/sonuç SHA-256 manifesti ve PR testleri gereklidir. Akışların çalıştığı ancak gerçek cihazda denemeden ileri sürülemez.
