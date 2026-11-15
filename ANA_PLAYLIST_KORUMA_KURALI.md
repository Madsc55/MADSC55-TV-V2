# MADSC55 TV V2 — 1 NUMARALI DEĞİŞMEZ KURAL

Kullanıcının açık ve özel talimatı olmadan ana IBO playlistine **hiçbir değişiklik yapılamaz**.

Korunan dosya: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`

- Kanal ekleme, silme, değiştirme, yeniden adlandırma, taşıma **YASAK**.
- Kategori ekleme, silme, yeniden adlandırma, sıralama değiştirme **YASAK**.
- Favoriler, favori sıralaması, yedekler, yayın URL'leri, kanal kimlikleri ve logo URL'leri **KORUNUR**.
- EPG adresi dahil playlist başlığı ve tüm baytlar **KORUNUR**.
- Keşif, EPG ve logo otomasyonları yalnızca kendi çıktılarında çalışabilir; ana playlisti değiştiremez.
- Yeni bulunan kanallar yalnızca ayrı aday raporuna yazılabilir. Otomatik canlıya alma **YASAK**.
- Kullanıcının açık izni olmadan korunan dosyada GitHub API, Actions, bot, betik veya insan aracılığıyla yazma işlemi yapılmaz.
- Eski depoları silmek bu kuralı değiştirmez.

Bu dosya bir politika kaydıdır; GitHub dal koruması veya teknik yazma engeli yerine geçmez.

## Yeni kanal kabul kuralı

- Dünya çapında keşfedilen yeni kanalların **tek hedef kategorisi**: `📦 YEDEKLER`.
- Amaç: Kullanıcının IBO Player'da gerçekten çalışıp çalışmadıklarını denemesi.
- Kullanıcı açıkça ekleme talimatı vermedikçe **ana playlistin YEDEKLER kategorisine bile otomatik ekleme yapılmaz**. Önce ayrı aday/test listesinde sunulur.
- Kullanıcı açıkça eklenmesini istediğinde yalnızca onayladığı adaylar YEDEKLER'e eklenir; diğer kategorilere ve mevcut kayıtlara dokunulmaz.
- Test sonucu ve sonrasındaki taşıma/silme işlemleri de ayrıca kullanıcı onayı gerektirir.

## Kullanıcı talimatıyla düzenleme — 15 Kasım 2026

Bu koruma, kullanıcının **açık ve somut talimatıyla** yapılan değişiklikleri yasaklamaz. Kullanıcı kanal sıralaması, kategori sırası, kategori ekleme/silme, kanalın birden fazla kategoriye kopyalanması veya YEDEKLER'den onaylı çalışan kanalların ilgili kategorilere aktarılması talimatı verebilir. Talimat yalnızca adı geçen kanal/kategori ve istenen işlemi kapsar; genel otomatik yazma izni değildir.

Zorunlu işlem sırası: (1) kullanıcı talimatını ve kapsamını kaydet, (2) ana listenin değişiklik öncesi SHA-256 yedeğini al, (3) aynı isimli farklı akışları URL/tvg-id/logo ile ayırt et, (4) yalnız onaylanan değişikliği PR dalında yap, (5) kayıtların, diğer kategorilerin ve URL'lerin korunmasını otomatik test et, (6) GitHub koruma kontrolleri başarılı olursa PR üzerinden birleştir, (7) cihazda oynatma kabulünü ayrıca doğrula. Otomatik keşif bu yetkiyi kullanamaz.

**Teknik durum:** Mevcut güvenlik kapısı yalnız YEDEKLER içi yeniden sıralamaya izin veriyor. Kullanıcı onaylı kategori/kanal düzenlemeleri için dar kapsamlı, denetlenebilir PR onay mekanizması geliştirilip test edilene kadar bu metin tek başına teknik engeli kaldırmaz.
