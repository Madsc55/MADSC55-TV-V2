# MADSC55 TV V2 — Ana çalışma sırası
**Kayıt:** 21 Kasım 2026  
**Baz main:** `3eb84f890cbe8524d16c1a16f219b0b494cc50f0`  
**Amaç:** Kanıtlı eksikleri tek tek kapatmak; tamamlanan işleri tekrarlamamak.

## Güncel çalışma sırası — 21 Kasım 2026, #561/#567 sonrası

Önceki bölümlerdeki “#551/#547/#543 açık”, “özgün #497 raporu yok” ve “#561 merge bekliyor” ifadeleri **tarihsel kayıt**tır; bugün geçerli değildir. Sonuçlar aşağıdaki sıraya taşındı:

**Kritik öncelik: #581.** #567 canlı retry workflow'u ham URL'yi FFprobe/FFmpeg'e verir; DNS/IP pinleme, alt HLS istekleri ve redirect/egress koruması doğrulanana kadar **manuel retry çalıştırılmayacak**. [PR #581](https://github.com/Madsc55/MADSC55-TV-V2/pull/581) güvenlik askısı ve kaldırılamama regresyonu içindir; CI/merge kontrolü yapılmadan tamamlandı sayılmaz. Salt-okunur #561 tarihî manifest önizlemesi bu ağ taraması değildir.

1. **Kabul edildi (tekrarlama):** #551 arşiv kabulü, #547 gerçek 1.792 rapor içeriği ve 1.107/685 önizlemesi, #543 iki medya akışını gerçekten decode eden FFmpeg kodu, #561 tek tetik manuel salt-okunur rapor işleme (main [44843901219](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44843901219) SUCCESS), #567 **yalnız 685 belirsiz** aday için manuel retry altyapısı (main [44843984931](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44843984931) SUCCESS), #571 URL/FFmpeg protokol sınırlandırması (PR [44843819098](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44843819098) SUCCESS). Bunlar altyapı/test kabulüdür, canlı 685 tekrar koşusu değildir.
2. **Sıradaki ilk teknik eksik:** [PR #572](https://github.com/Madsc55/MADSC55-TV-V2/pull/572) güvenli DNS/IP pinli sınırlı medya örneklemesini kontrol et. IPv4/IPv6 tüm DNS yanıtları public olmalı; redirect ve dış/alt playlist/segment istekleri kapalı; SNI ve sertifika denetimi doğru olmalı; FFmpeg yalnız yerel baytları çözmeli. Başarı için güncel CI ve negatif saldırı regresyonu şart. HLS/DASH çoklu segmenti kapsam dışı kalır.
3. **Sonraki eksikler:** gerçek akış kaynağından zaman/hash/yöntem izli ASR/OCR/WebVTT, 685 belirsizin yeni kanıtla idempotent ledger/retry sonucu (manuel tarama öncesi onay), #6 gerçek harici özel kasa backup/restore kabulü, geniş 18.074 yayın kanıtı, en son 2.500'lük İBO Player cihaz testi.
4. **Değişmez güvenlik:** tek ana playlist, toplam 18.912 kayıt, başlangıç 18.074 arşiv kaydı; güncel kategori dağılımı YEDEKLER 1.792 / ANA 15.574 / TÜRK 424 / YABANCI 284 / diğer 838. 48 karantina kaydı geri gelmez, 1003 kuralı uygulanmaz, ana kategoriler/URL/EPG otomatik değişmez.


## Değişmez koruma kuralları
- Tek ana IBO playlisti: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`; yeni test playlisti yok.
- 48 karantinaya alınmış kanal geri eklenmez; aynı URL mükerrer eklenmez.
- İlk 1.003 kanal koruması yeniden uygulanmaz.
- Kullanıcı onayı olmadan ana playlist, ana kategoriler, EPG veya arşiv içerikleri değiştirilmez.
- 18.912 kayıtlı envanter ve 18.074 başlangıç YEDEKLER sayısı tarihî referanstır; farklı snapshot sayıları birbirine karıştırılmaz.
- 112–486 Türk taşıma talimatı ve 59–181 seçilmiş düzeltmeler tekrar uygulanmaz.
- Kanal adı/ülkesi tek başına Türkçe yayın veya çalışan yayın kanıtı değildir.
- İBO Player 2.500'lük kullanıcı testi, sistemin arka plan taramasından ayrı tutulur.
- Her iş: kanıtı bul → kimlik/hash/kapsamı doğrula → yalnız gerçek açığı düzelt → hedefli test → güncel CI → rapor. Başarısız veya belirsiz kanıt tamamlandı sayılmaz.

## Başlangıçta doğrulanan durum
- Main HEAD: `3eb84f890cbe8524d16c1a16f219b0b494cc50f0`.
- Production Security Gate #44837457969: SUCCESS.
- Playlist Safety Invariants #44836309550: SUCCESS (önceki main).
- `v2/tasks/state.json` son üretilme zamanı 13 Kasım; 22 completed / 12 in_progress tarihî dosya beyanıdır, güncel durum değildir. Güncel kanıt olmadan statüler değiştirilmez.
- 101 offline PASS ve yerel FFmpeg/OCR testleri gerçek 18.074 kanalın test edildiğini göstermez.
- Dünya taraması #42216075104: 35.327 aday, 13.884 FFmpeg AV decode. Bu, 18.074 YEDEKLER'in tamamlanma kanıtı değildir.
- #551'deki snapshot: YEDEKLER 1.792, ANA ARŞİV 15.574, TÜRK 424, YABANCI 284, diğer korunan kategoriler 838; toplam 18.912. Bu sayım 18.074 başlangıç YEDEKLER sayısından ayrı snapshot'tır. #551 açık PR; kanıt mutabakatı tamamlanmadan nihai kabul değildir.
- İncelenecek açık PR'lar: #551, #552, #547, #543, #535, #514, #507. Açık PR olmak tek başına kabul/merge gerekçesi değildir.

## Sıralı çalışma aşamaları

### 0 — Devir kaydını sabitle
Bu plan ve DEVAM_NOTU kayda alınır. Başlangıç main/Actions/PR referansları sabitlenir. Playlist ve görev statüleri değişmez.

### 1 — #489 arşiv envanteri ve taşıma kabulü (PR #551)
- #551 diff'ini, 12 arşiv regresyonunu ve 18.912 / 18.074 başlangıç / 838 korunan kategori / taşıma-geri alma kanıtını incele.
- 1.792 YEDEKLER snapshot'ının kaynak commit/dosya/raporunu sabitle; başlangıç 18.074 ile farkın muhasebesini yap.
- 112–486 ve 59–181 talimatlarıyla çakışma, mükerrer URL ve kayıp kimlik olmadığını salt-okunur hash/kimlik mutabakatıyla doğrula.
- Kabul: kaynak-hedef sayım mutabakatı, korunan 838 kategorinin değişmediği, rollback testleri ve güncel main CI PASS. Playlist yazımı yok. Kanıt yetersizse PR açık kalır.

### 2 — #497 eski AV raporu ve kimlik manifesti (PR #552 → #547)
- Orijinal Actions artifact'ını ve değişmez kanal-ID/URL-hash manifestini bul.
- Bulunamazsa açık blocker kaydet; 1.107 çalışan + 685 belirsiz sayısını doğrulanmış veri gibi kullanma.
- Bulunursa kaynak run, playlist hash, kayıt sayısı, sıra, EXTINF ve URL hash birebir eşleştir.
- #547 yalnız doğrulanmış raporu kullanmalı; fail-closed, preview/manifest only, playlist değişikliği yok.
- #535/#514 ile örtüşmeyi ayır. Kabul: orijinal kanıt zinciri, hash eşleşmesi, hedefli test ve güncel CI PASS.

### 3 — Task 34 gerçek FFmpeg AV decode (PR #543)
- FFprobe metadata sonucunun gerçek FFmpeg video ve audio decode ile değiştirildiğini incele.
- Eksik video/audio veya decode hatası DECODE_UNVERIFIED kalmalı; timeout, boyut ve ağ güvenlik sınırları korunmalı.
- PR CI ve main güvenlik kapısı PASS olmadan merge yok.
- Kabul: kontrollü izinli örneklerde iki akış decode kanıtı, negatif testler, timeout ve CI PASS. Bu, 18.074 taraması değildir.

### 4 — Türkçe dil / altyazı / OCR kanıt zinciri
- Mevcut ASR/OCR/WebVTT altyapısını yeniden yazma; gerçek yayın örneğinden kanıt üreten eksikleri tamamla.
- Konuşma dili, ekran yazısı, altyazı, yayıncı/ülke kimliği ve AV durumu ayrı tutulmalı.
- Yurt dışındaki Türkçe yayınlar ve adında Türkçe ibare olmayan Türk kanalları kaybolmamalı.
- Kabul: kaynak, zaman damgası, örnek hash'i, yöntem ve güven düzeyi. Kanıt yetersizse inceleme bekliyor; otomatik Türk/Yabancı onayı yok.

### 5 — 18.074 YEDEKLER gerçek medya doğrulaması
- Önce mevcut dünya ve tarihî raporları tam URL hash/kimlik ile eşleştir; eski AV kanıtını yeni test gibi sayma.
- Her kayıt için tekil kimlik, son test zamanı, AV, ASR/OCR/WebVTT, kaynak ve retry geçmişi tut.
- Geniş taramayı yalnız #497/#543/dil kanıt kapıları hazır, güvenli ve CI kabulü tamamlandıktan sonra bounded paketlerle başlat.
- Geçici timeout/403/429 doğrudan kalıcı çalışmıyor sayılmaz; retry/backoff ve mükerrer önleme uygulanır.
- Kabul: 18.074 kimliğin her biri için sonuç veya açık blocker, sayım mutabakatı ve gerçek AV kanıtı. Ana playlist değişikliği yok.

### 6 — Otomatik sonuç işleme, retry ve arşiv önizlemesi
- Kalıcı ledger/checkpoint ve idempotent sonuç işleme eksiklerini tamamla.
- Çalışan, çalışmayan ve belirsiz ayrı tutulur; belirsizler kontrollü tekrar denenir.
- Her işlem öncesi/sonrası sayım, kimlik/hash ve rollback kanıtı üret.
- İBO 2.500'lük kullanıcı testi ile sistem taraması ayrı kalır.
- Kabul: yeniden başlatma/çökme sonrası devam, retry, idempotency, rollback ve preview testleri PASS. Kullanıcı onayı olmadan playlist yazımı yok.

### 7 — Şifreli arşiv gerçek ortam kabulü (PR #507; #502/#508/#509/#510/#548 altyapısı)
- Birleşmiş kodu yeniden yazma. Kalıcı özel depolama, anahtar yönetimi, yetki sınırı, harici şifreli yedek ve bağımsız restore'u gerçek ortamda doğrula.
- Kabul: yetkili ortamda gerçek backup/restore, hash/versiyon/izin kanıtı ve sırların loglanmaması. Kimlik bilgisi yoksa blocker.

### 8 — İBO Player kullanıcı kabulü ve kapanış
- Offline CI, gerçek AV, Türkçe sınıflandırma ve cihaz oynatması ayrı kabul kapılarıdır.
- Kullanıcının 2.500'lük deneme akışı yalnız kendi test alanında ve açık talimatla yürütülür.
- Final rapor: envanter, çalışan/çalışmayan/belirsiz, Türk/Yabancı kanıtı, korunan kategoriler ve rollback.
- Her görev için commit, PR, Actions run, artifact ve test sonucu sunulur; açık blocker saklanmaz.

## Tekrarlanmayacak tamamlanmış işler
- Birleşmiş #502, #508, #509, #510, #539, #546, #548 ve #549 tekrar yapılmaz; yalnız regresyon kanıtı varsa hedefli düzeltme.
- 101 offline PASS ve mevcut main Security Gate yeniden çalıştırma amacıyla tekrarlanmaz; yeni kodun zorunlu CI'si doğal olarak çalışır.
- #42216075104 dünya taraması mevcut tarihî kanıttır; aynı kapsam körlemesine yeniden taranmaz.
- 112–486 ve 59–181 taşıma talimatları tekrar uygulanmaz.
- 48 engelli kanal geri eklenmez; 1003 kuralı uygulanmaz.

## Her aşamanın rapor şablonu
Durum (bekliyor/çalışıyor/tamamlandı/bloke); değişen dosyalar; önce/sonra SHA; commit/PR; Actions run/job sonuçları; artifact ID/hash; kayıt sayıları; blocker; playlist/kategori değişikliği (evet/hayır); sonraki tek adım.


## İlerleme günlüğü — 21 Kasım 2026
### Aşama 1 / #489 arşiv kabulü — kanıt kontrolü yapıldı
- PR #551 kaynak diff'inde `DEVAM_NOTU.md` ve `v2/tasks/state.json` kanıt kaydı incelendi.
- PR #551 Production Security Gate run `44838963882`: **SUCCESS**; job `Verify suspended publishers, no cron and immutable IBO`: SUCCESS; live-discovery-diagnostic SKIPPED (beklenen, tarama yok).
- PR #551 kaydında arşiv regresyonları **12 test PASS** ve log kabul satırı `PASS: #489 canonical 18912; 18074 archive; 838 protected; move/restore` olarak belirtiliyor.
- Önemli sınır: bu test/CI kabulüdür. PR notu gerçek kullanıcı playlistine yazma yapılmadığını açıkça söylüyor. Bu nedenle canlı dosyada fiziksel taşıma yapıldı denmiyor.
- Eski fixture run `44828290696` içindeki 1.792 YEDEKLER / 15.574 ANA / 424 TURK / 284 YABANCI / 838 OTHER dağılımı, 18.074 başlangıç arşiv envanteriyle aynı snapshot değildir. Ayrı tutulacak.
- **Aşama 1 durumu: test ve kanıt incelemesi başarılı; PR #551 hâlâ açık olduğu için PR kabul/merge kapanışı bekliyor.** Playlist değişikliği yok.
### Aşama 2 / #497 kaynak artifact — blocker teyit edildi
- PR #552 dosya farkı ve notu incelendi: #497'nin orijinal Actions artifact'ı ile immutable channel-ID + URL SHA-256 manifesti bulunamamış.
- Aday #497 adapter CI run'ları `44799031940`, `44798131945`, `44837957693` ve ilgili denemelerde Actions artifact listesi boş döndü. Bunlar kod CI PASS kanıtıdır, özgün 1.792 kanal AV raporu değildir.
- `task17-18-20-bounded-retry-20261118.json` farklı kapsamlı 15 URL/17 deneme raporudur; ikame edilmeyecek.
- 1.107 çalışan + 685 belirsiz sayıları özgün artifact'tan doğrulanamadı. Hiçbir kayıt işlenmedi/taşınmadı; yeni tarama başlatılmadı.
- **Aşama 2 durumu: BLOKE — doğru tarihî Actions run/artifact ve hash manifesti bulunmalı.** Sonraki adım yalnız bu özgün kaynağı araştırmak; bulunamazsa blocker açık kalır.


### Aşama 2 / #497 özgün AV raporu — artifact bulundu ve kimlik eşlemesi doğrulandı
- Gerçek kaynak workflow: [#44640007709](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44640007709), workflow_dispatch, main commit `1e8bd6d46762366f151e1270cc767f598c8e63e8`; job `yedekler-av-audit` SUCCESS.
- Orijinal artifact: `yedekler-av-audit`, artifact ID `14587983768`; rapor dosyası `yedekler_av_audit.json`. Upload logundaki ZIP SHA-256: `d6fefd9dabc036302dcadf0e52fa66542c51d9032d9abf8aeb3e3b88233a9f73`; indirilen ZIP bu hash ile aynı. Rapor ham dosya SHA-256: `30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c`.
- Rapor schema 1, tarih `2026-11-20T00:20:09.490490+00:00`, kategori YEDEKLER, total 1.792; WORKING 1.107 / RECHECK_REQUIRED 685. 1.792/1.792 URL SHA-256 benzersiz, pozisyonlar 1–1.792 kesintisiz. 1.107 kaydın video=true, audio=true ve decoded_av_verified=true; 685 kayıt yeniden kontrol sınıfında. Politika: read-only; başarısızlar yeniden kontrol edilir; otomatik silme/işaretleme/sıralama yok.
- Orijinal raporun playlist SHA-256 değeri `eee260cce3926caff18238f9583958b40475e362ce7650fb7fac51a66a84ee1c`; kaynak commit'teki ana M3U dosyasıyla eşleşiyor. Denetim scripti `v2/audit_yedekler_av.py` ham playlist bayt SHA'sını ve her URL için SHA-256 üretip pozisyon/name ile raporluyor.
- Güncel main tam playlisti farklı SHA'ya sahip (`71b95cbc6e4f8b6bab4c294ffe423043870b0aa9b08d560327b4b512a3fc0a77)); ancak kaynak commit ile güncel main arasında 1.792 YEDEKLER EXTINF+URL bloklarının tamamı **sırası korunarak byte-byte aynı**. Her iki snapshot'ta da 1.792 kayıt ve benzersiz URL var; eşleşmeyen, tekrarlanan, adı veya EXTINF metadatası değişen YEDEKLER kaydı yok. Fark, YEDEKLER dışındaki playlist içeriğinde.
- Bu nedenle tam playlist SHA farklılığını görmezden gelerek doğrudan import yapılmayacak. PR #547 güncelleniyor: önce tarihî source commit + orijinal artifact sabit run/artifact/file SHA ile doğrulanacak; sonra 1.792 YEDEKLER bloğunun güncel main'de aynı sırayla byte-byte eşitliği aranacak; yalnız eşleşirse güncel playlist SHA'sına yeniden bağlanan preview/manifest üretilecek.
- PR #547'ye eklenen importer ve offline testler: sabit kaynak run `44640007709`, artifact `14587983768`, report hash, tarihî playlist hash; ordered block equality; değişmiş kayıt/sıra için fail-closed. Yalnız preview ve retry manifesti; yeni scan ve playlist yazımı yok. PR #547 hâlâ draft; yeni CI/preview kanıtı bekleniyor.
- **Aşama 2 durumu: özgün kaynak bulundu ve tarihî/current YEDEKLER kimliği eşleştirildi; güvenli importer kodu PR #547'de güncellendi. Nihai kabul için yeni testlerin PASS olması ve gerçek Actions artifact'tan preview+manifest üretiminin doğrulanması bekleniyor.** 685 kayıt henüz yeniden taranmadı/taşınmadı; kullanıcı playlistine yazılmadı.


## 21 Kasım 2026 — Ara kabul: eski AV kanıtı, FFmpeg ve mükerrer PR temizliği

- **Aşama 1 arşiv:** #551 birleşti. Arşiv regresyonları ve kanıt SUCCESS; bu, kullanıcının gerçek playlistinde bu inceleme tarafından yeni taşıma yapıldığı anlamına gelmez.
- **Aşama 2 özgün AV kanıtı:** [read-only run #44640007709](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44640007709) artifact **14587983768** ve tam `yedekler_av_audit.json` indirildi, ZIP ve dosya SHA-256 eşleşmeleri doğrulandı. Schema 1, 1.792 benzersiz URL kimliği ve 1–1.792 kesintisiz pozisyon; 1.107 video+audio decoded, 685 RECHECK_REQUIRED.
- **685 belirsizin ayrıntısı:** PROBE_FAILED 621; TIMEOUT 26; NO_MEDIA 23; AV_STREAMS_PRESENT (decode doğrulanmamış) 14; AUDIO_ONLY 1. **Hiçbiri kesin ölü ilan edilmedi.**
- #547 importer ve offline regresyonları main'e birleşti; main CI run [44842749390](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44842749390) SUCCESS. Ancak mevcut kayıtta özgün artifact'tan **gerçek preview+manifest üretiminin uçtan uca kanıtı henüz yok**; bu yüzden #497 üretim uygulaması tamamlandı sayılmaz, 685 kanala yeni test/taşıma yapılmadı.
- **Aşama 3 FFmpeg:** #543 birleşti; main CI [44842692873](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44842692873) SUCCESS. Bu kısa örnekte gerçek video+audio decode kabulüdür; 18.074 kanalın tümünün işlendiği veya İBO Player cihazda onaylandığı anlamına gelmez.
- **Mükerrer işler:** #514 ve #535'in ortak reconciler/test dosyaları mevcut main'de SHA eşitliğiyle doğrulandı; #535'in eski importer'ı #547 ile güçlendirildi. #514, #535 ve eski eksik-artifact notlu #552 gerekçeli yorumla birleştirilmeden kapatıldı.
- İşlem delili: [v2/reports/issue497-original-artifact-audit-20261121.json](v2/reports/issue497-original-artifact-audit-20261121.json). `v2/tasks/state.json` içinde yalnız yeni devir/gözlem alanı eklendi; 34 görev statüsüne ve ana playlist/URL/kategorilere dokunulmadı.
- **Sonraki tek adım:** #547 importer'ı kimlik ve SHA kilitleriyle gerçek mevcut artifact üzerinden yalnız read-only önizleme/manifest üretip doğrulamak; ardından ASR/OCR/WebVTT kanıt zincirindeki açık gerçek işleri ele almak.
