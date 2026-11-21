# Ana playlist ve arşiv bütünlüğü (21 Kasım 2026)

Kanonik playlist: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` (blob SHA `f3d39e4522d27912fccd6e67240a10fd16c4923b`). Doğrudan dosya içeriği üzerinden sayım:

| Kategori | Kayıt |
|---|---:|
| YEDEKLER | 1792 |
| ANA ARŞİV | 15574 |
| TÜRK ARŞİVİ | 424 |
| YABANCI ARŞİVİ | 284 |
| Diğer 12 kategori | 838 |
| **Toplam** | **18912** |

- Arşiv toplamı **18074**, benzersiz tam yayın URL sayısı **18074**; arşiv içinde ve arşivler arasında URL çakışması **0**.
- 18912 EXTINF kaydının ardından HTTP/HTTPS URL var; biçimsel eksik adres **0**.
- İlk paket: 1792 + 424 + 284 = **2500**.
- Boş `tvg-id` sayısı **17881**; boş olmayan kimliklerden **76** tanesi birden fazla farklı yayın URL'siyle ilişkilidir. Aynı kanalın farklı kalite/ayna akışları olabileceği için otomatik hata kabul edilmez.
- Diğer 838 kategori kaydı, arşiv URL'lerini yeniden gösterir; ayrı arşiv kanalı sayılmamalıdır.

## Kabul
**PASS:** Kanonik dosya toplamı, kategori dağılımı, dört arşivde URL ayrıklığı ve ilk paket sayısı.

**AÇIK / DOĞRULANMADI:** 112–486 ve diğer geçmiş taşıma emirlerinin her kanalının önce/sonra sıralı URL/hash manifestleri üzerinden kimlik eşleşmesi. Güncel playlist ve boş tvg-id alanları tek başına tarihsel doğruluğu kanıtlamaz.

**KAPSAM DIŞI:** Canlı AV, Türkçe ses/altyazı, İBO cihaz testi.

Bu denetim ana playlisti değiştirmez; yeni playlist oluşturmaz; kanal silmez veya taşımaz. Tarihsel kimlik doğrulanmadan kategori taşımalarını tekrar uygulamayın.
