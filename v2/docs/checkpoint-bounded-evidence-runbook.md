# V2 #17/#18/#20 — mevcut kanıtın şifreli checkpoint'e aktarımı

**Durum:** PR #431 ile `v2/merge_bounded_retry_checkpoint.py` ve regresyon testleri main'e alındı. Bu dosya gerçek checkpoint aktarımının yapıldığı anlamına **gelmez**.

## Ön koşullar
- `ibo-scan-progress.enc`: gerçek, şifresi doğrulanabilen **worldwide** tarama checkpoint'i; dosya adı ve kapsamı tam eşleşmeli.
- `V2_ARCHIVE_PASSPHRASE`: güvenli çalışma ortamından sağlanmalı; GitHub'a, loga veya rapora yazılmamalı.
- `v2/reports/task17-18-20-bounded-retry-20261118.json`: main'deki önceki 15 adres/17 deneme kanıtı.
- Çalışma yalnızca yetkili izole ortamda yapılmalı. Checkpoint önce şifreli olarak yedeklenmeli; yedek ve SHA-256 kontrolü kaydedilmeli.

## Çevrimdışı uygulama

```bash
# Repo kökünden; parolayı komut satırında yazmayın.
python3 v2/merge_bounded_retry_checkpoint.py \
  --checkpoint /secure/path/ibo-scan-progress.enc \
  --report v2/reports/task17-18-20-bounded-retry-20261118.json

# İlk komut hata vermediyse, gerçek şifreli checkpoint ve yedeği hazırsa:
python3 v2/merge_bounded_retry_checkpoint.py \
  --checkpoint /secure/path/ibo-scan-progress.enc \
  --report v2/reports/task17-18-20-bounded-retry-20261118.json \
  --apply
```

`--apply` olmadan hiçbir checkpoint yazılmaz. Araç tam hash eşleşmesi ister, eksik/tekrarlı kimliği reddeder; eski gözlemler yeni kayıtların üzerine yazılmaz. Tek HLS segmentindeki AV kanıtı tam tarayıcı onayına yükseltilmez. Kaynak raporun 15 kimliğinden biri gerçek checkpoint'te yoksa işlem **durur**; sahte URL veya yeni kanal keşfi yapılmaz.

## Kabul ölçütü
1. Dry-run hatasız, 15 tarihsel kimlik mevcut, uygun güncelleme sayısı kaydedilmiş olmalı.
2. Uygulama sonrası şifreli dosya tekrar kimlik ve satır sayısı denetiminden geçmeli; önceki satırlar korunmalı.
3. Aynı rapor ikinci kez uygulandığında `eligible_updates=0` olmalı.
4. Önceki şifreli yedek üzerinden geri dönüş mümkün olmalı.
5. Gerçek cihaz oynatma, yayıncı kimliği ve açık görevler ayrıca doğrulanmalı. Bu aktarım #17/#18/#20'yi tek başına kapatmaz.

**Koruma:** Ana İBO, YEDEKLER, ANA/TURK/YABANCI arşivleri, EPG, 48 engelli kanal değiştirilmeyecek. 2.500'lük İBO Player test döngüsü ayrı iş akışıdır. Yeni kanal araması yapılmayacak.
