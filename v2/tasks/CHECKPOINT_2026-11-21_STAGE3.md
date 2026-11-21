# MADSC55 TV V2 — 21 Kasım 2026 kaldığımız yer (Aşama 3)

Bu kayıt, tekrar çalışma yapılmaması ve bir sonraki sohbette aynı yerden başlanması içindir. **Test kabulü veya üretim değişikliği beyanı değildir.**

## Canlı GitHub okumasıyla doğrulananlar

- Ana playlist: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`; güncel main blob SHA `f3d39e4522d27912fccd6e67240a10fd16c4923b`. Büyük dosyada `fetch_file` boş içerik döndürdüğünden, **`fetch_blob` ile bu blob SHA okunmalıdır**.
- Güncel ana liste: **18.912** EXTINF kaydı. YEDEKLER **1.792**, ANA ARŞİV **15.574**, TÜRK ARŞİVİ **424**, YABANCI ARŞİVİ **284**, diğer kategoriler toplam **838**.
- Tarihsel kaynak commit `1e8bd6d46762366f151e1270cc767f598c8e63e8`; tarihsel playlist blob `688f0b194b9106d6fdc593e5d7dc4a64c7e01b2c`.
- Tarihsel kaynak YEDEKLER **1.792** ve güncel YEDEKLER **1.792**; **1.792/1.792 EXTINF+URL blokları, sıraları ve URL'leri birebir aynı**. Eksik tarihsel URL **0**. Bu sadece kimlik/sıra eşleşmesidir; güncel canlı AV doğrulaması değildir.
- Tarihsel Actions run [44640007709](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44640007709) başarılı; `yedekler-av-audit` artifact ID **14587983768**, ZIP digest `d6fefd9dabc036302dcadf0e52fa66542c51d9032d9abf8aeb3e3b88233a9f73`, rapor SHA256 `30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c`; sonuçlar **1.107 WORKING** ve **685 RECHECK_REQUIRED**. Artifact 20 Aralık 2026'da sona erecek şekilde listelenmiştir.
- #558 artık açık PR listesinde yok; `v2/ibo_497_existing_artifact.py` main'de bulunuyor. #560 ile rapor SHA kontrolü sıkılaştırıldı. Kodun main'de bulunması **uçtan uca importer çalıştırması kanıtı** değildir.
- Task34 gerçek FFmpeg çözümleme kodu main'de; Stage4 timestamp provenance kodu `5e78e6549a5254b3544618455bc9434f4d1b50e3` commitinde.

## Kesinlikle yapılmayanlar

- Bu denetimde playlist, URL, kanal sırası, kategori, arşiv veya 34 görev statüsü **değiştirilmedi**.
- **685** belirsiz kanal için yeni canlı test yapılmadı; İBO Player gerçek cihaz kabulü yapılmadı.
- Gerçek artifact ile güncel playlist üzerinde importer'ın uçtan uca `preview.m3u8` + `manifest.json` üretimi bu kayıtta **henüz kanıtlanmadı**.

## Bir sonraki tek iş

1. Güncel main SHA/blob'u ve kaynak rapor SHA'sını tekrar sabitle; özgün artifact ile `v2/ibo_497_existing_artifact.py` importer'ını **salt-okunur** çalıştır.
2. Üretilen manifestte `verified=1107`, `uncertain=685`, `failed=0`, `matched_historical_count=1792` (mevcut şemada varsa), `preview_only=true`, `canonical_playlist_written=false` ve preview baytlarının orijinal ana playlistle aynı olduğunu doğrula. Başarısızsa hiçbir taşıma/yayınlama yapma.
3. Ardından **yalnız 685 belirsiz** kayıt için gerçek AV yeniden kontrolünü ayrı, onaylı read-only iş akışında planla; tarihsel WORKING'i güncel canlı kabul diye sunma.
4. Sonra Türkçe ses/altyazı ASR/OCR/WebVTT ve gerçek şifreli harici arşiv geri-yükleme kabulünün kalan kanıtlarını ele al.

## Değişmez kurallar

Tek ana playlist; yeni test playlisti yok. 48 kaldırılmış hatalı kanal geri eklenmez; aynı URL mükerrer eklenmez; eski ilk 1003 kanal koruması tekrar uygulanmaz. Başlangıç 18.074 YEDEKLER envanteri ve 18.912 toplam kayıp/çift kayıt olmadan korunur; 112–486 ve seçili 59–181 TURK taşıma geçmişi korunur. Testleri kullanıcı İBO Player'da ayrıca yapar. Tamamlanmış PR/işler tekrar yapılmaz.

## 21 Kasım 2026 — devam denetimi / artifact yeniden doğrulama

- Orijinal artifact `14587983768` ZIP'i yeniden indirilen yerel dosyadan açıldı; **ZIP SHA256 `d6fefd9dabc036302dcadf0e52fa66542c51d9032d9abf8aeb3e3b88233a9f73` ve JSON SHA256 `30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c`** birebir eşleşti.
- JSON: `schema_version=1`, `total=1792`, `WORKING=1107`, `RECHECK_REQUIRED=685`, kaynak playlist SHA `eee260cce3926caff18238f9583958b40475e362ce7650fb7fac51a66a84ee1c`.
- Yeni gözlenen main commit `0137e18a2df527afd3124b6bd01d953cae21112a`: `feat(#497): add manual read-only YEDEKLER reconciliation`. **Bu commitin varlığı, gerçek artifact ile importer'ın uçtan uca çalıştırıldığını kanıtlamaz.**
- Önceki checkpoint PR [#570](https://github.com/Madsc55/MADSC55-TV-V2/pull/570) için kayıt dalı korunuyor. Bu ek güncelleme aynı dala yazıldı; main playlist ve görev statüleri değiştirilmedi.
- **Bir sonraki adım değişmedi:** orijinal JSON + kaynak playlist + güncel playlist ile read-only importer'ın gerçek preview/manifest üretimini kanıtlamak; sonra 685 belirsizi yeniden tarama kuyruğuna almak. Gerçek İBO cihaz kabulü hâlâ ayrı ve bekliyor.
