# MADSC55 TV V2 — Ana çalışma sırası
**Kayıt:** 21 Kasım 2026  
**Baz main:** `3eb84f890cbe8524d16c1a16f219b0b494cc50f0`  
**Amaç:** Kanıtlı eksikleri tek tek kapatmak; tamamlanan işleri tekrarlamamak.

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



### 21 Kasım 2026 — Aşama 4 güvenli örnek alma (kısmi kod kabulü)
- PR #561 `0137e18a2df527afd3124b6bd01d953cae21112a` birleşti: YEDEKLER için manuel/salt-okunur tek tetik kanıt işleme workflow'u; PR CI #44843702938 SUCCESS. 1.107/685 tarihî raporuna dayanır, **canlı retry yapmaz**.
- PR #571 `4b45245f094ffc1aba4e7ecff24f125d502f6d4e` birleşti: bounded FFmpeg capture URL ambiguity reddi, explicit network protocol whitelist ve sentetik negatif güvenlik testleri; PR CI #44843819098 SUCCESS.
- **Aşama 4 tamamen PASS değil:** DNS hostname'leri hâlâ güvenlik için reddediliyor. Gerçek HLS segment/anahtar alt istekleri için egress firewall, izinli alan adı, IP pinning, redirect ve tüm child URL denetimi gerek. URL doğrulama veya FFmpeg whitelist tek başına yeterli değil.
- Gerçek Türkçe konuşma/altyazı yayın örneği ve bağımsız gözlem yok. ASR/OCR/WebVTT yerel fixture'ları nihai Türk/yabancı kararı değildir; gerçek test/kanal taraması SON AŞAMA olarak bekler. Ana playlist/arşiv/EPG yazılmadı.

- PR #567 `7bbefc113b02e25e0d8da1709273c39e9bbb4f12` birleşti: yalnız 685 belirsiz kanalın manuel/kanıt-kilitli yeniden denemesi ve yeniden birleştirme kodu hazır; **hiçbir canlı retry çalıştırması başlatılmadı**. Post-merge main run #44843984931 SUCCESS; #561 run #44843901219 ve #571 run #44843949176 da SUCCESS.


## 21 Kasım 2026 — Aşama 4 DNS güvenliği, gerçek kod kabulü

- **PR #572 merge edildi**, ana dal merge commit `8e9e86b0a422a59b2cfccdd9d732c0a16b442c99`. PR'ın son Production Security Gate Actions run'ı [44844424809](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/44844424809) **SUCCESS**; 14 mevcut capture regresyonu ve 12 yeni pinned-DNS güvenlik testi PASS. Merge sonrası main run `44844614127` ayrı kontrol edilecek.
- Tam uygulama kaydı: [v2/reports/stage4-pinned-dns-capture-20261121.md](../reports/stage4-pinned-dns-capture-20261121.md).
- DNS adları artık **yalnız** onaylanmış genel/unicast IP'ye sabitlenmiş HTTP(S) indirme yoluyla örneklenebilir. DNS cevabında özel/multicast adres varsa fail-closed; HTTPS özgün hostname/SNI doğrular; HTTP redirect ve nested HLS/DASH reddedilir.
- İndirilen finite MP4/Matroska/MPEG-TS dosyaları FFmpeg'e **yerel** dosya olarak ve yalnız `file` protokolü + sabit demuxer ile verilir. ffconcat/metin/manifest otomatik algılaması reddedilir. Çıktı özel geçici dizinde üretilir, mevcut hedefin üstüne yazılmaz. Sonuç yalnız `SAMPLE_CAPTURED_UNVERIFIED`; Türkçe konuşma, altyazı ve cihaz kanıtı değildir.
- **Aşama 4 henüz tamamen tamamlanmadı.** En yaygın IPTV biçimi olan nested HLS/DASH, adaptif segmentler, anahtarlar ve redirect'ler için her alt isteği doğrulayan güvenli collector veya dış ağ egress duvarı gerekiyor; bilinçli olarak bloke. Mevcut legacy IP-literal FFmpeg modu da explicit whitelist'e rağmen egress firewall kanıtı değildir; ayrıca ele alınacak.
- Önceki #567 kodu yalnız 685 belirsiz kaydın manuel, kanıt-kilitli retry hattıdır; CANLI retry çalıştırılmadı. 18.074 tam test, gerçek ASR/OCR/WebVTT, Türk/Yabancı final kararları, gerçek şifreli dış arşiv restore ve İBO Player cihaz kabulü açık.
- Ana playlist, arşivler, EPG, yayın URL'leri ve kategoriler değiştirilmedi. Yeni playlist yok; 48 karantina kanal geri eklenmedi; eski 1003 kuralı uygulanmadı.
- **Sonraki teknik sıra:** (a) güvenli HLS/DASH alt kaynak erişimi/egress tasarımı ve offline negatif testleri, (b) IP-literal legacy modun güvenli transport ile aynı seviyeye getirilmesi, (c) gerçek medya/ASR/OCR/WebVTT kanıtları için izinli manuel kabul, (d) son aşamadaki toplu testler.

## 21 Kasım 2026 — Güncellenmiş devam sırası / Aşama 5 başlatıldı

1. **Bitti, tekrarlama:** #543 FFmpeg ses+görüntü, #547 değişmez 1.792 sonuç, #565 zaman damgalı ASR/OCR/WebVTT inceleme kayıtları. #547 CI `44842556117` ve #565 CI `44843144422` başarılı; ikisi de main'e birleştirildi. Gerçek 18.074 kanal taraması veya cihaz onayı anlamına gelmez.
2. **Aktif Aşama 5:** eski dünya taraması run `42216075104`, artifact `13524765368`, ZIP SHA-256 `6bec426291330c6b4b305e2871b721a25c44583f892c14d893472cdc3e80f87d` doğrulandı. 35.327 aday / 13.884 AV / tarihsel 4.949 URL hash / 3.080 AV verisi 18.074 kaynak envanterine salt-okunur karşılaştırılacak. Önceki tarama kanıtları tekrar sınanmıyor.
3. **Yapılacak kabul:** `v2/yedekler_worldwide_crosswalk.py` + negatif testleri CI'da çalıştır, gerçek `manifest.json` ve `crosswalk.json` artifact'ını doğrula, ilk 2.500 defteri `TEST=1.792, TURK=424, YABANCI=284` ve tüm kategoriler `18.912` ile kayıpsız tutarlı kalmalı. Kesin eşleşme sayılarını yalnız gerçek çıktıya bakarak kaydet. PR merge, CI PASS olmadan yok.
4. **Sonraki adımlar:** tarihsel kanıtla eşleşmeyen veya artık güncel olmayan kayıtları açık blocker olarak tut; Türkçe kanıtı konuşma/altyazı/OCR/kimlik kanallarında birbirinden ayrı izle. Paketli, kontrollü gerçek medya testi ve retry yalnız güvenlik/CI kapılarından sonra. İBO Player'ın kullanıcı kontrollü 2.500 test döngüsüne karışma. Arşiv gerçek ortam bağımsız restore ve İBO cihaz onayı ayrı son kapılardır.

**Dokunulmayacaklar:** tek ana playlist, 48 karantina, 1003 kuralı, kullanıcı onayı olmadan kategori/playlist yazımı yok. Daha önce yapılan Türk/Yabancı taşıma komutları tekrar edilmeyecek. Tam teknik devir kanıtı `DEVAM_NOTU.md` sonunda.


## Aşama 5 kabul edildi / Aşama 6 sıradaki iş — 21 Kasım

- PR #585, merge `cf4b28f16c25af59295c7ee13c3dc5f659585ce1`, PR CI `44845062944` SUCCESS. Gerçek tarama başlatmadan orijinal 18.074 URL hash'iyle dünya raporu karşılaştırıldı; artifact `14682746793` SHA-256 `b995abbb3eca5726d63c1a311a2132c57ded83caf87ca11eee778fc27463692f`. Tam dağılım ve 685 alt kümesinin ayrıntısı `DEVAM_NOTU.md` son kaydında.
- 18.074 özgün URL'nin 18.074'ü ana listede, kategori uyuşmazlığı 0; 16.931 tarihsel dünya eşleşmesi, 1.143 yok; 1.904 doğrudan eski-run AV, 10.947 prior-run hash-only, 4.080 diğer belirsiz eşleşme.
- #497 1.107 WORKING ve 685 RECHECK_REQUIRED içinden hiçbiri otomatik yeniden sınıflandırılmadı. Sonraki adım: 685 belirsiz için eski AV, zaman damgası, güncel durum, URL kimliği, tekrar deneme sayısı ve manifest ile **salt-okunur / idempotent retry önizlemesi**. 20 eski AV kanıtlı belirsiz kanal ayrıca inceleme grubuna konacak.
- Ana playlist değişmedi, yeni playlist açılmadı, envanter ve 838 korunan kayıt yerinde, İBO Player kullanıcı testi son aşamada ve ayrı. 34 ana görev tamamlandı sayılmıyor; Aşama 5'in hash-eşleştirme kod kabulü tamam, canlı 18.074 AV kabulü eksik.



## 21 Kasım 2026 güncellemesi — Aşama 6 plan kodu kabul edildi

- PR #594 merged (`c17af7945921ba61f29c9d2e2918425e897c6cc8`): 685 `uncertain/recheck_required` kaydı için deterministik, SHA-256 kimlikli, kaynak zaman damgalı, idempotent ve no-clobber salt-okunur plan üreticisi eklendi.
- PR Production Security Gate `44846469069` SUCCESS. Çevrimdışı testler; tam 685 satır, mükerrer/eksik kimlik reddi, URL hash eşleşmesi, kaynak rapor/run/artifact bağları, zaman damgası, playlist snapshot ve no-overwrite davranışını doğruladı.
- Bu **plan kodu kabulüdür**; manuel `workflow_dispatch` henüz çalıştırılmadı ve gerçek retry plan artefaktı henüz oluşturulmadı. Canlı retry veya yeni kanal taraması yok. `live_retry_authorized=false`, `network_attempts=0`, playlist/arşiv yazımı kapalı.
- Sonraki öncelikler: (1) Stage 5 tarihsel 18.074 crosswalk satırlarını kimlik/kanıt kaynağı bazında incele, (2) bağımsız özel şifreli kasa restore kabulünü kanıtla, (3) güvenli HLS/DASH segment/anahtar yakalama ve gerçek yayıncı örneği. 18.074 canlı AV taraması, 685 retry ve İBO cihaz testleri son aşamada.
