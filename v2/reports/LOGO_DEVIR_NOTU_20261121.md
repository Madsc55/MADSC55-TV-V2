# MADSC55 TV V2 — 21 Kasım 2026 logo çalışması devir notu

## Kullanıcının kesin isteği
Gerçek kanal logolarını eksiksiz tamamla. Tarihsel #391 aşamasında 307 logo eklenmiş, 558 eksik bildirilmişti. Kullanıcı tekrarlanan durum açıklaması istemiyor; yalnız gerçekten doğrulanmış orijinal logoların uygulanmasını, işi bitirmeyi istiyor.

## Doğrulanan güncel ana liste
Tek ana playlist: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`.
Kaynak SHA (denetim sırasında): `f3d39e4522d27912fccd6e67240a10fd16c4923b`.
GitHub `fetch_file` büyük dosyanın içeriğini boş döndürse de `fetch_blob` ile 3.675.691 karakterlik dosyanın tamamı okundu.
18.912 EXTINF kaydı: 4.745 kayıtta `tvg-logo` özniteliği yok veya boş. YEDEKLER 399; TÜRK ARŞİVİ 371; YABANCI ARŞİVİ 90; ANA ARŞİV 3.885. Bu sayı tüm playlist içindir; eski 558 ve #466'daki 489 sayısı eski/farklı kesitlere aittir. Başka kayıtta aynı görünen ada ait tekil logo bulunan 330 aday var; bunlar doğrulanmış değil.

## Gerçek GitHub değişiklikleri
- PR #609: https://github.com/Madsc55/MADSC55-TV-V2/pull/609 — taslak, `v2/reports/logo_inventory_20261121.md` güncel sayım ve ilk 100 aday. Playlist değişmedi.
- PR #618: https://github.com/Madsc55/MADSC55-TV-V2/pull/618 — taslak, tek ana playlistte 6 logo bağlantısı önerildi: Kanal D Drama 2, Bursa TV 1, Çekmeköy TV 1, TV41 2. Aynı `tvg-id` ve kanal adı olan başka mevcut playlist kayıtlarındaki URL'ler kullanıldı. URL'lerin güncel/orijinal görüntü olduğuna dair bağımsız kaynak ve canlı HTTP doğrulaması yapılmadı. **Doğrulamadan merge etme; tamamlandı deme.** Dal: `fix/logo-six-identity-matches-20261121`. Bu değişiklikler main'e henüz uygulanmadı.
- Eski PR #391: 307 tarihsel bağlantı; PR #466: 489 eksik ve 21 yalnız inceleme adayı; PR #467: TRT Çocuk eski logo reddi; PR #461/#464/#465 güvenli kimlik ve eşleşme kontrolleri.

## Kesin kurallar
Tek ana playlist, yeni playlist yok. 18.912 kanal sayısı, sıra, yayın URL'leri, kategoriler, YEDEKLER/ANA/TÜRK/YABANCI arşivleri, 48 eski dışlanmış URL korunacak. Tahmini/yanlış/eski logo yok; aynı isim tek başına yeterli değil. Resmî yayıncı/uygun kaynak, logo güncelliği ve URL görüntü doğrulaması yap. Değişiklikleri test et, yalnız kanıtlı olanları main'e birleştir. Bitmeyenleri doğrulanmamış olarak raporla.

## Sonraki sohbetin ilk eylemi
1. GitHub main SHA ve PR #609/#618 durumlarını kontrol et; güncel playlist blob SHA'yı yeniden al ve `fetch_blob` ile oku.
2. #618 altı URL'yi görsel olarak ve resmî kanal kimliğiyle doğrula; yanlış/eskiyse çıkar, doğrulanmışsa testlerle ilerle.
3. YEDEKLER 399 başta olmak üzere logosuzları güvenli eşleştirme ve gerçek yayıncı kaynaklarıyla partiler halinde tamamla; doğrulanmayanları boş bırak.
4. Ana playlist bütünlük farklarını otomatik kontrol et (yalnız logo alanları değişebilir), GitHub CI/security gate ve merge sonrası main'i doğrula.
5. Sonuçları DEVAM_NOTU.md ve v2/tasks/state.json'a yalnız kanıtlı durumlarla geçir. Önceki bitmiş işleri tekrar yazma.

**Durum:** Logo envanteri denetlendi, 6 logo için taslak PR açıldı; tüm gerçek logolar tamamlanmadı.
