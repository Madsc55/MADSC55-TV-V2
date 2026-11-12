# MADSC55 TV V2 — Aşama 6 kabul ve teslim kayıt defteri

Tarih: 2026-11-12. Durum: **AÇIK / TESLİM EDİLMEDİ**.

Bu belge gerçek kabul kanıtı yerine geçmez. Ana IBO listesi, YEDEKLER, favoriler ve EPG üzerinde değişiklik yapılmaz.

## #31 — Toplu kabul
- CI tanımı: `.github/workflows/v2-stage6-grouped-acceptance.yml`.
- PR: https://github.com/Madsc55/MADSC55-TV-V2/pull/14 (taslak).
- Kapsam: playlist değişmezleri, şifreli arşiv roundtrip, envanter geri yükleme regresyonu, çevrimdışı tarayıcı regresyonu.
- Doğrulanmış toplu çevrimdışı kabul: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43127461813 — success (önceki commit c8c3c779 için).
- Doğrulanmış üretim güvenlik kapısı: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43127894437 — success (commit 3cc6ff37).
- Bu iki farklı koşu birlikte tüm son kabulü kanıtlamaz. Son commit için Stage 6 toplu koşu ve gerçek canlı yayın/bağımsız bulut geri yükleme kanıtları eksiktir.
- Kabul: toplu koşu başarılı + önceki aşamaların bağımsız gerçek kanıtları doğrulanmış olmalı.

## #32 — Fiziksel IBO Player kabulü
- Gerçek cihazdan doğrudan erişim ve cihaz test kanıtı **yok**.
- Gerekli kayıtlar: cihaz modeli/uygulama sürümü, test tarihi, yüklenen playlist sürümü ve SHA-256, kanalların gerçek görüntü ve ses oynatımı, kategori/YEDEKLER/favori ve EPG ekranları, hatalar.
- Video ve ses gözlemi yapılmadan `PASS` yazılamaz. HTTP 200, FFprobe, sentetik fikstür veya ekran görüntüsü tek başına yeterli değildir.

## #33 — Son arşiv ve teslim
- Gerekli kayıtlar: şifreli arşiv nesnesi/konumu, SHA-256, erişim yetkileri, bağımsız geri yükleme koşusu ve sonucu, kanıt bağlantıları, envanter sayımları, nihai commit ve Actions URL'leri.
- Gerçek Google Drive/S3 geri yükleme kanıtı ve nihai cihaz kabulü **henüz bağlanmadı**.
- Teslim raporu **taslak**, nihai teslim **yapılmadı**.

## Karar
#31: AÇIK. #32: AÇIK. #33: AÇIK.
Gerçek kanıtlar tamamlanmadan bu görevler kapanmaz ve bu dosya başarı raporu olarak sunulmaz.
