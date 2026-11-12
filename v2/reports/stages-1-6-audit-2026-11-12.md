# MADSC55 TV V2 — Aşamalar 1–6 kanıt denetimi (12 Kasım 2026)

Bu belge bir **denetim başlangıç kaydıdır**, kabul belgesi değildir. Ana İBO playlisti ve üretim verileri değiştirilmedi. Aşamaların hiçbiri yeni gerçek kanıt olmadan kapatılamaz.

## Kontrol edilen kaynaklar
- `DEVAM_NOTU.md`: mevcut, fakat 2 Kasım tarihli durumlar ve geçmiş kararlar iç içe.
- `v2/tasks/state.json`: main dalındaki GitHub Contents API isteği 404 döndü; dosyanın farklı dalda bulunmadığı anlamına gelmez.
- `v2/test_playlist_invariants.py`: 876 kanal, 38 YEDEKLER, 3964 arşiv kaydı ve ilk iki yedek için sabit koruma.
- `v2/real_ibo_scan.py`: AV_VERIFIED kontrolü mevcut; tek başına gerçek İBO cihaz kanıtı değildir.
- `v2/config/sources.json`: çoklu keşif kaynakları tanımlı.
- `.github/workflows/v2-playlist-safety.yml`: statik koruma testi tanımlı, bu denetimde yeni Actions sonucu alınmadı.

## Kabul matrisi
| Aşama | Görevler | Henüz gereken bağımsız kanıt |
| --- | --- | --- |
| 1 | #14, #16, #5, #6 | Özgün kaynak satırları, geçici hata koruması, tarihî URL kurtarma ve gerçek arşiv kabulü |
| 2 | #15, #17–#21 | URL/SHA eşleştirme, kuyruklar, TR/AZ kimlikleri, EPG, ölçülmüş çözünürlük ve kategoriler |
| 3 | #24 | Keşif → gerçek video/ses → şifreli harici arşiv → bağımsız geri yükleme toplu kabulü |
| 4 | #28–#30 | Gerçek AV kanıtlı 1000/2000 paket ve M3U bütünlüğü; eksikse sayı doldurulmayacak |
| 5 | #31–#33 | Toplu regresyon, gerçek İBO Player cihaz kabulü, son arşiv raporu |
| 6 | #34 | TR/AZ/dünya GitHub, Gist, GitLab, Codeberg, resmî siteler, YouTube canlı ve M3U tarama raporu |

## Açık engeller ve güvenlik
1. Gerçek S3/Drive geri yükleme kanıtı ve ilgili workflow sonuçları yeniden doğrulanmalı.
2. `state.json` için yetkili dal ve şema bulunmalı; körlemesine yeni durum dosyası oluşturulmamalı.
3. Mevcut 38 YEDEKLER / 3964 arşiv koruması kaldırılmamalı; onaylı paket tesliminde kontrollü test güncellemesi yapılmalı.
4. Sahte yayın, yalnızca HTTP 200, metadata veya sentetik test sonucu gerçek video/ses kanıtı sayılamaz.
5. Korunan main dalına ve ana İBO listesine yazma yok. Kabul için toplu Actions, gerçek cihaz ve arşiv kanıtları gerekir.

**Durum:** Denetim kaydı oluşturuldu; uygulama düzeltmeleri, yeni Actions çalıştırmaları ve aşama kapanışları henüz yapılmadı.
