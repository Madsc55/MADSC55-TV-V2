# #17/#18/#20 — güvenli şifreli kontrol noktası aktarımı (19 Kasım 2026)

## Doğrulanmış durum
- PR #442, var olan 15 HTTP/AV gözleminin çevrimdışı aktarım kodunu ekledi; bu, gerçek şifreli kontrol noktasına uygulanmış olduğu anlamına gelmez.
- PR #448, yeni bir `v2-secure-bounded-checkpoint-import.yml` iş akışı ekledi. Production Security Gate koşusu [44502831052](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44502831052) `MAIN_WORKFLOW_FILE_LOCK_FAIL` / `WORKFLOW_INVENTORY` ile başarısız oldu. PR #448 **birleştirilmeden kapatıldı**.
- Mevcut `v2/merge_bounded_retry_checkpoint.py` çevrimdışı bir araçtır; varsayılanı salt-okunur dry-run'dır. Gerçek anahtar ve kimliği doğrulanmış `ibo-scan-progress.enc` olmadan kabul yapılamaz.

## Güvenli yürütme sırası (yetkili, kontrollü ortamda)
1. Gerçek `ibo-scan-progress.enc` dosyasını onaylı ve erişim denetimli kaynaktan alın. Kaynağın beklenen artefaktı, özgün ZIP SHA-256 değerini ve içteki şifreli dosyanın SHA-256 değerini ayrı ayrı doğrulayın; başka kayıtla ikame etmeyin.
2. `V2_ARCHIVE_PASSPHRASE` değerini yalnızca güvenli çalışma ortamında secret olarak sağlayın; komut satırına, rapora, GitHub yorumuna veya loglara yazmayın. Şifreli dosyayı ve yedeğini hiçbir zaman repoya commit etmeyin.
3. `python3 v2/merge_bounded_retry_checkpoint.py --checkpoint /secure/path/ibo-scan-progress.enc --report v2/reports/task17-18-20-bounded-retry-20261118.json` komutuyla **önce dry-run** yapın. `existing_rows`, `eligible_updates`, hata ve eşleşme sonuçlarını kontrol edin.
4. Sadece dry-run ve kimlik doğrulama başarılıysa, kontrollü bir **çalışma kopyasında** aynı komutu `--apply` ile yürütün. Oluşan `.pre-bounded-retry.bak` dosyasını koruyun. Kodun şifreli yazma sonrası tekrar okuma kontrolü başarılı olmalıdır.
5. Aynı kopyada dry-run'ı yeniden çalıştırın: `eligible_updates == 0` olmalı (idempotence). Kayıt sayısı değişmemeli; güncel AV kanıtı eski HTTP denemeleriyle düşürülmemeli.
6. Güncellenen **yalnızca şifreli** kontrol noktasını bağımsız kalıcı arşive, erişim ve bütünlük doğrulamasıyla aktarın; ardından bağımsız geri yükleme/okuma kabulü yapın. 7 günlük geçici Actions artefaktı kalıcı kabul değildir.
7. Bu kanıtlar olmadan #17/#18/#20'yi tamamlandı işaretlemeyin. Production Security Gate başarıyla tamamlanmadan hiçbir değişikliği main'e birleştirmeyin.

## Yasaklar ve kapsam
- Yeni GitHub Actions iş akışı oluşturmayın veya güvenlik envanter kilidini dolanmayın.
- Yeni genel kanal taraması, otomatik yayıncı yazma işlemi, cron, playlist veya arşiv değişikliği yapmayın.
- Ana İBO playlisti `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` değişmeden kalır.
- 15 gözlem: 1 AV **örnek** kanıtı, 6 HTTP 503, 8 HTTP 404; gerçek cihaz/İBO kabulü değildir.
- Engel: onaylı yürütme ortamı, gerçek şifreli dosya ve secret, ardından kalıcı bağımsız restore kanıtı.

## Kabul kayıtları
Her uygulamada güvenli ortamda şu alanlar kayıt altına alınmalı: kaynak artefakt kimliği ve doğrulanan SHA-256, işlenen kayıt sayısı, güncellenen kayıt sayısı, ikinci dry-run'ın sıfır güncelleme sonucu, şifreli çıktı SHA-256, bağımsız restore doğrulaması, Production Security Gate koşu bağlantısı. Gizli anahtarlar ve açık yayın adresleri rapora yazılmamalıdır.
