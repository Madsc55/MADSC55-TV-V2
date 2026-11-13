# #28–#33 — 13 Kasım 2026 gerçek İBO paket kanıtı denetimi

**Durum:** Gerçek Actions tarama/artifact kanıtı mevcut; fiziksel cihaz kabulü ve bağımsız üretim geri yükleme teslimi **açık**. Bu kayıt bir görev kapanışı değildir.

## Kaynak ve doğrulama

- GitHub Actions: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43412576224 — **SUCCESS** (13 Kasım 2026).
- Kanıt artifact'i: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43412576224/artifacts/14033805492
- Artifact ZIP SHA-256: `139c8a0868f35d4b64cd55a17bcbd56325d8e3c87b5d07295028bb4d56e832a6`
- İncelenen dosya: `v2-real-scan-evidence` ZIP. Parça sayımları arşivin **gerçek baytları** açılıp UTF-8 M3U girdilerinin yapısal eşleştirilmesiyle denetlendi; yeni internet kanal taraması çalıştırılmadı.

## Ölçülmüş sonuç

| Ölçüt | Sonuç |
|---|---:|
| Yeni farklı aday URL | 13.735 |
| Actions raporunda AV doğrulanan | 4.301 |
| Doğrulanmamış / başarısız | 9.434 |
| Şifreli envanter | `ibo-candidate-inventory.jsonl.enc` (ZIP içinde) |
| 1000'lik M3U parçaları | 1000 + 1000 + 1000 + 1000 + 301 |
| 2000'lik M3U parçaları | 2000 + 2000 + 301 |
| Her gruptaki toplam farklı URL | 4.301 |
| Gruplar arasında tam URL dizisi aynı | Evet |
| Yinelenen URL / eşleşmemiş EXTINF / biçimsiz yayın satırı | 0 / 0 / 0 |
| `mock_data_used` | `false` |
| `archive_restore_test_passed` | `true` (**Actions raporundaki test sonucu**, bağımsız bulut geri yükleme değildir) |
| `playback_verified_on_device` | `false` |
| Rapor durumu | `READY_FOR_DEVICE_TEST` |

### Doğrulama yöntemi ve kapsam sınırı

1. ZIP açılarak `IBO_AV_VERIFIED_1000_PART*.m3u8` ve `IBO_AV_VERIFIED_2000_PART*.m3u8` dosyaları ayrı ayrı incelendi.
2. Her dosyada `#EXTM3U` başlığı, her `#EXTINF` için bir HTTP(S) URL satırı, bitmemiş çift bulunmaması, URL tekrarı ve belirtilen parça büyüklüğü kontrol edildi.
3. Her iki grupta tüm 4.301 URL'nin aynı sırada bulunduğu ve rapor toplamıyla örtüştüğü doğrulandı. `4.301 + 9.434 = 13.735` aritmetiği tutarlı.
4. Arşivin şifresi kullanılmadı; bu denetim şifreli envanteri bağımsız çözmedi, FFmpeg akışlarını yeniden ölçmedi, video/sesin kimliğini veya İBO Player cihazını doğrulamadı.
5. Salt okunur denetim; ana İBO, YEDEKLER, YENİLER, FAVORİLER veya arşiv kayıtlarına yazma yok.

**Kabul sınırı:** Bu kanıt #28–#30 için gerçek paket oluşumu ve M3U biçim/bütünlük denetimine güçlü kanıttır; #31–#33 nihai kabulü için ayrı bağımsız gerçek ortam/cihaz/teslim kanıtları ve ilgili onay kapıları zorunludur. Görev statüleri otomatik değiştirilmedi.
