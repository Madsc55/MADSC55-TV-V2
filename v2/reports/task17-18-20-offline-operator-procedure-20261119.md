# #17–18–20: mevcut kanıtların çevrimdışı işlenmesi (kanal araması YOK)

Bu işlem yeni kanal, kaynak veya yayın aramaz. İBO ana listesi ve arşivler değiştirilmez.

## Ön koşullar
- 14 Kasım gerçek taramasının **orijinal** `ibo-scan-progress.enc` dosyasını [43608247496](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43608247496) çalışmasının `v2-real-scan-evidence` artifact'inden güvenilir çalışma ortamına alın.
- `V2_ARCHIVE_PASSPHRASE` ortam değişkeni yalnızca güvenli ortamda bulunmalı; GitHub'a, terminal çıktısına veya PR'a yazılmamalı.
- `python -m pip install 'cryptography>=42,<47'` ile bağımlılığı kurun.
- Kaynağın ayrı bir kopyasını saklayın. Şifreli dosyayı Git'e commit etmeyin.

## Çalıştırma (yalnızca mevcut 15 kimlik, ağ taraması yok)

```bash
mkdir -p /tmp/v2-existing-evidence
cp /secure/source/ibo-scan-progress.enc /tmp/v2-existing-evidence/ibo-scan-progress.enc
chmod 600 /tmp/v2-existing-evidence/ibo-scan-progress.enc
python v2/merge_bounded_retry_checkpoint.py \
  --checkpoint /tmp/v2-existing-evidence/ibo-scan-progress.enc \
  --report v2/reports/task17-18-20-bounded-retry-20261118.json
```

Önce `dry_run: true`, `eligible_updates` ve `applied: 0` doğrulanır. Orijinal kanıtla tutarlılık sağlanırsa **ayrı, açık yetkiyle** aynı komuta `--apply` eklenir. Bu yalnızca şifreli kopyayı günceller; gerçek AV taraması yapmaz.

**Önemli:** 1 kısa ses/görüntü örneği, tam yayın kabulü değildir. 8 HTTP404 ve 6 HTTP503 sonuçları, canlı tekrar tarama yapılmadan sadece geçmiş kanıt olarak tutulur. Kalan #17–18–20 görevleri kapatılmaz.

## Kanal araması için gelecekteki kural

Kullanıcı açıkça başlatana kadar keşif yapılmaz. Daha sonra bulunan yeni kanallar kapsamlı ses, görüntü, dil, altyazı, logo, EPG, kaynak ve çalışma testlerinden geçtikten sonra uygun olanlar ANA ARŞİV'e alınır. Ana İBO playlistine otomatik ekleme yoktur. İBO Player 2.500'lük manuel test süreci ayrıdır.
