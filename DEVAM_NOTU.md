## 14 Kasım 2026 — Aşama A devam arşivi: son tamamlanan başarılı/kısmi koşuyu da geri al
- 43598617218 koşusu GitHub Actions tarafında success, tarama raporunda PARTIAL_DISCOVERY_EVIDENCE_ONLY idi. 28.845 kayıttan 28.844 eski gözlem + 1 yeni FFmpeg AV; 8.510 toplam AV kanıtı. Önceki workflow yalnız '--status failure' koşularını aradığından, sonraki taramada bu daha güncel başarıyla yüklenmiş checkpoint atlanabilirdi.
- Onarım: son tamamlanan main gerçek tarama koşularını, sonuç SUCCESS veya FAILURE ayrımı yapmadan listeler; aktif/queued koşuları atlar. Her run artifaktı kendi geçici dizinine indirilir, ilk uygun şifreli checkpoint/legacy envanter alınır. Kimlik/18 saat/şifre anahtarı kontrolleri tarayıcı tarafında korunur. Gerçek A son kabulü hâlâ açık; kod ve offline CI kanıtı canlı resume yerine geçmez.

---
## 14 Kasım 2026 — V2 devam kontrolü: 13 açık görev, gerçek tarama kanıtı, A→B→C→D

**Güncel 34 görev:** tasks/state.json içinde 21 completed, 13 in_progress. Açıklar: #15 #17 #18 #19 #20 #21 #28 #29 #30 #31 #32 #33 #34. Başarısız/eksik kanıt için done işareti verilmez. Diğer sohbetlerdeki paralel PR ve işler ile çakışma kontrolü yapılır.

**Son gerçek tarama:** https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43598617218 (Actions success ama rapor PARTIAL_DISCOVERY_EVIDENCE_ONLY; artifact 14114764986). 105 kaynak listesinden 103 başarılı. Zorunlu kaynak hatası 0; 2 isteğe bağlı kaynağın kimliği ve hataları: integrated-m3u-2b5507d6e11114287bcd / ValueError, integrated-m3u-888758216b11cb003dde / HTTPError. 28.845 aday: 28.844 checkpoint tekrar kullanıldı, 1 yeni AV kontrolü; 8.510 AV kanıtı (8.509 eski, yalnız 1 bu koşuda yeni). 20.335 doğrulanmamış/hatalı aday. Kurtarma: 12.871 RETRY, 2.624 CHECK_AV, 4.840 REVIEW. Şifreli envanter pending.enc olarak tutuldu; archive_restore_test_passed true; cihaz AV kabulü false; yeni 1.000/2.000 paket ihracı 0. Bu başarılı üretim veya tam kanal keşfi kabulü DEĞİLDİR.

**Kaldığı yerden devam kanıtı:** PR #226 per-URL encrypted checkpoint, PR #240 pre-checkpoint eski gerçek envanterden güvenli resume, PR #241 zorunlu ve isteğe bağlı kaynak ayrımı. Eski 28.845 gözlem geri yüklenebildi. Yalnız eski AV yeni FFmpeg kanıtı olarak gösterilmez; 18 saatlik geçerlilik ve URL kimlik kontrolü uygulanır. Çalışma hatalarında checkpoint korunur, runner'ın tamamen kaybolmasında otomatik yükleme garantisi yoktur.

**Yeni düzeltme:** Yeşil Actions koşusuna rağmen partial raporun geçerli görünmesini engelleyecek v2/validate_real_scan_acceptance.py CI kapısı eklenecek. Tam kaynak keşfi, gerçek ve tutarlı decode sayıları, tam şifreli envanter ve M3U test parçaları yoksa iş FAIL olmalı. Bu yalnızca tarama işinin doğrulanmasıdır; nihai A/B/C/D veya cihaz kabulü değildir.

**Bitirme sırası ve kalanlar:**
1. A (#15 #17 #18 #19 #20 #21): #15 bağımsız yayıncı/kaynak kimliği, tarihî 4.955 kayıttan 6 hash eksik; #17/#20 gerçek kurtarma kuyruğu; #18 taze ses+görüntü FFmpeg kanıtı; #19 gerçek XMLTV ile 303 EPG boşluğu; #21 canlı TR/AZ/dünya kaynak kapsamı. YouTube canlı metadata 0, direct HLS 0/120. Fail kaynaklar önce teşhis; eksik yayınlar gerçek gözlemle tekrar ölçülmeli.
2. B (#28 #29 #30): yalnız gerçek AV ve kaynak kanıtıyla 1.000/2.000 M3U, ZIP, manifest, SHA-256, EXTINF/URL birlikteliği, bağımsız cihaz paketi. Eski 4.301 M3U yapısal kanıtı bu koşunun yeni AV kabulü değildir.
3. C (#31 #32 #33): Android/oynatıcı gerçek ses+görüntü, bağımsız haricî şifreli arşiv geri yükleme, nihai üretim kabulü. Offline CI veya yalnız dosya varlığı final kanıtı değildir. C dal ve PR'leriyle çatışma yaratılmayacak.
4. D (#34) EN SON: GitHub/Gist/GitLab/Codeberg/YouTube/resmî yayıncı, dünya ve TR/AZ geniş kaynak keşfi. Canlı Codeberg 429, GitLab API hata ve YouTube/live direct HLS boşlukları çözülmeden done değil.

**Koruma:** Ana İBO, YEDEKLER, YENİLER, FAVORİLER, korumalı üretim tetikleyicileri değişmez. Mevcut kanıt korunur; hatalı kaynaklar sessizce tam keşif olarak kabul edilmez. Birbiriyle yarışan testler ve eski pull request'ler körlemesine birleştirilmez. Manuel kanal taraması kullanıcı talebi olmadan yeniden başlatılmaz.

---
## 13 Kasım 2026 — #28–#30 Unicode M3U satır bütünlüğü KABULÜ
- PR #193 squash merge `8ea0c66296788dda207d75279e44f3db725fd984`: `export_ibo_batches.py` içindeki metadata temizleyici, ASCII CR/LF yanı sıra Unicode NEL (U+0085), LINE SEPARATOR (U+2028), PARAGRAPH SEPARATOR (U+2029) karakterlerini de tek satırlı güvenli boşlukla değiştirir. Yeni regresyon her üçünde tam 3 satır/tek EXTINF üretimini doğrular.
- PR Actions `43482907222` SUCCESS; main Actions `43483112580` SUCCESS: Stage 6 offline kabul, korunan İBO invariants ve üretim tetikleyici güvenlik kontrolleri geçti.
- Önceki URL/metadata filtrelemesi başka bir eşzamanlı PR ile ana dala alındığından çakışan PR #192 kapatıldı; güncel uygulama üzerine yalnızca Unicode ek koruması taşındı.
- Bu kanıt çevrimdışı kod/CI kabulüdür; #28–#33 için gerçek cihaz kabulü, yeni yayın FFmpeg AV ve bağımsız harici geri yükleme açık kalır. Kanıt olmadan görev kapatılmadı. Ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi; kapsamlı tarama başlatılmadı.

## 13 Kasım 2026 — #28–#30 gerçek İBO paketlerinin silinmeden korunması: CI KABULÜ
- PR #183 squash merge `c108fafe1915e9c9b3c1863184a1a1cbdc23d216`: `v2/export_ibo_batches.py` önceki `IBO_AV_VERIFIED_*_PART*.m3u8` paketlerini silen işlemi kaldırdı. Yeni paketler tüm hedef dosya adları için ön kontrol yaparak mevcut dosyayı, sembolik bağlantıyı veya yinelemeli hedefleri reddediyor; klasör sembolik bağlantıları reddediliyor.
- Koruma regresyonları `v2/test_export_ibo_batches.py` içine eklendi; ana Production Security Gate Stage 6 adımına test çağrısı bağlandı.
- PR Actions run `43481457491` SUCCESS; merge sonrası main Actions run `43481721700` SUCCESS. Kanıt: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43481721700
- Bu, **sistem güvenliği/çevrimdışı test kabulü**dür; gerçek cihazda yayın, bağımsız harici arşiv restore veya nihai 1000/2000 İBO paket teslimi kabulü değildir. #28–#33 statüleri değiştirilmedi; ana İBO, YEDEKLER, YENİLER, FAVORİLER ve kapsamlı tarama korunuyor.

## 13 Kasım 2026 — #31–#33 Stage 5 güvenlik düzeltmesi main kabulü
- PR #181 başarıyla squash merge edildi: `a04ca3e8bb7e4148efdab1d6cddb00a11427328f`. Kaynak PR: https://github.com/Madsc55/MADSC55-TV-V2/pull/181
- Güncel main tabanlı PR commit'i `643c19d9819ab34247b823451557bfaf4a132005` için Production Security Gate Actions https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43481305204: SUCCESS. Korunan İBO invariants, görev defteri, Stage 2/3, Stage 5, Stage 6 ve #34 çevrimdışı kabul adımları PASS.
- Stage 5 kanıt URL'lerinde özel/yerel IP, bozuk port, saklı kullanıcı bilgileri, kontrol karakterleri ve .local/.internal gibi yerel ana makine alanları reddedilir; bozuk JSON şeması fail-closed, mevcut kabul çıktısı exclusive create ile korunur. Negatif regresyon testleri main'de doğrulandı.
- Bunlar sadece çevrimdışı güvenlik/altyapı kabulüdür. Gerçek FFmpeg görüntü/ses, harici şifreli geri yükleme, gerçek 1000/2000 İBO paketleri ve cihaz kabulü doğrulanmadı. #31–#33 nihai kapatılmadı, task ledger değiştirilmedi; ana İBO/YEDEKLER/YENİLER/FAVORİLER korunuyor ve kapsamlı tarama başlatılmadı.

## 13 Kasım 2026 — #19 sahte EPG kabul işareti engellendi (PR #161)
- PR #161 squash merge: `a715a612facf325322e2b911366b8d5f45a173a5`. Stage 2 entegrasyonu, XMLTV doğrulama kaynağı olmadan gelen `epg_programme_available=True` ve sahte `epg_match_type` değerlerini sıfırlıyor.
- PR baş commit `5615599e06196d77e6daa1937074e292b27cf17d` için Production Security Gate Actions `43480580074` SUCCESS; gerçek logda `test_untrusted_xmltv_programme_claims_are_not_promoted` PASS, Stage 2/3 grup testleri PASS.
- Daha önce ana dala alınan PR #156, XMLTV programının geçerli başlangıç/bitiş zamanı ve tekil kanal kimliği olmadan mevcut sayılmasını zaten engelliyor. PR #161, bu kanıtın haricî girdiden sahte biçimde eklenmesini kapatıyor; bağımsız kabul şartı korunuyor.
- #19 in_progress: gerçek EPG boşlukları ve #18 bağımlılığı açık. Bu yalnızca offline kabul kanıtıdır; yeni canlı kanal/EPG taraması, gerçek AV veya nihai yayın kabulü değildir. Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi.

## 13 Kasım 2026 — Gerçek İBO 4.301 AV paketinin bağımsız ZIP/M3U denetimi
- Gerçek Actions run `43412576224` SUCCESS; artifact `14033805492`, ZIP SHA-256 `139c8a0868f35d4b64cd55a17bcbd56325d8e3c87b5d07295028bb4d56e832a6` kontrol edildi.
- ZIP içindeki 1000'lik parçalar 1000+1000+1000+1000+301, 2000'lik parçalar 2000+2000+301; her ikisi tam 4301 farklı URL, birebir aynı sıra, sıfır URL tekrarı, sıfır eşleşmemiş EXTINF. Rapor: 13735 yeni aday, 4301 AV, 9434 doğrulanmamış; mock=false, arşiv roundtrip=true (rapor beyanı), cihaz playback=false.
- Bağımsız paket bütünlüğü raporu: `v2/reports/IBO_REAL_BATCH_INTEGRITY_2026-11-13.md`. Bu iş yeni tarama yapmadı, şifreli envanteri çözmedi, fiziksel cihaz veya bağımsız bulut geri yükleme kanıtı üretmedi. #28–#33 statüleri kanıt sınırları nedeniyle değiştirilmedi. Ana İBO/YEDEKLER/YENİLER/FAVORİLER değişmedi.

## 13 Kasım 2026 — #34 federated API yanıtı güvenliği (kanıtlı entegrasyon)
- PR #151 squash merge `171a3c50`: GitLab/Codeberg M3U kaynak aramasına genel terimler eklendi; önceki TR/AZ terimleri ve bounded/project limits korundu. Main Actions `43479368483` SUCCESS.
- PR #154 squash merge `4e50de45`: HTTP 200 API hata nesnelerinin başarılı boş depo araması olarak kaydedilmesi engellendi. 5 negatif çevrimdışı regresyon testi eklendi; PR Actions `43479623350` ve main Actions `43479774992` SUCCESS.
- PR #160 squash merge `1c76c9a8`: HTTP 200 hatalı GitLab/Codeberg depo-ağacı yanıtlarının başarılı boş sonuç sayılması engellendi. 4 negatif çevrimdışı regresyon testi eklendi; PR Actions `43479941927` ve main Actions `43480100836` SUCCESS.
- Bu entegrasyonlar **yalnızca çevrimdışı altyapı/safety kabulü**dür. Canlı Codeberg 429 engeli; gerçek worldwide FFmpeg görüntü/ses kabulü; gerçek 1000/2000 İBO paketleri; bağımsız harici şifreli restore halen açıktır. #34 görev kaydı kapatılmadı. Yeni kapsamlı kanal taraması başlatılmadı; ana İBO/YEDEKLER/YENİLER/FAVORİLER değiştirilmedi.

## 13 Kasım 2026 — #34 keşif kanıtı üzerine yazma koruması
- Güncel main üzerinde PR #157 squash merge `b0ed1797e31e9953125473adca9be56b06dd4484`; eski PR #152 main ile çakıştığı için merge edilmeden kapatıldı.
- `v2/discovery_34.py` ve `v2/discovery_34_integrate.py` raporları artık yalnız `open("x")` ile yazar; önceden mevcut aday veya entegre raporu asla üzerine yazmaz.
- İki CLI için regresyon testleri mevcut raporun byte içeriğini koruduğunu ve işlem kodunun başarısız döndüğünü doğrular.
- PR head `5161a4263faada3376fbd9e9fae64d243f748a97` için Actions run `43479914354`: SUCCESS. Production Security Gate, Stage 2/3, Stage 5/6, #34 offline entegrasyon ve korunan İBO invariantları PASS.
- Bu sadece kod ve çevrimdışı kabul kanıtıdır. Canlı Codeberg, yeni gerçek AV, 1000/2000 gerçek İBO paketleri ve bağımsız geri yükleme doğrulaması açık. Yeni toplu kanal taraması ve korunan liste değişikliği yapılmadı.

## 13 Kasım 2026 — PR #106 güncel ana dal kabul testi başarılı
- PR #106 (`integrate-stage6-28-33-current-main-20261113`) için Actions run `43457997079` completed / success.
- Tüm adımlar SUCCESS: grouped safety regression tests; production trigger/write policy; original IBO category/backup invariants; historical task ledger; Stage 2 identity recovery metadata; Stage 6 offline package/archive regressions; Stage 2/3 offline identity, EPG and recovery; Discovery #34 offline adapter/integration acceptance.
- Bu, PR #106'nın merge test ağacında çevrimdışı ve güvenlik kabulüdür. Gerçek FFmpeg AV, gerçek harici bağımsız restore ve üretim kanal paketi kanıtı yerine geçmez.
- PR #87 kapatıldı; PR #106 squash merge commit `478aba262b0b37c39019a85bcc3abfc812b04208` ile birleştirildi. PR #106 merge test ağacı Actions run `43457997079`: SUCCESS.
- Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi; kanal taraması başlatılmadı.

## 13 Kasım 2026 — Aşama 2 (#15, #17–#21) çevrimdışı kabul kapısı ana dala alındı
- PR #72 squash merge `e333adca5c0497de6c021e021d74b3369571276d`; ana Production Security Gate Actions `43455393756` SUCCESS.
- Başarılı adımlar: Stage 2 identity/recovery/metadata integration acceptance; Stage 2/3 offline identity, EPG and recovery acceptance; Stage 6 offline package/archive; #34 offline adapter/integration; production security and protected IBO invariants.
- Bu kanıt mevcut gözlemler üzerinde çevrimdışı entegrasyon içindir. Canlı motorun tüm üretim girdilerinde devreye alındığı, gerçek yayın AV, logo/EPG varlığı veya 1.000/2.000 gerçek İBO paketleri kanıtlanmış değildir. #15/#17–#21 ve #28–#33 görevleri bu sebeple otomatik kapatılmadı.
- Yeni kapsamlı kanal taraması yapılmadı; ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi.

## 13 Kasım 2026 — PR #53 kontrol karakteri regresyonu ve CI kabulü
- PR #53 düzeltmesi: `v2/test_discovery_34.py` gerçek newline/CR/NUL/DEL karakterlerini Python string kaçışlarıyla test eder; önceki hatalı fixture nedeniyle başarısız testin kendisi düzeltildi. Üretim URL reddetme kontrolü PR #45 ile ana dala alınmıştı.
- GitHub Actions run `43451905845`: SUCCESS. Ana güvenlik kapısı, görev defteri bütünlüğü, Stage 6 offline paket/arşiv ve #34 offline keşif testlerinin tüm adımları PASS.
- Bu koşu canlı GitHub/GitLab/Codeberg API erişimini, yeni adayların FFmpeg ses/görüntü kanıtını veya bağımsız arşiv geri yüklemesini doğrulamaz. #34 ve #28–#33 gerçek kanıt kabulleri açık. Kapsamlı tarama yapılmadı; ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi.

## 13 Kasım 2026 — Güncel görev defteri ve PR #48 kabul kanıtı
- `v2/tasks/state.json` doğrulandı (GitHub Contents API): 34 kayıt; 21 completed, 11 pending, 2 in_progress. Bu sayım yalnızca defter statüsüdür; idari kapanışlar gerçek yayın onarımı/AV kanıtı anlamına gelmez.
- #15 in_progress: 1.777/4.955 tarihî hash IPTV-org kataloğuyla eşleşti; 3.178 hash için güncel katalog eşleşmesi yok, eksik yayıncı atıfları ayrıca doğrulanmalı.
- #34 in_progress: çevrimdışı sistem doğrulaması başarılı; keşif sonucu, yeni adayların AV doğrulaması ve arşiv kanıtı bekleniyor.
- #17, #18, #19, #20, #21 ve #28–#33 pending. #18/#19/#20 bazı kısmi ölçüm kanıtlarına sahip; bağımlı görevlerin nihai kabulü henüz tamamlanmadı.
- PR #48 merge commit `f82156e7c36612f0e05c373706ab436608779ca8`; PR head `3a8b4cc1fbe47e0b8f495585d5111f26c7bf72b3` için Actions `43449878648` SUCCESS: güvenlik, korunan İBO, Stage 6 offline paket/arşiv ve #34 offline keşif adımları PASS.
- Canlı #34 API sözleşmesi ve yeni aday AV/arşiv kabulü bu koşuda yapılmadı. Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi; kapsamlı yeni tarama başlatılmadı.

## 13 Kasım 2026 — #34 PR #37 birleşimi ve doğrulanmış CI kanıtı
- PR #37 squash merge `b981b139cfaae6a1a83b9d31db268f12cd60e636`: HTTP 408/425 retry, API host tanılaması ve iki regresyon testi `main` dalında.
- PR baş commit `d2756c804a384a9f72e4aec2b7d19217cb381bf0` için GitHub Actions `43449222459` SUCCESS; güvenlik, İBO koruması, Stage 6 offline paket/arşiv ve #34 offline keşif PASS.
- Canlı API sözleşmesi ve gerçek FFmpeg görüntü/ses kabulü bu çalışmayla kanıtlanmadı; #34 ve gerçek kanıt isteyen #28–#33 açık. Kapsamlı tarama ve korunan listelerde değişiklik yok.
- `v2/tasks/state.json` istenen yolda 404; mevcut olmayan dosyada görev kapanışı yapılmadı.

## 13 Kasım 2026 — #34 güncel main üzerinde API tanılama düzeltmesi
- Güncel `main` tabanlı `fix-34-api-diagnostics-current-main-20261113` dalında HTTP 408/425 retry ve API host tanılaması (`584b476`) ile iki regresyon testi (`eaea679`) eklendi. Var olan yanıt şeması ve bağlantı kesintisi kontrolleri korundu.
- CI ve canlı Codeberg API kabulü bekleniyor; #34 açık. Ana İBO ve YEDEKLER/YENİLER/FAVORİLER değişmedi; kanal taraması yapılmadı.

## 13 Kasım 2026 — güncel main tabanlı #34 PR #30 güvenlik işi PASS
- Dal fix/v2-34-socket-retries-20261113, PR #30: commit f950fb09 ile geçici socket hataları için en fazla üç deneme; commit 7a294735 ile dört HTTP/socket regresyon testi.
- GitHub Actions run 43448792241: "Verify suspended publishers, no cron and immutable IBO" işi SUCCESS. Güvenlik regresyonları, İBO invariants, Stage 6 çevrimdışı paket/arşiv ve #34 offline adapter/entegrasyon adımları SUCCESS.
- Bu güvenlik işi canlı Codeberg API sözleşmesi veya gerçek FFmpeg AV kabulü değildir. #34 nihai kabulü AÇIK; kapsamlı tarama yapılmadı, korunan İBO/YEDEKLER/YENİLER/FAVORİLER değiştirilmedi.

## 13 Kasım 2026 — Stage 6 temiz PR CI kabulü
- PR #27, commit cd24cc65ded9be6c5b2e242d31c20ed8cb515553: GitHub Actions 43448236664 SUCCESS. `Stage 6 offline package and archive acceptance regressions` adımı PASS; güvenlik kilidi, ana İBO koruma ve #34 offline entegrasyon adımları da PASS.
- Bu sonuç çevrimdışı test kanıtıdır. Gerçek yayın görüntü/ses, bağımsız harici arşiv geri yükleme ve nihai cihaz/kanal kabulü henüz kanıtlanmadığından #28–#33 nihai görevleri kapatılmadı.
- Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi; kapsamlı tarama başlatılmadı.

## 13 Kasım 2026 — #34 canlı API retry düzeltmesi ana dalda; nihai kabul açık
- PR #24 squash merge: 313a9abe6f44af1635523823ac69e17b74f0ea54. Canlı API geçici hatalarında en çok üç deneme, beş regresyon testi ve mevcut grouped acceptance iş akışına test çağrısı eklendi.
- PR baş commit'i c4f204d4 için Production Security Gate Actions 43447044630: SUCCESS; güvenlik, İBO invariants ve offline discovery başarılı. Bu koşu yeni retry testlerinin veya canlı Codeberg API kabulünün başarılı çalıştığına kanıt değildir.
- Merge sonrası yeni Actions kabulü henüz doğrulanmadı; #34 açık. Kapsamlı tarama yapılmadı; ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi.

## 13 Kasım 2026 — #34 son güvenlik regresyonu PASS
- Commit bb52eac0, GitHub Actions 43327990827: SUCCESS; discovery offline acceptance, source-host restrictions, production security and IBO invariants PASS.
- Codeberg canlı API kabulü hâlâ ayrıca doğrulanmalı; workflow_dispatch ile çalışan canlı sözleşme adımı henüz yürütülmedi. #34 nihai kabul açık; playlist değiştirilmedi.

## 12 Kasım 2026 — #34 toplu çevrimdışı kabul PASS
- Commit 574d5d69, GitHub Actions run 43322841131: SUCCESS. Production Security Gate, IBO invariants ve "Discovery 34 offline adapter and integration acceptance" adımı SUCCESS.
- Altı adaptörün offline birim/entegrasyon kabulü tamamlandı. Bu sonuç canlı Codeberg API erişimini veya gerçek FFmpeg AV kanıtını doğrulamaz.
- Codeberg canlı API HTTPError nedeniyle #34 tam canlı kabul açık. Ana İBO değiştirilmedi.

## 12 Kasım 2026 — #34 izinli kabul iş akışına bağlandı
- Commit ab0066e6 için Production Security Gate run 43321317264 SUCCESS.
- Yeni workflow eklemek güvenlik envanterini bozduğundan #34 çevrimdışı kabul adımları mevcut, izinli, salt-okunur v2-stage6-grouped-acceptance.yml iş akışına 1ab65026 commit'i ile eklendi. Workflow yalnızca workflow_dispatch ile çalışır; bu commit için henüz yeni #34 Actions kabul sonucu yoktur.
- Codeberg canlı API isteği önceki testte HTTPError verdi; yeni başarılı canlı kabul kanıtı yoktur. #34 açık kalır. Ana İBO korunur.

## 12 Kasım 2026 — #34 güvenlik düzeltmesi doğrulandı
- Production Security Gate run 43320335176: SUCCESS, commit 4019cb7c. Workflow envanteri ve korunan İBO dosyası kontrolü geçti.
- Codeberg canlı sözleşme testinde HTTPError vardı; v2/discovery_34_live_contract.py hata HTTP durum kodunu raporlayacak şekilde iyileştirildi (1beaf556). Bu değişikliğin canlı kabul testi henüz yapılmadı.
- #34 kapatılmadı: Codeberg canlı sözleşme kabulü ve onaylı workflow altında altı adaptörün uçtan uca kabulü açık.

## 12 Kasım 2026 — #34 güvenlik ve canlı API hata analizi
- Actions run 43319831631: offline-acceptance PASS; live-contract FAIL. GitHub API 20 aday, GitLab API 0 aday/başarılı yanıt, Codeberg HTTPError.
- Actions run 43319830482: güvenlik kilidi, yeni v2-discovery-34-offline.yml dosyasını beklenmeyen workflow saydı. Kilidi değiştirmeden bu yeni workflow dosyası efddbdd4 commit'inde kaldırıldı. Test kodları dalda korundu.
- #34 nihai kabul açık: Codeberg erişim sorunu ve izinli Actions kabul yolu çözülmeli. Başarısız testler tamamlandı sayılmadı. Ana İBO değişmedi.

## 12 Kasım 2026 — #34 güncel kabul
- Entegre çevrimdışı kabul başarılı: GitHub Actions run 43318458059 (success), commit 9b04bff570602ce31520e70dd03429f06cf95a0f.
- Gerçek GitHub/GitLab/Codeberg API uçlarının uçtan uca üretim doğrulaması henüz yapılmadı; #34 nihai kabulü açık. Kanal taraması ve İBO değişikliği yok.

## 12 Kasım 2026 — #34 keşif adaptörleri (geliştirme dalı)
- Dal: stage7-34-discovery-adapters-20261112. v2/discovery_34.py: GitHub/GitLab/Codeberg arama API adaptörleri; official/youtube/m3u aday kimliği normalizasyonu; salt-okunur, ağ erişimi yalnızca --network ile.
- v2/test_discovery_34.py: çevrimdışı birim testleri. .github/workflows/v2-discovery-34-offline.yml: compile, unit test, offline smoke acceptance.
- Gerçek kaynak taraması yapılmadı; yeni AV kanıtı üretilmedi; ana İBO/YEDEKLER/EPG değiştirilmedi.
- #34 henüz kabul edilmedi: yeni Actions koşusunun yeşil sonucu ve adaptörlerin gerçek servis yanıtları doğrulanmalı; official/youtube/m3u mevcut keşif modülleriyle üretim entegrasyonu tamamlanmalı.

## 2 Kasım 2026 — kaynak kimliği bütünlüğü ve 500'lük varsayılan paket (yeni çalışma)
- `v2/consolidate_inventory.py` eski `source_id` ile yeni `source_ids` aynı kayıtta bulunduğunda ikisini de saklar (59d594e). Regresyon testi eklendi (9e44e86).
- `v2/real_ibo_scan.py` geçmiş arşivden okunan her iki kaynak kimliği biçimini kayıpsız birleştirir ve varsayılan paket boyutu son kullanıcı kararıyla 500'dür (401d194). Offline regresyon testi eklendi (28c97fa).
- Eski workflow run 41189283457'nin compile/protect/discovery-tests/safety işleri başarılı görüldü; bu eski run yeni commitlerin test kanıtı değildir. Yeni commitlerin Actions başarı sonucu doğrulanmadı.
- Yeni internet taraması başlatılmadı; korunan playlist/YEDEKLER/EPG/favoriler değiştirilmedi. #60 gerçek URL kurtarma ve harici kalıcı şifreli yedek hâlâ açık.

## 2 Kasım 2026 — eksik taramada paket koruması
- `v2/real_ibo_scan.py` eksik kaynak taraması durumunda eski başarılı IBO paketlerini silmeyecek biçimde değiştirildi; eski `source_id` kaynak kimlikleri de taşınır (commit c6ce007d).
- Değişiklik GitHub'a kaydedildi; Actions sonucu ve uçtan uca doğrulama henüz teyit edilmedi. Yeni ağ taraması başlatılmadı, ana liste/YEDEKLER/EPG değiştirilmedi.
- Gerçek geçmiş #60 kayıtlarının adres bazında kurtarılması ve GitHub dışı kalıcı şifreli arşiv doğrulaması açık işlerdir.

## 2 Kasım 2026 — tarihsel kaynak kimliği uyumluluğu
- `v2/consolidate_inventory.py` eski `source_id` alanını `source_ids` listesine taşır; bozuk `observations` öğelerini reddeder (654767c1). Offline regresyon testleri eklendi (d359444b).
- Son commitler için Actions sonucu doğrulanmadı. #60 kayıplarının gerçek adreslerle kurtarılması ve GitHub dışı kalıcı yedekleme hâlâ açık. Ağ taraması ve YEDEKLER aktarımı yapılmadı.

## 2 Kasım 2026 — şifreli arşiv geri yükleme testleri
- `v2/test_secure_archive_roundtrip.py` oluşturuldu (commit 20067e68): çevrimdışı fikstür üzerinde şifreleme, geri yükleme, bozulma ve yanlış şifre reddini sınar. Gerçek yayın verisi veya gerçek tarama değildir.
- `.github/workflows/v2-offline-inventory.yml` bu testi CI'a dahil eder (commit 5d654015).
- Bu değişiklik **harici kalıcı özel depolama sağlamaz**; Actions başarı sonucu henüz teyit edilmedi. Gerçek tarihsel kayıt kurtarma ve harici depolama hâlâ açık.

## 2 Kasım 2026 — son altyapı değişiklikleri ve açık doğrulamalar
- Gerçek tarama BAŞLATILMADI; ana playlist, EPG, YEDEKLER ve yabancı arşiv değiştirilmedi. Yeni adayların YEDEKLER'e aktarımı yalnızca kullanıcı onayıyla, 500'lük gruplarla yapılır.
- `v2/real_ibo_scan.py`: geçmiş envanterdeki kaynak kimlikleri ve gözlemler sonraki taramada korunacak biçimde güncellendi; 3964 yabancı arşiv kaydı benzersiz URL sayısına eşit olmak zorunda değil; eksik tarama raporunda yazılmayan paket sayısı sıfırlanır (commit 136565c7).
- `v2/consolidate_inventory.py`: dosya yolunun farklı yazımlarıyla şifreli girişin üzerine yazma, yinelenen giriş ve rapor/giriş çakışması engellendi (commit 134355e5).
- Offline CI artık tarayıcının Python sözdizimini de denetliyor; ağ taraması çalıştırmıyor (commit 556f7717).
- `v2/test_consolidate_inventory.py`: gözlem geçmişi roundtrip, bozuk arşiv reddi, giriş/çıkış yol çakışması ve tekrar giriş regresyonları eklendi (commit 5bd76de ve 6753f451).
- **Doğrulanmamış:** Bu son commitlerin Actions yeşil sonucu; geçmiş #60 kayıplarının gerçek URL bazında kurtarılması; harici özel depolamaya yedek aktarımı ve geri yükleme; gerçek uçtan uca üretim koşusu. Bunlar tamamlandı diye raporlanamaz.

# MADSC55 TV V2 — TEK DEVAM NOTU

## 2 Kasım 2026 — toplu altyapı tamamlama, taramasız
- Kullanıcı açıkça yeni tarama istemiyor; eski kayıtların saklanması, entegrasyon ve offline doğrulama öncelikli. 500'lük YEDEKLER aktarımı yalnızca yeni açık kullanıcı talimatıyla yapılır.
- `v2/consolidate_inventory.py` oluşturuldu (commit 1bbb788f): gerçek JSONL girişlerini URL'ye göre birleştirir; kaynak kimliklerini ve her gözlemi saklar; şifreli arşivi diske yazar ve geri yükleme kontrolü yapar. Yeni yayın adresi uydurmaz, internete çıkmaz.
- `v2/test_consolidate_inventory.py` (commit 9628e09e) sentetik **yalnızca offline test fikstürü** kullanır; gerçek kanal çıktısı olarak sunulmaz.
- `.github/workflows/v2-offline-inventory.yml` (commit b330fbdc) sadece offline bütünlük testlerini çalıştırır; kanal taraması yapmaz. İlk Actions sonucu henüz teyit edilmedi.
- Henüz gerçek geçmiş JSONL dosyaları bu birleştiriciye verilmedi, kalıcı harici depolama sağlanmadı ve #60 URL kurtarma yapılmadı. Bunlar açık işlerdir.
- 38 aktif YEDEKLER ve 3964 yabancı arşiv değişmedi. EPG ve ana playlist düzenlenmedi.


## 2 Kasım 2026 — kullanıcının yeni öncelik kararı
- **Şimdi kanal araması/taraması başlatılmayacak.** Önce altyapı, entegrasyon, kaynak kaybı koruması, envanter ve offline test eksikleri kapatılacak.
- Kanal araması tamamlandıktan sonra adaylar önce kalıcı envanterde saklanacak. **Kullanıcı açıkça söylemeden** YEDEKLER'e hiçbir aday aktarılmayacak.
- Kullanıcının yeni İBO test grubu **500 kanal** (önceki 2000'lik kararının yerine geçer). 500 sayısını doldurmak için sahte/çalışmayan URL üretilmeyecek.
- Ana V2 playlist, 38 mevcut YEDEKLER kanalı, 3964 kayıtlı yabancı arşivi, EPG ve favoriler korunacak; TRT 1 ile DHA ilk iki sırada.
- `.github/workflows/v2-public-source-audit.yml` günlük otomatik taraması durduruldu; workflow elle çalıştırılabilir, ancak kullanıcı onayı olmadan tetiklenmeyecek. Commit a36e7ca7.
- Diğer keşif workflow'larının zamanlayıcıları ayrı ayrı denetlenmeli; bu değişiklik **bütün taramaların durduğu anlamına gelmez**.
- Kodun varlığı, Actions başarısı ve kalıcı arşiv/üretim teslimi birbirinden ayrı doğrulanacak.


## 2 Kasım 2026 — güncel durum (önceki tarihli notları geçersiz kılan kararlar)
- Çalışılan tek depo: Madsc55/MADSC55-TV-V2. Ana dosya: MADSC55_TV_IBO_CALISANLAR_TEST.m3u8.
- Kullanıcı YEDEKLER 1-38 kayıtlarını korumayı, 39-4002 arasındaki 3964 kaydı ayrı yabancı arşive taşımayı onayladı. Arşiv: v2/arsiv/yabanci_yedekler_2026-11-02_3964.m3u8.
- V2 ana listede 838 diğer kategori kaydı + 38 YEDEKLER = 876 kayıt bulunur. TRT 1 ve DHA YEDEKLER ilk iki sırada, EUROSPORT 1 HD TR üçüncü, 24 dördüncü, ADA TV beşinci sıradadır.
- Arşivdeki 3964 yayın adresi korunur; bunlar otomatik olarak Türkçe sayılmaz ve yeniden İBO test adayı yapılmaz.
- v2/real_ibo_scan.py, yabancı arşivi zorunlu olarak okuyup URL'leri yeni adaylardan ayıklayacak şekilde güncellendi; commit 4c7fddeb. Bu kodun yeni Actions koşusu henüz doğrulanmadı.
- Eski raporlarda 12148 ana listede olmayan URL ve 4098 AV doğrulama adayı bildirilmişti; güncel 500 kanal paketi hazırlanmış veya YEDEKLER'e eklenmiş değildir. Eski Actions artifact verileri yeniden elde edilmeli; yeni ağ testi ve Türkçe/Azerice kontrolü yapılmalıdır.
- DEVAM_NOTU.md'nin aşağıdaki 27 Ekim kayıtları tarihsel bilgidir; eski YEDEKLER=2 ve 1047 kanal sayımları artık güncel değildir.
- Koruma testleri 38 YEDEKLER + 3964 arşiv kuralına uyarlanmıştır. Gelecekte kullanıcı onayıyla 500 kanal eklenecekse testlerin sabit 38 sayımı da kontrollü güncellenmelidir.
- GitHub Actions gerçek koşu sonucu ve IBO Player yenilemesi ayrı doğrulanır; commit başarısı oynatım kanıtı değildir.


**Son güncelleme:** 27 Ekim 2026 — çok kaynaklı M3U arama ve kanal URL çakışma denetimi
**Kural:** Projede devam ve devir için TEK kanonik dosya budur: `DEVAM_NOTU.md`. Yeni devir/durum notları açma; her çalışma sonunda bu dosyayı güncelle. Eski mimari K1–K5 ve 92 workflow geri getirilmeyecek.

## Değişmezler
- Kullanıcının İBO'da kullandığı **asıl playlist**: https://raw.githubusercontent.com/Madsc55/Madsc55-Tv/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8
- İBO EPG: https://madsc55.github.io/madsc-tv/madsc-epg.xml
- V2 geliştirme playlisti: https://raw.githubusercontent.com/Madsc55/MADSC55-TV-V2/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8
- Bu iki playlist **ayrı GitHub depolarındadır**. V2'yi güncellemek İBO'nun mevcut adresini otomatik güncellemez. Asıl İBO dosyasına geçmeden önce güvenli karşılaştırma, koruma ve son doğrulama yapılmalı.
- Orijinal favoriler, kategoriler, yayın URL'leri ve EPG korunacak. YEDEKLER'deki **TRT 1 1440P QHD** ve **DHA CANLI 720P HD** kesinlikle silinmeyecek.
- İBO uyumluluğu teyit edilmemiş YouTube sayfa URL'lerini doğrudan M3U yayını gibi ekleme. Telif, yayın hakkı, DRM, erişim anahtarı ve coğrafi kısıtlamaları atlatma.

## Tamamlanan ve doğrulanan
1. V2 ana playlisti kullanıcı talebiyle **1047 kayıt** oldu; YEDEKLER yeniden yalnızca **2 orijinal kanaldan** oluşuyor. Son değişiklik commit 60a98365deae3ba1b7c0fc8894a640a8ea3662fe.
2. TRT Arabi ve TRT World yabancı dil nedeniyle V2 listesinden çıkarıldı. Aras TV, Haber61 TV, TV Den ve YOL TV, YEDEKLER'den alınıp hem **📍 YEREL (74)** hem **📺 HEPSİ (378)** kategorilerine eklendi. Orijinal TRT 1 ve DHA CANLI YEDEKLER (2) içinde korundu. Yeni kanalların İBO Player'da uzun süreli oynatımı henüz kanıtlanmadı.
3. IPTV-org dünya, Türkiye, İsveç M3U listeleri ve Türkiye kanal dizini üzerinden keşif; bağlantı/ffprobe kontrolü. Kaynaklar `v2/config/sources.json` dosyasında.
4. `v2/youtube_discovery.py` eklendi: YouTube'da beş Türk TV arama sorgusu, sınırlı aday keşfi, en fazla 12 adayın canlı yayın metadatası kontrolü. Bulunanlar `v2/reports/youtube-live-candidates.json` dosyasına raporlanır; **playlist otomatik değişmez**.
5. `.github/workflows/v2-youtube-discovery.yml` eklendi: günlük ve elle tetiklenen keşif, rapor artifact'ı. **İlk çalışmanın başarı sonucu ayrıca kontrol edilecek.**

## Açık işler — öncelik sırasıyla
1. **YouTube iş akışının ilk çalışmasını kontrol et:** syntax, arama erişimi, aday sayısı, canlı doğrulama sayısı, hatalar. Gerekiyorsa düzelt ve tekrar çalıştır. `yt-dlp` arama başarısı platform koşullarına bağlıdır.
2. **Resmî TV siteleri keşfi:** \`v2/official_sites_discovery.py\` ve haftalık \`v2-official-sites.yml\` eklendi; Türkiye kanallarının resmî web sitelerini kamuya açık katalogdan raporlar. İlk workflow **başarılı**: run 40555364316, **370 resmî web sitesi kaydı**. \`v2/official_site_gap.py\` eklendi: bu kayıtları V2 playlistindeki isim/ID ile karşılaştırır; workflow **başarılı**: run 40555669301, 370 site, 6 kesin isim/ID eşleşmesi, 364 manuel inceleme gerektiren kayıt. 364 eksik kanal demek değildir; takma ad önerileri için kod güncellendi. İlk alias test run 40556916080, satır 19'da yanlış literal \\n yüzünden SyntaxError verdi; düzeltme commit 22eb5be93ffd844a90f085b49c63277e0e81a92c, yeniden test run 40557210310. Sonuç doğrulanacak. Ardından izinli yayın oynatıcı türü/İBO uyumluluğu analizi ekle. DRM/token aşma yok.
3. **Kaynak çeşitliliği:** başka kamuya açık ve meşru IPTV dizinlerini güvenilirlik açısından incele; tekrarları, yanlış ülke eşleşmelerini ve sahte Türk kanalı isimlerini ele. Yeni kaynakları ancak doğrulayınca `sources.json` içine ekle.
4. **İBO uyumluluğu:** yeni altı kanalı gerçek İBO Player üzerinde kullanıcıyla doğrula; uzun süreli çalışma, EPG ve logoları test et. Sadece ffprobe başarılı olması yeterli değildir.
5. **Asıl İBO playlistiyle eşitleme:** eski `Madsc55/Madsc55-Tv` deposunun canlı dosyasını ve kategorilerini karşılaştır; hiçbir eski kaydı değiştirmeden yalnızca kullanıcı onaylı, doğrulanmış yeni kanalları ekle. Güncellemeden önce/sonra sayım ve içerik bütünlüğü testini yap.
6. **Otomasyon güvenliği:** `v2-promote-yedekler.yml` tek seferlik iş akışıdır; gelecekte yanlışlıkla tekrar çalışıp YEDEKLER sayısını çoğaltmaması için kontrol et. Her eklemede önceki 2 yedek de korunmalı.

## 27 Ekim 2026 son ilerleme\n- YouTube workflow başarılı: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/40554927212 — 27 aday, 0 canlı doğrulama, 0 arama hatası.\n- Resmî TV sitesi keşif kodu ve haftalık workflow eklendi; ilk çalışma **başarılı**: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/40555364316 — 370 site kaydı. Fark karşılaştırması başarılı: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/40555669301 — 6 eşleşme, 364 inceleme kaydı. Eşleşme yönteminin kısıtları nedeniyle 364 eksik kanal sonucu çıkarılamaz.\n- IPTV-org API kanal/stream/logo/EPG/blocklist uçları belgelendi: https://github.com/iptv-org/api . Resmî site keşfi sadece kanal kataloğu URL'lerini listeler, doğrudan stream doğrulaması değildir.\n\n## Son kontrol ve erişim engeli\n- V2 playlisti GitHub'dan tekrar okundu: **1047 kanal, 2 YEDEKLER**; iki orijinal yedek mevcut.\n- **Asıl İBO deposu erişim engeli:** \`Madsc55/Madsc55-Tv\` içindeki \`MADSC55_TV_IBO_CALISANLAR_TEST.m3u8\` dosyasına GitHub bağlantısı 404 döndürüyor. Depo listesinde yalnızca \`madsc-tv\` ve \`MADSC55-TV-V2\` erişilebilir. \`Madsc55/madsc-tv/CALISANLAR.m3u\` dosyası ayrıca kontrol edildi: 1039 kanal ve orijinal 2 YEDEKLER; eski V2 playlist blob SHA'sıyla birebir aynı (b40aaf...). Ancak kullanıcının verdiği **İBO raw URL'si \`Madsc55/Madsc55-Tv\`** deposuna işaret ediyor ve bu depo GitHub bağlantısında 404; \`madsc-tv/CALISANLAR.m3u\` dosyasının İBO'nun gerçekten kullandığı dosya olduğu doğrulanmadı. **Asıl İBO listesi değiştirilmedi**. V2 listesiyle eşitleme hâlâ açık iştir.\n- \`v2/test_playlist_invariants.py\` ve \`.github/workflows/v2-playlist-safety.yml\` eklendi. 1045+ kayıt, 8+ YEDEKLER, orijinal TRT 1/DHA ve YEDEKLER kategori sayacı korunmasını test eder. Workflow **başarılı**: run 40557969966, 1047 kanal, 2 yedek, 14 kategori, 3 kaynak.\n- Resmî site alias test hatası düzeltildi; başarılı tekrar run: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/40557210310\n\n## Yeni eklenen gerçek İBO kontrolü\n- \`v2/ibo_parity.py\` ve günlük \`.github/workflows/v2-ibo-parity.yml\` eklendi. Kullanıcının verdiği **tam raw İBO URL'sini** HTTP üzerinden okuyup V2 ile SHA-256, kanal sayısı, eksik eski URL'ler ve yeni aday isimlerini karşılaştırır; **hiçbir dosyayı değiştirmez**.\n- İlk iş akışı **başarılı çalıştı** (run 40558519460) ancak sonuç **IBO_URL_UNREACHABLE**; V2 1047 kayıt, asıl İBO içeriği okunamadı. İBO raw URL 404/erişilemez ise raporda açıkça \`IBO_URL_UNREACHABLE\` olarak belirtilecek; V2'nin üretimle eşit olduğu iddia edilmeyecek.\n- Açık işler: İBO bağlantısına yazma yetkisi/doğru repo, gerçek İBO Player oynatım testi, YouTube canlı metadata 0 sonucunu iyileştirme ve resmî site akışlarının doğrulanması.\n\n## Sonraki sohbet için çalışma şekli
- Önce bu **tek dosyayı** oku; güncel GitHub Actions ve playlist sayımını kontrol et.
- Sonra açık işlerden en yüksek öncelikliyi gerçekten uygula; başarısını somut commit/run/çıktıyla doğrula.
- Başarıyla tamamlananları yukarı taşı, açık işleri güncelle. **Başka DEVAM, RAPOR, DEVİR veya NOT dosyası açma.**
- Kullanıcıyı GitHub'da elle işlem yapmaya yönlendirme; mevcut yetkilerle doğrudan çalış. Test edilmemiş işi bitmiş gibi anlatma.

## Son kullanıcı kararı — öncelikli ve geçerli
- YEDEKLER'de **yalnızca TRT 1 1440P QHD ve DHA CANLI 720P HD** tutulacak. TRT Arabi ve TRT World istenmiyor; yeniden ekleme.
- Aras TV, Haber61 TV, TV Den, YOL TV **YEREL ve HEPSİ** içinde bulunacak; YEDEKLER'e geri taşınmayacak.
- V2 son sayım: **1047 kayıt, 14 kategori, YEDEKLER 2, YEREL 74, HEPSİ 378**. Koruma testi yeni kurala uyarlandı; GitHub Actions sonucu doğrulanacak.
- Asıl İBO raw URL'sine erişim hâlâ doğrulanmadı; bu değişiklik yalnızca V2 reposuna işlendi.

## Son çalışma — üretim bağlantısı güvenliği
- `v2/ibo_parity.py` erişilemeyen kanonik İBO URL'si durumunda `Madsc55/madsc-tv/CALISANLAR.m3u` dosyasını **yalnızca tanı amaçlı referans** olarak okur ve ayrı raporlar; bu dosyanın İBO'nun gerçek kaynağı olduğu **iddia edilmez**. Commit `8c6429aad2698f9497d0ebff2e0105af8dd21f64`.
- V2 kullanıcı kararı geçerli: **1047 kayıt, YEDEKLER 2, YEREL 74, HEPSİ 378**. Test run `40559428314` başarılı.
- Kanonik İBO raw URL erişim sorunu ve gerçek IBO Player oynatım doğrulaması açık; üretime otomatik aktarım yapılmadı.

## Yeni ilerleme — kullanıcıdan oynatım testi beklemeden
- Kanonik İBO karşılaştırma workflow'u `40560009239` **success**; fakat içerik sonucu **IBO_URL_UNREACHABLE**. Bu, otomasyonun düzgün çalıştığını gösterir, gerçek IBO içeriğini doğrulamaz.
- `v2/test_playlist_invariants.py` artık sadece YEDEKLER'i değil **14 kategorinin tamamının** parantez içindeki sayacını gerçek kayıt sayısıyla doğrular. Commit `b1fd24b79c20514404ddcccb1824acd586b67e95`; CI sonucu kontrol edilecek.
- Kullanıcı yeni kanalların İBO Player'daki oynatımına **daha sonra kendisi bakacak**. Bu konuda tekrar tekrar soru sorma; kanal keşfi ve otomatik testlerle ilerle. Canlı IBO playlistine erişim yokken değiştirme.

## Son ilerleme — yeni kaynak keşfi
- 14 kategori sayacı güvenlik testi **başarılı**, run `40560761225`: 1047 kanal kaydı, 2 yedek, 14 kategori, 3 keşif kaynağı.
- `v2/turkish_stream_catalog.py` ve `.github/workflows/v2-turkish-stream-catalog.yml` eklendi. IPTV-org **streams.json** içinden TR kanal kimlikli doğrudan yayın adaylarını toplar, V2'de zaten olan URL'leri ayıklar, eşleşen kanal kimliklerini işaretler ve **salt-okunur** JSON artifact üretir. Haftada iki kez otomatik çalışır; DRM veya erişim kısıtlaması aşmaz; kullanıcı onayı ve oynatım doğrulaması olmadan playlist değiştirmez.
- İlk workflow sonucu kontrol edilecek. İBO Player'daki oynatım kontrolünü kullanıcı daha sonra kendisi yapacak.

## Son keşif sonucu
- Türk yayın API keşfi ilk workflow **başarılı**: run `40561001771`, V2'de bulunmayan **115 URL adayı**, mevcut playlist 1047 kayıt. Bunlar 115 doğrulanmış yeni kanal değildir.
- Keşif filtresi TRT Arabi ve TRT World'ü kullanıcı isteğine göre hariç tutacak şekilde güncellendi. Mevcut kanal için alternatif yayın ile yeni kanal adayları ayrı sınıflandırılır; özel HTTP header gerektiren yayınlar otomatik aday yapılmaz. Commit `84243be09c64b88279219d08e2431c506ed0bb4b`; yeni test sonucu kontrol edilecek.
- İBO Player oynatım kontrolünü kullanıcı daha sonra yapacak; bu konuyla kullanıcıyı tekrar tekrar meşgul etme.

## HTTP başlığına ihtiyaç duyan adaylar
- İlk yeni keşif 115 URL adayı; sıkı filtreli ikinci çalışma `40561936686` başarılı, **101 normal URL adayı** buldu. Farkın tümü yalnızca HTTP header kaynaklı kabul edilmemeli; diğer filtreler de değişti.
- `v2/turkish_stream_catalog.py` güncellendi: `http_referrer` veya `user_agent` isteyen yayınları sessizce atmak yerine `header_required_review` adlı **ayrı salt-okunur rapor bölümünde** tutar. Bunlar otomatik playlist aktarımına girmez. Commit `20f6a29be4c14d696bc3c048f7bdee0060cc883a`.
- Hiçbir mevcut kanal, YEDEKLER, kategori, EPG veya İBO bağlantısı değiştirilmedi.

## Yeni aday doğrulama aşaması
- Run `40562287679` **success**: **101 normal URL adayı + 11 HTTP header gerektiren ayrı inceleme adayı**, V2 1047 kayıt. Bunlar ayrı URL adaylarıdır, kesin yeni/çalışan kanal sayısı değildir.
- `v2/turkish_stream_probe.py` ve `.github/workflows/v2-turkish-stream-probe.yml` eklendi. En fazla 120 normal adayı 8 eşzamanlı istekle 8 saniyelik timeout ve en fazla 4096 bayt örnekle salt-okunur HTTP/media işareti testine sokar; sonuçlar artifact olarak saklanır. Header isteyen 11 aday ayrı tutulur. HTTP başarısı gerçek uzun süreli oynatım kanıtı değildir.
- Hiçbir İBO/V2 playlistine otomatik aktarım yapılmaz; gerçek IBO Player testi kullanıcıya bırakılmıştır.

## Yayın adaylarının teknik doğrulaması
- HTTP probe run `40562872598` **success**: 101 normal adaydan 18 `HTTP_RESPONSIVE_MEDIA_HINT`, 1 `HTTP_RESPONSIVE_UNVERIFIED`, 82 `UNREACHABLE`; 11 header bağımlı aday ayrı tutuldu. HTTP medya işareti oynatım garantisi değildir.
- `v2/turkish_stream_decode.py` ve `.github/workflows/v2-turkish-stream-decode.yml` eklendi: HTTP medya işareti veren en fazla 24 adaya 13 saniye sınırında `ffprobe` kısa ses/video codec doğrulaması. Haftada iki kez, salt-okunur; sonuçlar artifact. İlk çalışma henüz doğrulanacak.
- İBO ve V2 playlistleri değişmedi; kullanıcı İBO oynatımını daha sonra kontrol edecek.

## Kısa çözümleme sonucu ve aday inceleme
- `40563554096` başarılı: bu çalışmada **19 HTTP medya işareti**, **11 kısa ffprobe doğrulaması**; 8 aday kısa çözümlemeden geçemedi. Bunlar kanal sayısı değil URL/akış denemeleridir; uzun süreli İBO oynatımı doğrulanmadı.
- `v2/turkish_stream_review.py` ve `.github/workflows/v2-turkish-stream-review.yml` eklendi: kısa çözümlenmiş adayları mevcut kanal alternatifi / yeni kanal adayı olarak etiketleyip **salt-okunur manuel inceleme kuyruğuna** yazar. Aynı kanal kimliğiyle birden fazla URL olabileceğinden otomatik aktarım yapılmaz. İlk test sonucu ayrıca kontrol edilecek.
- İBO Player kullanıcı kontrolü ertelendi; canlı playlist, kategoriler ve iki yedek değişmedi.

## Tek seferde otomatik keşif zinciri
- `.github/workflows/v2-turkish-stream-review.yml` artık **V2 Turkish Stream End-to-End Discovery** adını taşır: tek çalışmada **aday kataloğu → HTTP probe → kısa ffprobe çözümleme → inceleme kuyruğu → artifact**. Elle veya haftada iki kez zamanlanmış tetiklenir. Kod değişikliklerinde de tetiklenir.
- Önceki ayrı workflow'lar hâlâ mevcuttur; birleşik workflow aynı işlemleri tek çalışmada tamamlayabilir. Tüm keşif türlerinin (YouTube, resmî siteler vb.) birleştiği iddia edilmez. Hiçbir canlı playlisti otomatik değiştirmez.
- Commit `3a80383af8dcec01a7e751fa55898693391440cd`; yeni birleşik CI sonucu kontrol edilecek.

## Birleşik keşif — EPG ve logolar
- `.github/workflows/v2-turkish-stream-review.yml` tek çalışmada katalog → HTTP → ffprobe → aday inceleme → **mevcut playlist EPG XMLTV bütünlüğü** (`v2/epg_integrity.py`) → **logo/EPG URL erişimi** (`v2/assets_health.py`) → **logo formatı/kaynak incelemesi** (`v2/logo_attribution.py`) → artifact yapar. Commit `7a47b32ecd10f5e42b04fa0330bedae1b45882be`.
- Bu denetimler mevcut playlist EPG/logo sağlığını ölçer; yeni adaylar için doğru logo veya tvg-id eşleştirmesi **henüz otomatik yapılmıyor**. Playlist otomatik değiştirilmez.

## Bağımsız M3U kaynakları ve kanal çakışmaları
- `v2/config/sources.json`: üç iptv-org diliminden farklı olarak `Free-TV/IPTV` ve `omerdenizhan/IPTV-M3U` Türkiye listesi eklendi. Artık 5 M3U kaynağı; bağımsız kökenler karıştırılmamalı. Her kaynak salt-okunur ve erişim hataları raporlanır.
- Birleşik `.github/workflows/v2-turkish-stream-review.yml` artık `python v2/discover.py` ile tüm M3U kaynaklarını tarar ve `python v2/stream_url_collisions.py` ile mevcut V2 playlistinde **aynı URL'nin farklı kanal kimliklerine bağlanmasını** kontrol eder. Aynı kanalın farklı kategorilerde tekrar görünmesi ayrı sınıflandırılır. URL'ler raporda SHA-256 olarak saklanır.
- Sınırlama: aynı içeriği farklı URL'lerde sunan akışların video-fingerprint eşitliği henüz doğrulanmıyor. Yeni adayların EPG/logo eşleştirmesi henüz otomatik değil. İBO playlisti korunur.

## Kullanıcı önerisi — yeni kaynak incelemesi
- `discevisita/hayatiptv` içindeki `TRDECesitlikanallar.m3u` ve `ilyswch/IPTV-TR` içindeki `box.m3u` **salt-okunur kaynak** olarak `v2/config/sources.json` dosyasına eklendi. Bulunan URL'ler otomatik playlist'e alınmaz.
- `ramazansancar/UzunMuhalefet_Legal-IPTV` incelendi: doğrudan standart M3U dosyası yerine `lists/video/sources` ağacı bulunuyor; uygun güvenli kaynak formatı ayrıntılı incelenmeden otomatik çalıştırılmayacak.
- `MohamedAminGrami/IPTV-SCRAPPER` Python kod projesi; üçüncü taraf kodu incelemeden CI'da çalıştırılmayacak. Kaynak üretim mantığı ayrı güvenlik/izin değerlendirmesi gerektirir.

## 27 Ekim 2026 — Kalite doğrulama düzeltmeleri
- `v2/turkish_stream_decode.py` artık ffprobe gerçek video width/height, codec, bitrate alanlarını ve **test edilen URL'yi** raporlar.
- `v2/turkish_stream_review.py` yalnızca aynı kanal kimliği **ve aynı URL** için doğrulama eşler; kardeş URL'leri yanlışlıkla doğrulanmış saymaz, `measured_max_height` ekler.
- `v2/discover.py` mevcut kanal kimliğine ait farklı URL'leri artık atmaz, `existing_channel_alternative` ile işaretler. Yine salt-okunur, kaynak raporunda URL hash tutulur.
- Birleşik workflow keşif/kalite betiklerini derleme kontrolüne aldı. Gerçek çözünürlüğün **mevcut playlist yayınına karşı** ölçülmüş otomatik yükseltme kararı, görüntü fingerprint, yeni aday EPG/logo eşleştirme ve resmî site/YouTube adımlarının tek workflow'da birleştirilmesi hâlâ açık işlerdir. Test sonucu doğrulanmadan tamamlandı denmemeli.

## 27 Ekim 2026 — Birleşik arama son eklemeler
- Resmî TV sitesi keşfi ve YouTube canlı yayın keşfi tek V2 Turkish Stream End-to-End Discovery workflow'una dahil edildi. Önceki birleşik run 40572810092 SUCCESS.
- FFprobe sonuçları kalite raporuna URL+kanal kimliği eşleşmesiyle katılıyor; **mevcut playlist yayını gerçek çözünürlüğü henüz karşılaştırılmıyor**.
- `v2/candidate_assets.py`: aday tvg-id değerini mevcut playlist ile birebir eşleyerek EPG ID ve logo **önerisi** çıkarıyor; bağımsız doğrulama değil.
- `v2/frame_collisions.py`: kısa video örneklerinin tek kare hash eşleşmesiyle olası aynı görüntüleri işaretliyor; kesin yayın kimliği veya zamana yayılmış karşılaştırma değil.
- Her iki yeni rapor birleşik workflow artifact'ına eklendi. Yeni run 40574958656 sonucunu doğrula; başarısızsa düzelt. Canlı IBO, FAVORİLER, kategoriler ve iki yedek değişmedi.

## 27 Ekim 2026 — Mevcut yayınların gerçek çözünürlük karşılaştırması
- Birleşik run 40574958656 SUCCESS.
- `v2/current_stream_resolution.py` mevcut playlistten en fazla 24 farklı tvg-id için ffprobe ile gerçek video yüksekliği örnekler; sonuç `current-stream-resolution.json`.
- `v2/quality_upgrades.py` aday ffprobe ölçümlerini mevcut yayının ölçülmüş yüksekliğiyle tvg-id temelinde kıyaslayıp `MEASURED_CANDIDATE_HIGHER`, `MEASURED_NO_UPGRADE` veya `INSUFFICIENT_MEASUREMENTS` olarak raporlar.
- Bu yalnızca örneklenmiş kanallarda tek kısa ölçüm; tüm 1047 girdinin kapsamlı kalite/stabilite veya içerik kimliği onayı değildir. `frame_collisions.py` tek karelik olası tekrar tespiti de kesin doğrulama değildir. Canlı IBO ve yedekler değişmedi.
- Yeni workflow run 40575609850 doğrulanmalı.

## 27 Ekim 2026 — Aday öncelikli mevcut yayın ölçümü ve üç kare örneği
- Run 40575609850 SUCCESS (birleşik keşif ve ölçüm).
- `current_stream_resolution.py` artık mevcut playlistte alternatifi keşfedilen tvg-id değerlerini önceleyerek en fazla 120 farklı kanalı örnekler; tüm playlistin otomatik doğrulandığı anlamına gelmez.
- `frame_collisions.py` tek kare yerine üç örnek kareden ham video hash'i üretir; zaman kayması ve içerik eşitliği kesin tespit edilmez.
- Yeni run 40576629287 henüz doğrulanmalı. Otomatik yayın değiştirme kapalı, canlı IBO/favoriler/yedekler korunur.

## 27 Ekim 2026 — Kanallar arası görüntü çakışması raporu
- Run 40576629287 SUCCESS.
- `frame_collisions.py` 32 kısa decode adayını örnekleyebilir; eşleşen üç-kare hash'lerinde `channel_ids` ve `cross_channel_identity_risk` alanlarını verir. Yalnızca olası çakışma işareti, kesin kanal kimliği değildir.
- Yeni workflow run 40577598333 doğrulanmalı. Uzun süreli stabilite/çok zamanlı içerik doğrulaması ve 1047 kanalın tümünün ölçümü hâlâ kapsam dışı. Canlı IBO, favoriler, kategoriler ve iki orijinal yedek korunur.

## 27 Ekim 2026 — Sözdizimi hata düzeltmesi
- Run 40577598333 FAILURE: `Validate scripts` aşamasında `v2/frame_collisions.py` içinde literal `\\n` karakterleri SyntaxError üretti. `e20f462` commit'iyle gerçek satır sonlarına dönüştürüldü.
- Düzeltme run 40578459621 sonucu kontrol edilmeli; henüz başarılı ilan edilmedi.
- Mevcut yayın örnekleme önceliği alternatif tvg-id'ler üzerinden en fazla 120 ile sınırlandırılmıştır. Tam 1047 kanal ve uzun dönem yayın kararlılığı testi henüz bitmedi.

## 27 Ekim 2026 — Düzeltme doğrulandı, mevcut yayın örneklemesi genişletildi
- 40578459621 ve 40578503591 birleşik workflow çalıştırmaları SUCCESS; `frame_collisions.py` SyntaxError giderildi.
- `current_stream_resolution.py` önce alternatifi bulunan kanal kimliklerini seçiyor, 120'lik sınırda yer kalırsa diğer kanallarla dolduruyor; tüm 1047 kanalın doğrulandığı anlamına gelmez.
- Yeni test run 40579224508 bekleniyor. Canlı IBO ve yedekler değiştirilmedi.

## 27 Ekim 2026 — Toplu mevcut yayın ölçümü
- Run 40579224508 SUCCESS.
- `current_stream_resolution.py` artık `--batch` ve `--batch-size` destekliyor; birleşik workflow 10 x 120 ayrı kanal kimliği ölçümünü sırayla yürütüp JSON sonuçlarını birleştiriyor (en fazla 1200 distinct tvg-id; 1047 playlist girdisiyle aynı kavram değildir).
- Bütün kanalların ölçülebilir olması garanti değil; kısa ffprobe erişim testi uzun dönem kararlılık veya kanal içerik kimliği kanıtı değildir.
- Workflow timeout 65 dakika. Yeni Actions sonuçları doğrulanmalı. Canlı IBO, favoriler ve yedekler değişmedi.

## 27 Ekim 2026 — Tek çalıştırmada toplu doğrulama
- Ana `v2-turkish-stream-review.yml` workflow'una `stream_stability.py` (32 aday, 3 HTTP örneklemesi, 90 saniye aralık) ve son `test_playlist_invariants.py` güvenlik kapısı eklendi. 10 x 120 mevcut yayın çözünürlük grubu, ffprobe aday ölçümü, 3 kare olası çakışma, EPG/logo ve resmî/YouTube keşfi aynı workflow'da.
- Bu **gerçek 24 saatlik kararlılık veya kesin kanal kimliği doğrulaması değildir**; ayrı zamanlanmış gözlemler ve manuel kanıt gerekir. Workflow başarılı olsa bile tüm 1047 playlist girdisinin kararlı olduğu iddia edilmemeli.
- Yeni run 40582406848 sonucunu kontrol et. Canlı IBO/favoriler/yedekler değişmedi.

## 27 Ekim 2026 — Tek final rapor kapısı
- Birleşik altı alanlı test run 40582406848 SUCCESS.
- `v2/final_validation_summary.py` bütün ana JSON kanıtlarını toplayıp `v2/reports/final-validation-summary.json` üretir; eksik rapor varsa workflow başarısız olur. Sayılar, 24 saatlik kararlılık veya kesin kanal kimliği kanıtı olarak yorumlanmaz.
- Son rapor ana workflow'a zorunlu adım olarak eklendi. Yeni run 40584261821 sonucunu kontrol et. Canlı IBO ve yedekler değişmedi.

## 27 Ekim 2026 — NewlistTR ayrı doğrulanmış yayın çıktısı
- `v2/newlisttr_extract.py` doğrudan akan1970 NewlistTR M3U kaynağını okur, farklı URL'leri HTTP ve kısa ffprobe ile sınar; kısa video çözümlenebilenleri `v2/reports/newlisttr-decoded-only.m3u8` dosyasına yazar. Bu dosya yalnızca GitHub Actions artifact'ıdır, canlı IBO listesine otomatik eklenmez.
- `newlisttr-check.json` test kapsamı, başarısızlar ve ölçülen çözünürlükleri URL hash'leriyle kaydeder. 600 URL sınırı vardır; kalanlar varsa açıkça `remaining_untested` olarak gösterilir.
- Final kanıt raporuna NewlistTR kaynak, test, decode ve test edilmemiş sayı alanları eklendi. 24 saatlik kararlılık, kesin kanal kimliği ve logo/EPG doğruluğu kısa ffprobe ile kanıtlanmaz.


## 29 Ekim 2026 — SABİT BİTİŞ SÖZLEŞMESİ (yeni sohbetlerde de geçerli)
Kullanıcı kararı: Yeni özellikler icat ederek işi uzatma; mevcut eksikleri topluca kapat, tek birleşik workflow ile test et ve kabul koşulları karşılanınca projeyi tamamlandı ilan et.

### Dört değişmez kabul koşulu
1. Türkçe yayın adayları keşfedilir; çalışırlık ve **gerçek konuşma dili** kanıtı açıkça doğrulanır. Metadata, ülke kodu, video decode veya ses varlığı tek başına Türkçe kanıtı değildir. Kanıtlanmayan adaylar onaylanmaz.
2. Onaya aday yayınların kanal kimliği, görüntü/ses, kalite, EPG ve logo kanıtları gözden geçirilir; eksik veya şüpheli olanlar karantinada kalır. İnceleme bekleyen tüm internet yayınlarının sıfırlanması değil, **yayına alınacakların** güvenli kabulü esastır.
3. Canlı `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` Git blob hash `4b1c3cea4b5107a425abab60f62d41f9f81e05a7`, FAVORİLER, 13 kategori, TRT 1 1440P QHD ve DHA CANLI 720P HD daimi yedekleri korunur; kullanıcı onayı olmadan otomatik yayın yapılmaz.
4. `.github/workflows/v2-turkish-stream-review.yml` **tek birleşik final testi** başarıyla tamamlanır, final raporları incelenir ve kabul şartları karşılanır. Sonra "MADSC TV TAMAMLANDI" denir. Yeni bağımsız proje aşamaları açılmaz; zamanla bozulan internet yayınları bakım kapsamındadır.

### Kapanışa kadar uygulanacak sıra
- Var olan birleşik workflow'u yeniden tasarlama veya gereksiz tekrar taraması yapma. Önce en son çalışmanın gerçek run ID, job sonuçları ve `turkish-stream-review` artifact raporunu incele.
- Açık gerçek eksikleri tek listede sınıflandır: Türkçe ses kanıtı; kanal kimliği/çakışmalar; oynatma ve ses; EPG/logo/kalite; test/rapor tutarlılığı.
- Mümkün olan düzeltmeleri toplu uygula; ucuz çevrimdışı testleri önce çalıştır, pahalı tek birleşik taramayı en sonda bir kez başlat.
- Kanıtlanamayanları doğrulanmış diye gösterme. Güvenli inceleme kuyruğuna al; kullanıcıya her küçük değişiklik için yeni test yaptırma.

### Doğrulanmış ve doğrulanmamış durum
- Önceki #66 birleşik test kullanıcı ekran görüntüsüne göre SUCCESS; 32 playback işi, 68 artifact. #66 son commitlerin testi değildir.
- Eski run `40758418496` için GitHub API'den ilk sayfada 30/30 job SUCCESS ve 52 artifact görüldü; bu run yeni son test olarak sunulmaz.
- Son kod değişiklikleri: `73f9e1b` ses kanıtı ayrımı; `d2f0fb1` çevrimdışı güvenlik sözleşmesi; `a015741` bu sözleşmeyi birleşik workflow'un ilk kapısına bağladı. Bu commitlerin yeşil sonucu henüz doğrulanmadı.
- `v2/turkish_language_evidence.py` henüz ASR veya gerçek konuşma dili sınıflandırması yapmıyor; `spoken_turkish_verified=0`, otomatik onay 0. Bunu bitmiş sayma.
- Güncel raporlar görülmeden yeni adayların gerçekten Türkçe, kimlikleri kesin, 24 saat kararlı veya yayıma hazır olduğu iddia edilmez.


## 29 Ekim 2026 — TOPLU TEST SONUCU VE KALAN İŞLER
- En son tam birleşik kanal taraması: #72, run 40948768782, SUCCESS. Rapor: 13.518 aday, 7.254 VIDEO_DECODED, 6.264 diğer, 46 kaynak; gerçek Türkçe konuşma doğrulaması 0. Bu başarı kanal onayı değildir.
- Birleşik kısa çevrimdışı test: `.github/workflows/v2-one-shot-final-contract.yml`, run 40965143233, SUCCESS. Python derleme, IBO/yedek bütünlüğü, güvenlik sözleşmesi, dil davranış fixture testleri, ses örnekleyici CLI kontrolü aynı çalışmada geçti.
- Yeni `v2/spoken_language_sample_review.py` ses örneklerinden ASR dil ipucu çıkarma için eklendi; bağımsız gerçek akışta henüz çalıştırılmadı ve bütün adayları kapsamaz. Çıktı hiçbir kanalı onaylamaz/yayımlamaz.
- Değişmez dört bitiş şartı: (1) gerçek Türkçe konuşma kanıtı ve çalışan yayın, (2) terfi adayı için kimlik/video/ses/kalite/EPG/logo, belirsizleri karantina, (3) IBO/favoriler/13 kategori/2 yedek koruma, otomatik yayın yok, (4) tek toplu final test ve doğru rapor; sonra MADSC TV TAMAMLANDI. Beşinci şart yok.
- **Sıradaki işler:** (A) son #72 raporundan çalışan, kimliği makul adayların önceliklendirilmesi; (B) ses örnekleme ve ASR ipuçlarını mevcut inceleme raporuna güvenli biçimde entegre edip belirsizleri karantinada tutma; (C) sadece terfi düşünülen adayların yayıncı kimliği, kalite, EPG, logo ve gerçek IBO oynatım uygunluğunu doğrulama; (D) koruma testleriyle tek nihai bitiş kararı. Gerçek IBO cihaz oynatımı ve insan gerektiren dil/kimlik kanıtları yazılımın tek başına ispatlayamadığı hususlardır.
- Gereksiz 32-shard tam tarama tekrarları yapılmayacak. Toplu kısa test başarılı diye gerçek Türkçe doğrulandı veya proje bitti denmeyecek.


## 29 Ekim 2026 — #60 ve #72 gerçek karşılaştırması (güncel otoritatif durum)
- #60 başarılı run 40743765437: 27.047 benzersiz URL test edildi; 11.860 VIDEO_DECODED. #72 başarılı run 40948768782: 13.518 URL; 7.254 VIDEO_DECODED.
- İki gerçek aggregate artifact'ı karşılaştırıldı: 13.136 ortak URL SHA-256, 13.911 yalnızca #60'ta, 382 yalnızca #72'de; #60'ta VIDEO_DECODED olup #72'de bulunmayan **4.955** bağlantı. Bunlar #72'de test edilmedi; hâlâ çalıştığı veya Türkçe konuştuğu kanıtlanmadı.
- Büyük kaynak düşüşleri: iptv-org 11204 -> 9; github-auto-7 4931 -> 0; github-auto-8 1854 -> 1; free-tv-independent 1347 -> 5. Kaynak sayısı artmış olması aynı kapsama ulaşıldığını kanıtlamaz.
- Kod: `v2/compare_historical_playback.py` salt-okunur SHA-256 bazlı karşılaştırma; `.github/workflows/v2-historical-recovery.yml` mevcut #60/#72 artifact'larını indirip tek seferde anonim CSV+JSON üretir. Workflow run 40968303248; tamamlanma sonucu kontrol edilecek. Tam 32-shard canlı taramayı tekrar çalıştırmaz.
- Öncelikli açık iş: 4.955 geçmişte görüntüsü çözülmüş bağlantının **güncel canlı durumunu** ve Türkçe sesini izinli/korumalı ortamda yeniden test etmek. Eski #60 artifact'ında özel URL snapshot'ı bulunmuyor; SHA-256'dan URL geri çıkarılamaz. Kaynak kapsamındaki düşüşün nedenini ayrıca kaynak düzeyinde teşhis et. Eksik kanalları onaysız üretime ekleme.
- Son başarılı konuşma örnekleme run 40966389885; 16 deneme, 14 analiz, 6 Türkçe model ipucu; 0 doğrulanmış kanal.
- Korunan V2 playlist: 840 kayıt, 13 kategori, YEDEKLER'de 2 orijinal kanal; bu çalışma playlist'i değiştirmedi. Yukarıdaki eski 1047/14 kategori notları tarihsel ve güncel değildir.


## 30 Ekim 2026 — Kullanıcı kararı: 27.429 benzersiz yayın kimliğini koru
- #60: 27.047 URL, #72: 13.518 URL, ortak SHA-256: 13.136; birleşim: **27.429 benzersiz yayın URL kimliği** (27.047 + 13.518 - 13.136). Bu **27.429 farklı veya çalışan Türk TV kanalı değildir**; aynı kanalın birden çok URL'si olabilir.
- Eskiye özgü 13.911, yeniye özgü 382 URL kimliği vardır. Eski #60'ta VIDEO_DECODED olup #72'de olmayan 4.955 kurtarma adayı bulunur. Bunlar güncel çalışır/Türkçe doğrulanmış sayılmaz.
- Kullanıcı kendi player'ında oynatım testlerini kendisi yapacak; kullanıcıdan her aşamada tekrar player testi isteme. Otomatik keşif, kaynak teşhisi, mevcut güvenli ses/oynatım kontrolleri ve toplu testler sürdürülebilir.
- **Saklama gerçeği:** Tarihsel raporlar anonim URL SHA-256 kimliklerini saklar; 27.429 URL'nin tamamının açık metin adresleri elde değildir. SHA-256'dan adres türetme iddiasında bulunma. Yeniden keşfedilen adresleri yalnızca izinli, güvenli ve erişim sınırlarına uygun şekilde işle; token/özel URL'leri açık GitHub raporuna koyma.
- Mevcut IBO, favoriler, kategori düzeni ve iki orijinal YEDEKLER kanalı korunacak. Otomatik üretime alma yok; doğrulanmayan adayları karantinada tut.
- Teşhis: `v2/rediscover_historical_candidates.py` yalnızca `sources.json` sabit kaynaklarını okuyor; `discover.py` ise mevcutsa `github-source-discovery.json` dinamik kaynaklarını da kullanıyor. Bu kapsam farkını güvenli biçimde gider; eski kaynak kaybının nedenlerini audit ile ayır. Tam 32-shard taramayı gereksiz yere yeniden çalıştırma.
- Son kurtarma raporunun `rediscovered_count` ve `still_unmatched` değerleri henüz okunup doğrulanmadı. Yeni başarı rakamı uydurma.


## ANA TARAMA BITINCE YAPILACAK: Kalici kanal hafizasi ve kademeli IBO Player testi (30 Ekim 2026)

Kullanici tarafindan onaylanan sonraki calisma plani; **ana toplu Turkce kanal taramasi tamamlandiktan sonra** uygulanacak. Bu bolum bir uygulama tamamlandi iddiasi degildir.

1. Tarama sonucu bulunan tum adaylarin gercek oynatilabilir URL'lerini, adlarini, kaynaklarini, TVG-ID ve URL kimliklerini, ulke/dil ipuclarini **guvenli, kalici ve geri yuklenebilir** ana havuzda tut. Su anki 1 gunluk private playback snapshot ve yalnizca SHA256 iceren aday raporu bunun icin yeterli degil. Kimlik bilgisi/token iceren URL'leri acik repoya koyma; saklama/erisim politikasi belirle.
2. Tekrarlari ayikla, sabit aday kimlikleri ve deterministik siralama olustur; taramalar arasi kaybolmasin. 1000'lik (istege gore 1500'luk) M3U deneme partileri uret; parti numarasi, aralik, test durumu ve son kalinan konumu kaydet.
3. Deneme partilerini mevcut IBO ana playlist, favoriler, kategoriler ve iki orijinal YEDEKLER kaydina dokunmadan **ayri gecici test listeleri** olarak hazirla. Kullanici kendi IBO Player'inda kanallari tek tek dener; otomatik playback testleri kullanici kararinin yerini almaz.
4. Her aday icin kullanicinin karari kalici olarak kaydedilsin: CALISAN_TURKCE, CALISMIYOR, YABANCI_DIL, KARARSIZ, HENUZ_TEST_EDILMEDI. Ayrica kanal adi, kaynak/ulke, yayin dili, URL kimligi, TVG-ID, son test tarihi, parti numarasi ve kullanici notu tutulabilsin. Kaynak ulkesi yayin dili kaniti degildir.
5. Onayli calisan Turkce kanallari ayri koru. Test edilen calismayan/yabanci adresleri sonraki kullanici test partilerinden ayir; yeni taramalarda ayni URL veya ayni kanalin alternatiflerini tani. Calismayanlari sonsuza kadar engelleme: yeniden deneme tarihi/manuel sifirlama imkani sagla.
6. Bir parti tamamlandiginda kullanici onayi ile gecici test listesini temizle ve siradaki 1000/1500 adayi hazirla. Kayitlar, onaylar ve parti sirasi kesinlikle silinmesin. Yeni sohbetlerde DEVAM_NOTU.md ve durum dosyalarindan ayni noktadan devam edilebilsin.
7. Kabul testleri: 27.500 ornek adayda 28 x 1000'lik parti; tekrar aday yok; yeniden tarama kullanici kararlarini silmez; ayni kanal farkli URL'den gelirse alternatif olarak iliskilendirilir; bir parti geri alinip yeniden acilabilir; ana IBO ve iki yedek degismez. 27.500 sayisi varsayimsal ornektir, dogrulanmis mevcut sayi degildir.

**Oncelik:** Ana kanal taramasinin sonucu alindiktan sonra bu plani ilk siraya koy. Kullaniciya tarama bitince bu plani hatirlat; sonraki calismaya buradan basla.


## DEGISMEZ KURAL: Bulunan hicbir kanal kaydi kaybolmayacak (30 Ekim 2026)

Kullanicinin acik ve yuksek oncelikli talebi: **Kesfedilen hicbir kanal/stream adayi, calismiyor, yabanci, Turkce degil, tekrar veya gecici olarak erisilemez diye veri tabanindan silinmeyecek.** Bulunan her adresin tarihi ve kaynaklari korunacak. Bu bir veri saklama gereksinimidir; mevcut uygulamanin bunu sagladigi iddia edilmez.

- Append-only/versiyonlu kalici aday arsivi: gercek URL (yetkili/guvenli erisimle), URL hash'i, kaynak M3U, gorulen kanal adi, tvg-id, grup, logo, kaynak ulke, yayin dili kaniti, ilk/son gorulme, tum tarama kimlikleri, gozlemler ve kullanici kararlari.
- Kanal kimligi ile stream URL kimligini ayri tut; ayni kanal birden fazla URL ile gelebilir, ayni URL farkli kaynaklarda gecse de kaynak iliskilerini kaybetme.
- Durumlar CALISAN_TURKCE / CALISMIYOR / YABANCI_DIL / KARARSIZ / HENUZ_TEST_EDILMEDI; tarihli, kaynakli karar gecmisi tut. Siniflandirma veri silme degildir.
- Yeni tarama mevcut kayitlari **birlesitirir**, asla onceki arsivi yeni snapshot ile degistirip eski kayitlari yok etmez. Yeni gorulmeyen aday 'bu taramada gorulmedi' diye isaretlenir; arsivden silinmez.
- Kalici URL depolamasi tek gunluk GitHub Actions artifact'ina veya SHA256'ya dayanmayacak. Yetkisiz/kimlik bilgili URL'leri acik repoya yazma; guvenli depolama, yedekleme, geri yukleme ve erisim kontrolu gerekli.
- Tum tarama adaylari kullaniciya 1000/1500'luk IBO test partileri olarak sunulabilecek; daha onceki parti ve test kararlari korunacak. IBO ana liste/favoriler/kategoriler/iki orijinal yedek korunacak.
- Kabul testleri: ard arda iki taramada toplam aday birlesimi korunuyor; bir aday silinse/erisilemez olsa bile arsivde; tum kararlar yeniden baslatma ve yeni sohbet sonrasi geri yukleniyor; yedekten gercek URL'lerle M3U parti yeniden uretilebiliyor; yetki bilgileri sizmiyor.

**Yapilacak:** Tarama sonucunun saklama suresi dolmadan mevcut URL snapshot'larini kurtarip kalici guvenli arsive alma mekanizmasini kurmak ilk teknik oncelik. Yalnizca not almak bu guvenceyi saglamaz.


## SONRAKI OTURUM: TEK TOPLU TAMAMLAMA PLANI (30 Ekim 2026)

Kullanici talimati: Kanal aramasini gelistirmek icin kalan butun isleri **ayri ayri testlerle oyalamadan, tek koordineli toplu calisma** halinde ele al. Su an ana taramanin bitmesi beklenecek. Bu bir yapildi iddiasi degil; siradaki uygulama ve kabul plani.

**A. Once gercek durum:** `v2-turkish-stream-review.yml` en son run ID/commit/sonuc, 32 shard ve review job durumu, taranan kaynaklar, benzersiz URL adaylari, oynatilan/video decoded, Turkce konusma kaniti, hatali kaynaklar, eksik raporlar ve onceki 27047 / 13518 / 27429 URL kimligi karsilastirmasini raporla. Yeni sayilari rapordan dogrula, 27429'u onayli Turk kanali olarak sunma.

**B. Kaynak kapsami ve kesif:** Dunyadaki Turkce yayin yapan kanallarin uluslararasi M3U kaynaklarinda bulunmasini hedefle. 17 sabit kaynak, GitHub dinamik kesif (10 sorgu, 150 repo/240 dosya siniri) ve diger resmi/yayinci/YouTube kesiflerinin gercekten ana taramaya baglandigini test et; limitleri ve API oran sinirlarini gozden gecir. Kaynak basarisizligi, filtreleme, istikrarsiz github-auto siralamasi, iptv-org 11204->9 ve github-auto kaynak kayiplari icin kok neden incelemesi yap. Kaynak ulkesi ile Turkce yayin kanitini karistirma. Eksikleri topluca duzelt.

**C. Tarihsel kurtarma:** Eski #60 ve #72 tarama kimlikleri, 4955 eksik onceki VIDEO_DECODED URL kimligi, v2-historical-recovery.yml ve dinamik kaynak entegrasyonunu denetle. Hash'ten URL geri cevrilemeyecegini kabul et; eski gercek URL'leri ancak hala erisilebilir guvenli artifact/kaynaklardan kurtar. Gercek kurtarilan URL sayisini ayrica raporla.

**D. Veri kaybini engelle:** Bir gunluk private snapshot ve sadece SHA256 raporu kalici arsiv degildir. Tum kesfedilen stream URL'leri, kaynaklar, gorulme tarihleri, metadata, URL hash'leri ve tarama kimliklerini guvenli, geri yuklenebilir, versiyonlu/append-only depolamaya al. Hassas token/kimlik bilgili URL'leri public repoya koyma. Yeni tarama eskileri silmesin. Arama sonucu kayitlarini saklama suresi dolmadan guvenli arsive aktarma kritik. Yedekleme/geri yukleme ve tekrar tarama kabul testleri yap.

**E. Kademeli IBO Player manuel test:** Kalici havuzdan sabit kimlikli, tekrar etmeyen 1000/1500'luk M3U partileri uret. Kullanici kendi player'inda test ederek CALISAN_TURKCE, CALISMIYOR, YABANCI_DIL, KARARSIZ, HENUZ_TEST_EDILMEDI olarak ayiracak; kararlari, tarihleri ve parti sirasi kalici kaydedilecek. Yeniden taramada onceden karar verilenleri tekrar yeni test partisine koyma, ama arsivden asla silme; calismayanlara gelecekte yeniden deneme imkani ver. Kanal ile URL kimligini ayri tut.

**F. Koruma ve toplu kabul:** Mevcut 840 girdili V2 IBO playlist, 13 kategori, favoriler ve iki orijinal YEDEKLER yayini korunacak; izinsiz otomatik yayinlama yok. Tek koordine CI/test turunda syntax/offline kontrat, kaynak kesif, tarihi kurtarma, snapshot arsivleme, shard playback, rapor birlestirme, 1000/1500 parti olusturma, tekrar/geri yukleme ve playlist invariants dogrulansin. Basarisiz adimlar icin net hata/kok neden/duzeltme ver; yeni testleri gereksiz yere tek tek kullaniciya yaptirma.

**G. Devir ve durum:** Her anlamli degisiklikten sonra bu DEVAM_NOTU.md'ye commit SHA, run ID, kesin sayilar, tamamlanan/kalan isler, sonraki tek adim ve veri koruma durumunu yaz. Sohbet hafizasina guvenme.

**Kabul:** Kullaniciya tamamlandi demeden once hem kaynak kapsami hem URL arsivi hem geri yukleme hem kademeli IBO parti ve durum hafizasi hem playlist korumasi testlerden gecmis olmali. Tarama bitene kadar bu yeni toplu isi baslatmak icin kullanicidan ekstra is isteme.


## KULLANICI GUNCEL PARTI BOYUTU: 2000 (30 Ekim 2026)

Kullanici son talimati: **Ana kanal taramasi tamamlandiktan sonra ilk 2000 bulunan adayi IBO Player'da manuel test edebilmek icin YEDEKLER/test alanina hazirla.** Daha once konusulan 1000/1500 varsayilaninin yerine **2000** esas alinsin. Kullanici calisan Turkce, calismayan ve yabanci kanallari sececek; sonuclari kalici kaydet, sonraki 2000'lik partiye gec, onceki partileri ve tum URL verisini asla kaybetme. **Mevcut iki orijinal YEDEKLER kaydini, IBO ana listeyi, favorileri ve kategorileri silme/ustune yazma**; gerekiyorsa ayri isimli gecici test yedegi/playlist uret ve kullaniciya yukleme seklini acikla. Yalnizca tarama bitince, gercek URL'lerin guvenli arsivden geri yuklenebildigi dogrulandiktan sonra parti dosyasini olustur. Kullanici test kararlarini otomatik playback sonucuyla degistirme.


## DUZELTME: 2000 ADAY AYRI PLAYLIST DEGIL ANA IBO YEDEKLER ICIN (30 Ekim 2026)

Kullanicinin kesin talimati: **Ayrica bir playlist VERME/URETME.** Ana playlist zaten kayitli: `https://raw.githubusercontent.com/Madsc55/Madsc55-Tv/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`. EPG: `https://madsc55.github.io/madsc-tv/madsc-epg.xml`. V2 gelistirme playlisti farkli depoda, asil IBO olarak varsayilmayacak. Tarama bitince 2000 aday **kullanicinin ana IBO playlistindeki YEDEKLER bolumunde** test icin isteniyor; baska URL/playlist onerme ve kullanicidan bu adresleri tekrar isteme. Mevcut iki orijinal YEDEKLER kanali TRT 1 1440P QHD ve DHA CANLI 720P HD silinmeyecek; favoriler, mevcut kategoriler ve EPG korunacak. Asil IBO adresine erisim/yazma yetkisi daha once 404 olarak raporlandi; erisim ve guvenli geri alma/backup olmadan asla degistirildi iddiasinda bulunma. Yetki saglanmadan kullanicinin talebini ayri playlist ile ikame etme. Eski notlardaki 'ayri gecici test listesi' onerisi kullanici tarafindan acikca reddedildi; bu son talimat gecerlidir.


## 30 Ekim 2026 - Kapsam genisletme uygulamasi (KISMEN TAMAMLANDI)
- `v2/discover.py`: Ayni URL farkli kaynaklarda goruldugunde `source_ids` ile tum kaynak kimlikleri kaydediliyor; ilk kaynak tekeline bagli raporlama azaltildi. Mevcut `source` alani uyumluluk icin korundu.
- `v2/config/sources.json`: Azerbaycan ulke/dil/akim, Turkce dil ve Avrupa/Asya bolgesel M3U listeleri eklendi. Kaynaklarin canli erisimi ve test sonucu henuz dogrulanmadi.
- `v2/github_source_discovery.py`: Turkce/Azerbaycanca/diaspora/ucretsiz IPTV GitHub arama sorgulari genisletildi; repo tarama siniri 240. API kotasi ve gercek kaynak kalitesi sinirlayabilir.
- ONEMLI EKSIKLER: GitLab/Codeberg benzeri platformlarin otomatik kaynak kesfi; resmî yayin siteleri ve YouTube canli yayinlarinin ana aday havuzuna guvenli ve dogrulanabilir entegrasyonu; Gunes TV, Rec TV, Gopik TV isimlerinin somut kanal/site eslestirmesi; #60 URL'lerinin kalici geri yuklenebilir arsivi; tek toplu CI sonucu ve son kaynak bazli karsilastirma. Bu isler tamamlandi diye raporlanmayacak.
- Kritik veri riski: Gercek stream URL'lerini saklayan ozel snapshot 1 gunluk artifact; kalici sifreli URL arsivi/geri yukleme HENUZ YOK. SHA256 tek basina URL kurtarmaz. Onceki tarama verileri korunmadan yenisi eskisinin yerine gecmis sayilmayacak.
- Ana IBO playlisti, iki orijinal YEDEKLER, favoriler, kategoriler, EPG degistirilmedi. Kullanicinin son istegi 2000 aday mevcut IBO YEDEKLER bolumunde, AYRI playlist yok. Kanonik IBO URL erisimi dogrulanmadan yazma yapma.


## 2026-10-30 YENI SOHBET DEVIR NOTU

Bu not, yeni sohbette devam icin son durumdur. Kullanici butun kararlarin korunmasini istiyor.

- Asil IBO playlist: https://raw.githubusercontent.com/Madsc55/Madsc55-Tv/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8 . EPG: https://madsc55.github.io/madsc-tv/madsc-epg.xml . V2 gelistirme playlisti farklidir. Asil URL daha once erisilemez gorundu; dogrulamadan degistirme. Kullaniciya adresi yeniden sorma.
- Kesin karar: ayri test playlisti yok. 2000 aday mevcut asil IBO YEDEKLER bolumunde test edilecek. Iki orijinal yedek TRT 1 1440P QHD ve DHA CANLI 720P HD, favoriler, kategoriler, EPG korunacak. V2 referans 840 giris ve 13 kategori.
- Bulunan her URL ve kaynak bilgisi kalici, guvenli ve geri yuklenebilir saklanmali. Calisan Turkce, calismiyor, yabanci dil, kararsiz, test edilmedi kararlarini kaydet; onaylanan/elenen kanallari sonraki partide tekrar sunma. Tokenli URL'leri acik depoda yayinlama. Bir gunluk ozel artifact kalici arsiv degildir.
- #60 run 40743765437: 27047 URL, 11860 VIDEO_DECODED, 42 kaynak. #74 run 40972785562: 13593 URL, 7306 VIDEO_DECODED, 68 kaynak. Raporlanan ortak URL kimligi 13179, yalniz #60 13868, yalniz #74 414. Bunlar kesin Turkce kanal sayilari degil. Kaynak sayiminda ilk-kaynak deduplikasyon etkisi var.
- Son kod commitleri: 7262458a, 6a6b685f, 332e854f, 0130133b, e42a076c, 1acecd9f, fad4442b. AZ/Turkce dil/Avrupa/Asya kaynaklari eklendi, GitHub sorgulari 20, repo limiti 240, source_ids izleme eklendi. Bunlarin yeni tam tarama sonucu henuz dogrulanmadi.
- Cok GitHub Actions isi gorulmesi normal olabilir: tek ana tarama 1 sources + 32 playback + 1 review = 34 job. Push tetikleyicileri birden fazla run baslatmis olabilir. concurrency group v2-turkish-stream-review-main, cancel-in-progress false. Yeni run kimlikleri ve durumlari henuz kontrol edilmedi; gereksiz kosular ve Actions kotasi incelenecek. Bilinen #74 basarili.
- Acik isler: GitLab ve diger kod barindirma platformlarinda IPTV kesfi; resmi canli TV ve YouTube canli yayin adaylarini ana havuza katma; Gunes TV/Rec TV/Gopik TV kaynaklarini dogrulama; #60 ve #74 kayip adaylarini kurtarma; kalici guvenli URL arsivi; 2000 adaylik YEDEKLER test uygulamasi; tek koordineli CI ve regresyon testleri. Yapilmamis isi tamamlandi diye bildirme.
- Yeni sohbet ilk adim: bu notu oku, son GitHub Actions run'larini kontrol et, sonra eksikleri topluca ele al. Kullaniciya eski bilgileri tekrar sordurma.


## 2026-10-30 EN SON KESIN DEVIR - V2 TEK HEDEF

KULLANICI DUZELTMESI: Butun aktif calisma yalnizca `Madsc55/MADSC55-TV-V2` deposunun `main` dalinda yapilacak. `Madsc55-Tv`, eski repo, eski IBO raw adresi ve diger projelere KULLANICI ACIKCA SOYLEMEDIKCE dokunma, yonlendirme yapma veya onlari aktif hedef olarak kabul etme. Onceki devir notlarindaki asil IBO'nun baska repo oldugu talimati bu is icin GECERSIZDIR. Aktif V2 playlisti: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`. V2 EPG, favoriler, kategoriler ve mevcut kanallar korunacak. Iki orijinal YEDEKLER TRT 1 1440P QHD ve DHA CANLI 720P HD silinmeyecek. Ayri playlist YOK. Manuel test partisi 2000 aday ve mevcut V2 playlistinin YEDEKLER bolumune eklenecek; guvenli backup, tekrar etmeme, kullanici kararlarini koruma ve izin/kabul testleri gereklidir.

Onceki tarama #60: 27047 URL, 11860 decoded, 42 kaynak; #74: 13593 URL, 7306 decoded, 68 kaynak. 13179 ortak hash, 13868 yalniz #60, 414 yalniz #74. Hash = Turkce kanal kaniti DEGIL. Kaynak sirasi/dedup kaynak bazli farklari etkileyebilir.

Bu sohbette V2 commitleri: 7262458a, 6a6b685f, 332e854f, 0130133b, e42a076c, 1acecd9f, fad4442b, 4c545474. AZ/Turkce dil/Avrupa/Asya kaynaklari, 20 GitHub sorgusu, 240 repo limiti, source_ids ve workflow tetikleyicileri eklendi. Yeni Actions testlerinin basari durumu dogrulanmis DEGIL.

Tek bir V2 ana taramasi 34 job (1 kaynak, 32 playback, 1 review) acabilir. Son kod degisiklikleri birden fazla run tetiklemis olabilir. Workflow concurrency `v2-turkish-stream-review-main`, `cancel-in-progress: false`, `queue: max`; dolayisiyla sirada bekleyen tekrarlar olabilir. Bilinen #74 eski basarili run; yeni run ID/status kontrolu henuz yapilmadi. Yeni sohbette ilk is Actions sayfasindan yeni run ID/status/job/hata kontrolu; basarili varsayma ve gereksiz taramalari ayirt et.

KALAN ISLER: GitLab/Codeberg/benzeri kaynak kesfi, resmi yayin siteleri ve YouTube adaylarinin ana havuza entegrasyonu, Gunes TV/Rec TV/Gopik TV dogrulamasi, tarihsel #60 URL kurtarma, tokenleri aciga cikarmayan kalici geri yuklenebilir URL arsivi, manuel karar hafizasi, 2000'lik V2 YEDEKLER partisi, toplu CI regresyon ve playlist degismezlik testi. Her URL'nin kaynaklarini ve tarihcesini koru; tekrar tarama eski veriyi silmesin. Yapilmayan isleri yapildi diye yazma. Kullaniciya daha once verdigi bilgileri tekrar sorma.

Bu kayit onceki tum hedef-repo referanslarindan ONCELIKLIDIR. Yeni sohbet yalnizca MADSC55-TV-V2 ile devam edecek.


## 2026-10-30 DEVAM - KAYNAK KESFI SIRALAMA DUZELTMESI
- Yalnizca V2 main dalinda `v2/github_source_discovery.py` degistirildi; commit `b113e9c7ff93198b2c82ed07f9a36f202ab5b7fd`.
- GitHub depolari ve depo ici M3U dosyalari casefold sirali seciliyor; bulunan kaynak raporu da sabit sirali yaziliyor. Amac: kaynak kesfi secimindeki degisken siralama etkisini azaltmak. GitHub API arama sonucunun ve kota/limitlerin kapsami hala degisebilir; #60 kayip URL kurtarma garantisi degildir.
- Ana V2 playlisti, YEDEKLER, EPG, kategoriler ve favoriler degistirilmedi. Bu commit sonrasi Actions testleri henuz dogrulanmadi; kullanici onceki testlerin yesil oldugunu bildirdi.
- KALAN: son Actions run ID/job/log kontrolu; eski #60 URL'lerini gercek adres olarak kurtarma; kalici guvenli geri yuklenebilir arsiv; GitLab/Codeberg ve resmi TV/YouTube kaynak entegrasyonu; 2000'lik mevcut V2 YEDEKLER testi; koordineli regresyon. Yeni test partisi hazir diye iddia etme.


## 2026-10-30 DEVAM - DINAMIK KAYNAK KIMLIGI
- V2 `v2/discover.py` icindeki `github-auto-<sira>` kimlikleri, kaynak URL'sinin SHA256 ilk 20 hex karakteri ile kararlı `github-auto-<hash>` kimligine cevrildi. Commit: `d438d2bb0142a40ee30438941fef0fbb1ddfd475`.
- Sebep: farkli taramalarda kaynak sirasi degisince ayni ID'nin baska M3U dosyasini gostermesini onlemek; #60/#74 kaynak karsilastirmasi ve provenance icin gerekli. Onceki raporlardaki sira tabanli ID'ler yeni hash ID'lerle birebir ayni degildir; eslestirme kaynak URL'sinden yapilmali.
- `get_commit_combined_status` sorgusu `b113e9c7` icin bos statuses dondu; bu, GitHub Actions basarisi veya basarisizligi kaniti DEGIL. Kullanici onceki testleri yesil bildirdi; yeni commitlerin run/job sonucunu kontrol etmek gerekiyor.
- Playlist/YEDEKLER/favoriler/kategoriler/EPG degismedi. Kalici URL arsivi, resmi/YouTube/GitLab/Codeberg entegrasyonu, 2000 aday testine gecis ve tarihsel URL kurtarma hala acik.


## 2026-10-30 DEVAM - OZEL SNAPSHOT KAYNAK PROVENANCE
- `v2/discover.py` icinde public-safe aday `source_ids` tekrarlarini engelleme ve private playback snapshot icinde her benzersiz URL icin tum kaynak ID'lerini `source_ids` ile koruma degisikligi yapildi. Commit `f6d564c3e3a07a01923935eb53f2bf24e0143edd`.
- Bu degisiklik mevcut `source` ilk-kaynak alanini korur, ayni URL'nin baska kaynaklarda gorulmesini private snapshot icinde kaybetmez. Kisa sureli snapshot'i kalici arsive DONUSTURMEZ; 1 gunluk artifact veri kaybi riski suruyor.
- Yeni commitin Actions sonuclari henüz dogrulanmadi; onceki yesil testler yeni commitin testi sayilamaz. Ana playlist/YEDEKLER/favoriler/kategoriler/EPG degistirilmedi.
- Acik kalan isler: son Actions run/job/log kontrolu, URL kalici guvenli arsiv ve restore testi, #60 eski URL kurtarma, GitLab/Codeberg, resmi site/YouTube ana kaynak entegrasyonu, 2000 V2 YEDEKLER manuel test akisi ve toplu kabul.


## 2026-10-30 DEVAM - KAYNAK PROVENANCE REGRESYON TESTI
- Yeni `v2/test_source_provenance.py` eklendi, commit `0ea36dfb1d2c8676b5b34be3e7b4dc9276e0a44f`: iki M3U kaynaginin ayni URL'si icin tek aday, iki `source_ids`, URL SHA256, kaynak sirasi degisimi ve mevcut playlist URL'sinin dislanmasi offline kontrol ediliyor.
- Birlesik `.github/workflows/v2-turkish-stream-review.yml` sources asamasina bu offline test eklendi; commit `40b294d06d1f2bd308db8ec0afe77f8f85b42991`. Yeni test dosyasi degisimi de workflow tetikleyicilerine eklendi. Ayrica ayri manuel test workflow'u acilmadi.
- Yeni commitler icin GitHub Actions gercek run sonucu henüz dogrulanmadi. Bu kayit testin yesil oldugu iddiasi degildir. V2 playlist, YEDEKLER, EPG, favoriler ve kategoriler degismedi.
- Kalan: kalici guvenli URL arsivi/restore, #60 gercek URL kurtarma, GitLab/Codeberg, resmi yayin/YouTube ana havuz entegrasyonu, 2000 YEDEKLER manuel test akisi ve toplu kabul.


## 2026-10-30 KULLANICI ONAYLI SIRALI BEKLEYEN IS PLANI
- Kullanici talimati: son birlesik Actions testleri bitene kadar tekrar tekrar test baslatma; kalan isleri asagidaki bagimlilik sirasina koy ve test sonucu geldikten sonra bu sirayla devam et. Bu bir arka plan otomasyonu olusturuldugu anlamina GELMEZ; bir sonraki calismada GitHub Actions durumu kontrol edilerek devam edilir.
- 1. Actions: son commitlerin run ID, 32 playback shard, sources/review job, artifact ve log sonucunu dogrula; yesil/eksik/hata durumunu kanitla. Gerekirse tek birlesik workflow icinde onar.
- 2. Kalici guvenli URL arsivi: kaynak URL'leri, provenance, tarih, run ID, hash, oynatma sonuclari ve insan kararlarini versiyonlu, erisim kontrollu, geri yuklenebilir bicimde sakla; tokenli URL'leri public repo'ya yazma; restore testi yap. 1 gunluk Actions artifact yeterli degildir.
- 3. #60 kurtarma: 27047 unique URL / 11860 VIDEO_DECODED tarihsel referans; #74 13593 unique URL / 7306 VIDEO_DECODED. 13868 yalniz #60 URL hash kimligi ile 4955 once calisan ama kaybolan hash adayini gercek URL olarak tarihsel artifact ve kaynaklardan geri bul; hash tek basina adresi geri vermez. Kaynak atif sayilarini URL kaybi sanma.
- 4. Kaynak kapsami: GitLab/Codeberg/diger kod platformlari, resmi TV canli siteleri, YouTube, Turkce dunya/diaspora, AZ/Azerbaycanca; Gunes TV, Rec TV, Gopik TV tek tek teyit. Yalnizca yasal/erisilebilir yayina dair kanit; konusulan dilin dogrulanmasi ayridir.
- 5. Tek birlesik test: kesif, arşiv/restore, kaynak kapsam, dedup, kanal kimligi, playback, dil, mevcut playlist ve orijinal YEDEKLER degismezligi; kullaniciyi tek tek testlere yonlendirme.
- 6. Ilk 2000: arsiv, dedup, manuel karar defteri ve backup koruma saglandiktan sonra kullanicinin onayi dogrultusunda mevcut V2 `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` dosyasinin YEDEKLER bolumune 2000 yeni aday ekle; orijinal TRT 1 1440P QHD ve DHA CANLI 720P HD'yi koru. Ayrı playlist olusturma. Kullanici IBO Player'da CALISAN_TURKCE/CALISMIYOR/YABANCI_DIL/KARARSIZ/HENUZ_TEST_EDILMEDI olarak siniflar; kararlari sonraki batch'ten disla ama tarihceyi silme.
- Kesin koruma: SADECE Madsc55/MADSC55-TV-V2; eski repo yok; ana playlistin mevcut 840 kanal/13 kategori/EPG/favori duzeni ve YEDEKLER'in iki orijinali kullanici onayli degisiklik asamasina kadar korunur.
- Bu kayit SADECE is sirasi ve devir notudur; isler tamamlandi, testler yeni commitler icin yesil veya arka planda surekli calisiliyor iddiasi degildir.


## 2026-10-30 #82 PLAYBACK (0,0) ARTIFACT INDIRME HATASI
- Kullanici GitHub Actions #82 ekran goruntusunu paylasti. `sources` basarili; `playback (0,0)` `Download shared source discovery` adiminda 5 retry sonrasi `Unable to download and extract artifact` hatasiyla durdu. Bu log oynatma/kanal decode hatasi degil, GitHub Actions artifact transfer hatasidir. Diger shard'larin tum sonucunu bu ekran kanitlamaz.
- `.github/workflows/v2-turkish-stream-review.yml` playback `Download shared source discovery` adimina kontrollu ikinci indirme denemesi ve indirilen JSON'un dolu/gecerli oldugunu kontrol eden fail-closed kontrol eklendi. Commit `1e2e12f5a9b546ceb9ca234a68e451dd4f04c05f`. Degisiklik hem playback hem review'daki ayni indirme adimina uygulandi; mevcut calisan #82 run'ini geriye donuk duzeltmez.
- Yeni commit Actions sonucu henuz dogrulanmadi; kullaniciya yeni run'in basarili oldugunu soyleme. Ana playlist/YEDEKLER/favoriler/EPG degismedi. Sonraki adim: #82 tamamlanma sonucu, yeni run, artifact tekrar hatasi ve tum shard kapsam kontrolu.


## 2026-10-30 #82 FAILURE SONRASI EK ARTIFACT RETRY
- Kullanici #82 final ekraninda FAILURE, 1h11m32s, 66 artifact, sources yesil, 32 playback job tamamlanmis fakat matrix kirmizi, review kirmizi gosterdi. Bilinen playback(0,0) sebebi source snapshot download 5 retry sonrasi basarisizlik; diger shard/review hata loglari henuz elde edilmedi.
- V2 workflow `Download private candidate snapshot` adimina ikinci download-artifact denemesi eklendi; commit `d2453cefab2173a82550200c46d85a88a3e3664f`. Onceki `unified-source-snapshot` retry duzeltmesi korunuyor. Yeni commitin Actions sonucu henüz dogrulanmadi; #82 eski committe calistigi icin duzeltilmis sayilamaz.
- Kaynaklarin ilk indirme hatasinda sonraki retry calisir; her iki deneme de basarisizsa job fail-closed olur. Public playlist, YEDEKLER, favoriler ve EPG degismedi.
- SIRADAKI: yeni run'in 32 shard/review durumlarini kontrol et; ayrintili review logu varsa diger hata sebebini ayir; sonra kalici guvenli arsiv ve #60 kurtarma yol haritasina devam et.


## 2026-10-30 KULLANICI EKRAN GORUNTUSUYLE ACTIONS DOGRULAMASI
- GitHub All workflows ekran goruntulerinde V2 `Kanallari ara — Tek Birlesik Gorev` #85 (commit d2453ce, 1h50m15s) YESIL, #84 (commit 1e2e12f, 1h21m53s) YESIL, #83 (commit 40b294d, 1h48m32s) YESIL. Eski #82 (commit f6d564c, 1h11m32s) KIRMIZI.
- `V2 Canonical IBO Playlist Parity` #5 YESIL. Bu bilgiler kullanicinin sagladigi GitHub ekran goruntulerine dayali, is-bazinda ayrintili log incelemesi degil. #85'in tam scan sayilari/arsiv dogrulamasi ayri kontrol edilmeli.
- Kullanici testlerin bittigini bildirdi. Yeni tam tarama baslatma; siradaki oncelik kalici guvenli tam URL arsivi ve #60 kurtarma. Ana playlist, YEDEKLER ve favorilere dokunma.


## 2026-10-30 ARSIV ONCESI KIMLIK VE PROVENANCE KAPISI
- Kullanici `v2/verify_private_archive_input.py` dosyasini main'e yukledi; GitHub fetch ile dosyanin varligi ve icerigi dogrulandi.
- Birlesik workflow `sources` job'una `discover.py --snapshot-output` sonrasi ve artifact upload oncesi `python v2/verify_private_archive_input.py --private v2/reports/private-playback-snapshot.json --public v2/reports/candidates.json` adimi eklendi. Commit `2da1bd6bc91850cd140980cf3c324bee525c7616`.
- Kontrol private/public URL SHA256 kimlikleri, tekillik, aday sayisi, source_ids eslesmesini fail-closed denetler; stream URL loglamaz. Workflow degisikligi yeni bir Actions calismasini tetikleyebilir; henuz yeni run sonucu dogrulanmadi.
- Bu kontrol KALICI SIFRELI ARSIV, harici saklama veya restore testi DEGIL. Kalici, yetki kontrollu depolama ve restore kaniti hala bekliyor. Ana playlist, YEDEKLER, favoriler degismedi.


## 2026-10-30 KALAN ISLERIN GERCEK DURUM KONTROLU
- V2 `v2/config/sources.json` dosyasi GitHub'dan okundu: iptv-org TR/AZ ulke listeleri, tur/aze dil listeleri, tr/az stream listeleri ve bolgesel girdiler zaten var. Bu girdileri yeniden eklemek gereksiz; kaynaklarin canli olarak basarili tarandigi veya tum eksiklerin kurtarildigi bu kontrolle kanitlanmaz.
- `v2/verify_private_archive_input.py` GitHub'da mevcut; kaynak taramasinda private/public aday kimlik kontrolu var. Review artifact transfer retry commit `f869229a` eklendi. Kullanici testlerin yesil oldugunu bildirdi, fakat bu son commitlerin ayri Actions sonucunu burada API ile dogrulamadik.
- KRITIK ACIK: harici kalici, erisim kontrollu, sifreli URL arsivi ve gercek restore testi kurulmus degil. #60'in sadece SHA256 ile bilinen kayip URL'leri hash'ten geri elde edilemez; kaynaklardan tekrar bulunmalidir. 2000 kanal YEDEKLER'e otomatik eklenmeyecek.
- Gunes TV / Rec TV / Gopik TV ve GitLab/Codeberg/official/YouTube kaynak kapsami ayri kanit gerektirir. Korunan IBO playlisti, iki orijinal YEDEKLER kaydi ve favoriler degistirilmedi.


## 2026-10-30 EKSIK SNAPSHOT OLUSTURMAYI ENGELLEME
- `v2/discover.py` kaynak hatalari varsa `--snapshot-output` ozel URL snapshot dosyasini yazmadan once fail-closed durur. Commit `2173ea3bbdb2421522fcb96e9909c6826b14c1ab`. Eksik kaynaklarla olusturulmus yeni private snapshot'in tam envanter gibi kullanilmasi engellenir.
- Bu commitin yeni Actions sonucu henuz bagimsiz dogrulanmadi. Onceki kullanici yesil test bildirimi eski run'lar icindir.
- Kalici sifreli arsiv, restore kaniti, #60 eksik URL kurtarma ve 2000 YEDEKLER test asamasi HALA tamamlanmadi. Ana liste ve YEDEKLER degismedi.


## 2026-10-30 TOPLU KAYNAK KESFI GENISLETME
- Yalniz V2 `v2/github_source_discovery.py` icin Gunes TV, Rec TV, Gopik TV, Azerbaycan Turkce ve Almanya/Hollanda Turk diaspora M3U arama sorgulari eklendi: commit `3e073f33c4361eb9d14b1eb4d14f8333023b18d5`.
- Genisleyen sorgu kapsamina uygun olarak MAX_REPOS/MAX_FILES 240'tan 320'ye cikarildi: commit `7fbbb30a8e6c2d41b7c8b37a7b727926f63f2056`.
- Bu degisiklikler GitHub'da kaydedildi, fakat yeni tarama sonucu ve testlerin yesil oldugu henuz bagimsiz dogrulanmadi. GitLab/Codeberg taramasi, resmi site stream esleme, YouTube dogrudan IBO uyumlulugu, kalici sifreli URL arsivi, #60 kurtarma ve 2000 YEDEKLER testi acik. Ana playlist/YEDEKLER/favoriler degismedi.


## 2026-10-30 BELGE SITELERI VE EK KANAL KAYNAKLARI
- Kullanici Scribd ve benzer belge sitelerinden Turk M3U kaynaklari aramayi istedi. Scribd, SlideShare, Internet Archive: belge/arastirma kaynagi, dogrudan M3U endpoint'i degil; erisim ve telif sinirlarina uyarak baglanti incelemesi gerekir. Bu uc sitenin otomatik tarayicisi HENUZ eklenmedi.
- Web ile incelenen TURKTV archive, iptv-org GitLab TR/TUR mirror ve dearbulut tam index M3U kaynaklari `v2/config/sources.json` icine discovery-only olarak eklendi. Commit `bd2bbf6c0845a7f554c642c33823b7d0a5db4685`. Mirror'lar URL dedup sisteminden geciyor; tum stream'ler oynatilir veya Turkce konusur iddiasi yok.
- Yeni commitin Actions sonucu henuz dogrulanmadi. Ana IBO, YEDEKLER ve favoriler korunuyor. Belge kaynaklari, Codeberg genel kesif, #60 URL kurtarma, sifreli kalici arsiv ve 2000 test kanali acik.


## 2026-10-30 BELGE ARAMASI VE BEST M3U KAYNAGI
- Scribd/SlideShare/Internet Archive icin web arastirmasi yapildi; SlideShare'deki IPTV belgelerinin bir kismi kurulum rehberi veya iptv-org liste kopyasi. Belgeyi dogrudan M3U endpoint'i gibi `sources.json` icine EKLEME; baglanti ve lisans incelemesi yapmadan URL cikarma.
- Dearbulut `PLAYLISTS.md` best/online/index listelerini belgeliyor; `best.m3u` discovery-only olarak `v2/config/sources.json` dosyasina eklendi, commit `7137b87fb24c8d3da282a817117e9786c409c23c`. Bu listedeki adaylarin video decode testi yeni run icin henuz dogrulanmadi.
- Kullanici toplu test ve arama istiyor. Yeni commit workflow push tetikleyebilir ama gercek run sonucunu API kaniti olmadan YESIL yazma. Yeni testler, kalici sifreli arsiv, #60 kurtarma, 2000 YEDEKLER islemi tamamlanmadi. Ana playlist ve favorilere dokunulmadi.


## 2026-10-30 ONUR EROZ DOGRUDAN M3U KAYNAKLARI
- Yayincinin kamuya acik sayfasinda 13.07.2026 guncelleme notuyla listelenen dort endpoint V2 discovery-only `v2/config/sources.json` icine eklendi: `/indirmeler/turk/index.m3u`, `/indirmeler/turk/all.m3u`, `/indirmeler/turk/karma-index.m3u`, `/indirmeler/dunya/index.m3u`. Commit `b99983d447a2f464b9e2a06597962185bb50eb2d`.
- Scribd'de Turk kanallari gecen belgeler tespit edildi, ancak belge sitelerinin tam M3U stream endpoint'i olmadigi ve kimi belgelerde kimlik bilgileri/abonelik akislari bulundugu goruldu. Scribd/SlideShare/Archive otomatik crawler kurulmus DEGIL; kaynaklari incelemeden veya kimlik bilgilerini yayinlamadan ayrica islemek gerekiyor.
- Yeni commitin Actions tarama/test sonucu henuz dogrulanmadi. Eklendi demek calisti demek degil. Ana IBO, YEDEKLER ve favoriler degismedi. Kalan kritik isler: yeni kaynak hatalarini denetle, GitLab/Codeberg belge aramasini tamamla, sifreli kalici arsiv ve restore, #60 URL kurtarma, 2000 test kanali.


## 2026-10-30 DUNYA/DİASPORA KANAL ADAYI FILTRESI
- `v2/discover.py` dunya ve dinamik kaynaklardaki Azerbaijani/Azeri/Azerbaijan/Azərbaycan etiketlerini aday kabul edecek sekilde genisletildi: `3d21b7e`.
- Ek kontrol sirasinda `TRT Turk` gibi dunya kaynaklarinda adinda sadece `TRT` veya `Turk/Turk` bulunan adaylarin elenebildigi goruldu; bu adlandirmalar da eklendi: `669f6310`.
- Sentetik regex kontrolunde Azerbaijani TV, Azərbaycan TV, Azeri live ve Turkish diaspora eslesti; English TV eslesmedi. Bu YALNIZCA filtre birim kontroludur; GitHub Actions'in 32 shard playback testi veya gercek kanal taramasi degildir.
- Kullanici toplu test istiyor; yeni commitlere ait Actions sonucunu dogrulamadan YESIL denemez. Kaynaklarin calisirligi, #60 kurtarma, belge crawler, kalici sifreli arsiv ve YEDEKLER 2000 hala acik. Korunan IBO playlisti degismedi.


## 2026-10-30 KULLANICI KARARI: TARAMA EN SON, IBO 2000+2000
- Kullanici yeni kanal taramasinin altyapi, eksik kaynaklar, offline testler, guvenli kalici arsiv ve restore hazir olmadan BASLATILMAMASINI istedi.
- Birlesik `.github/workflows/v2-turkish-stream-review.yml` otomatik `push` tetikleyicisi kaldirildi; `workflow_dispatch` manuel tetikleyicisi korundu. Commit `3645070a1e4905c6e37e09f3118a4de05a13935e`. Bu yeni push-tetikli scan olusmasini engeller; daha once kuyruga girmis/calismakta olan run'lari iptal ettigi anlamina gelmez. Diger workflow tetikleyicileri ayri denetlenmeli.
- Sira: (1) eksik kesif kaynaklari ve crawler kurulumlari, (2) kod/guvenlik ve offline testler, (3) erisim kontrollu sifreli kalici URL arsivi ve restore testi, (4) tam hazirlik denetimi, (5) kullanici talimatiyla TEK kapsamli tarama, (6) kalici arsiv + dedup + playback/dil siniflandirma, (7) mevcut YEDEKLER bolumune iki orijinali koruyarak 2000+2000 IBO test batchleri; her batch icin kullanici kararlari kalici tutulacak. Test kanallarini erken ekleme. Ana playlist, favoriler, EPG, logolar, yedekler korunacak.
- Son degisikliklerden sonra kanal taramasi sonucu veya yeni Actions YESIL iddiasi YOK. Hazirlik boyunca `discover.py` ve tam playback workflow'u calistirma.


## KALICI ANA IS SIRASI — TARAMA EN SON / IBO 2000+2000 (2026-10-30)
Bu bolum onceki tum devir notlariyla birlikte uygulanacak; tamamlandi isaretleri yalniz kanitli test/commit ile degistirilecek. SADECE Madsc55/MADSC55-TV-V2. Eski repo yasak.

### FAZ 0 — KORUMA VE DURUM ENVANTERI [ACIK]
- Tum V2 Actions workflow tetikleyicilerini ve kuyruktaki/calisan isleri denetle; tarama yapan push/schedule tetikleyicilerini kapat, halihazirda baslamis isleri otomatik durduruldu sanma. Birlesik workflow push kapatildi (3645070a); digerleri denetlenecek.
- Koruma sabiti: MADSC55_TV_IBO_CALISANLAR_TEST.m3u8 840 kanal, 13 kategori, blob 4b1c3cea4b5107a425abab60f62d41f9f81e05a7; YEDEKLER'in orijinal TRT 1 1440P QHD ve DHA CANLI 720P HD; YENILER/FAVORILER/cihaz favorileri/EPG/logo/sira ve yedekler. Kullanici onayli batch asamasina kadar hicbirine dokunma.
- DEVAM_NOTU, mevcut config, raporlar, #60/#74 farklari, #82-#85 CI kanitlari ve workflow esdegerliklerini tek kontrol listesinde uzlastir.

### FAZ 1 — KANAL ARAMASI YAPMADAN KESIF ALTYAPISI [ACIK]
- M3U kaynaklarinin endpoint, format, ulasim ve dedup testlerini mock/offline fixture ile yap; gercek kanal taramasi YOK. Mevcut 32 config girdisi icin source-id/URL/scope ve mirror cakismalarini denetle; eklenen TURKTV, GitLab mirror, Dearbulut best/index, Onur Eroz dort liste dahil.
- Scribd, SlideShare, Internet Archive icin kamuya acik belgelerden yasal/erisebilir M3U URL referansi kesfi; belgeyi playlist sanma, abonelik/paywall/credential/token toplama ve sizdirma yok; rate limit ve provenance.
- GitLab, Codeberg ve uygun diger kod barindiricilarinda genel TR/AZ/diaspora repo/dosya kesfi; GitHub/Gist 320 sinirli kesifin kaynak kapsamini ve kaynak kaybini test et.
- Resmi kanal siteleri, canli TV sayfalari, YouTube Turkce canli, Azerbaycan/Azerice, yurtdisi Turk kanallari, Gunes TV/Rec TV/Gopik TV icin ayrik adaptorler; IBO uyumlu dogrudan stream ile sayfa URL'sini ayir.
- #60 regresyonu: iptv-org 11204->9, Efeisot 4931->247, YOUSEFX13 1854->0, Free-TV 1347->5 vb. Kaynak, filtre, boyut, sira, parser ve kapsam kaybi icin offline regresyon fixture'lari ekle; yeni kaynaklari dogrudan IBO'ya yazma.

### FAZ 2 — GUVENLIK, KALICI ARSIV VE TEST ALTYAPISI [ACIK]
- Kaynak hatalarinda fail-closed fakat hangi kaynagin neden eksik oldugunu acik raporla; retry/backoff, boyut siniri, timeout, duplicate ve idempotency kontrolleri. Bozuk kaynagi sessizce basarili sayma.
- Private tam stream URL + source_ids + ilk/son gorulme + test/karar gecmisi icin erisim kontrollu sifreli KALICI arsiv tasarla/kur; GitHub public raporlara token/URL sizdirma; 1 gunluk Actions artifact arsiv DEGIL.
- Restore testi, butunluk hashleri, versiyonlama, kaynak izlenebilirligi, kismi tarama durumu, kayip kaynak raporu, 2000'lik batch checkpoint ve karar defteri ekle. Guvenli depolama erisimi yoksa taramayi baslatma; eksigi acik tut.
- Tum parser, discovery adaptor, kimlik/provenance, dil/ulke ayrimi, kalite/EPG/logo, playlist invariants, backup ve Actions artifact aktarimi icin mock/offline testleri tamamla. 32 playback shard ve review birlestirme mantigini sentetik veriyle dogrula; agdan gercek kanal arama YOK.
- Eski workflow davranissal esdegerlikleri ve besli sistem K2/K5 dahil tum onceki eksikleri kontrol et; kanitsiz kapatma, PR #71/main merge veya eski repo degisikligi YOK.

### FAZ 3 — TARAMA ONCESI KABUL KAPISI [ACIK]
- Kaynak kapsami ve yeni adaptor testleri, CI, koruma hashleri, arşiv/restore, kapasite ve guvenlik raporu YESIL olmadan tarama baslatma. Sadece bu faz bittiginde kullanici talimatiyla tek kapsamli tarama icin workflow_dispatch.

### FAZ 4 — EN SON TOPLU KANAL ARAMASI VE DOGRULAMA [BEKLEMEDE]
- Dunya capi Turkce ve Azerice yayin aramasi; GitHub/GitLab/Codeberg/M3U/belge referanslari/resmi siteler/YouTube/canli TV kaynaklari. URL/provenance'yi kalici arsive al, kaynak hatalarini ayri goster.
- #60 27047 URL, #74 13593 URL, ortak 13179, #60'a ozel 13868, #74'e ozel 414; 4955 gecmiste calisan ama yeni taramada olmayan hash. Hash'ten URL geri uretilemez; kaynaklardan yeniden edin. Eski/yeni farkini raporla, aday sayisini calisan kanal sayisi diye sunma.
- Playback/ffprobe, tekrar, turkce/azerice/yabanci/kararsiz, ulke, kaynak, kalite, stabilite, EPG/logo ve manuel karar kuyrugunu test edip arsivle. Kanitsiz 'calisiyor' deme.

### FAZ 5 — IBO PLAYER TESTI: 2000 + 2000 + ... [BEKLEMEDE]
- Arsiv, restore, test sonucu ve backup kanitindan SONRA mevcut YEDEKLER bolumune 2000 adaylik ilk parti; iki orijinal YEDEKLER kanalini koru. Ayrı playlist yok. Kullanici IBO cihaz testini yapacak.
- Sonuclari CALISAN_TURKCE / CALISMIYOR / YABANCI_DIL / KARARSIZ / HENUZ_TEST_EDILMEDI, ulke ve kaynakla kalici kaydet. Onceki test edilenleri kaybetme, sonraki partide tekrar sunma.
- Ilk 2000 sonucu ve geri alma/koruma kontrolunden sonra ikinci 2000, sonra ayni kuralla sonraki 2000'ler. Kullanici onayli YEDEKLER degisimi disinda ana listeyi/favorileri/EPG'yi degistirme.

### DURUM KURALI
- [ACIK]/[BEKLEMEDE] maddeleri bitmis sayilmaz. Yeni istegi uygun faza ekle, eski maddeyi silme. Her kod degisikligi icin commit, offline test kaniti ve kalan engeli yaz. Kanal taramasini faz 3 kabulunden once baslatma.


## 2026-10-30 FAZ 0/2 UYGULAMA: TARAMA KILIDI OFFLINE REGRESYON
- `v2/test_unified_safety_contract.py` icine birlesik taramanin sadece `workflow_dispatch` ile baslatilmasi ve `push`/`schedule` tetikleyicilerinin olmamasi regresyon kontrolleri eklendi.
- 32 kaynagin URL/id benzersizligi, HTTPS zorunlulugu, izinli scope ve yeni TURKTV/Onur Eroz/Dearbulut kaynaklarinin kaybolmama kontrolleri eklendi. Commit `ef0ad7e396a348dd2d18148445575d2404ed51b6`.
- Bu sadece kod degisikligidir: yeni Actions sonucu ve offline test calisma sonucu henuz dogrulanmadi. Gercek kaynak fetch, discover.py, playback veya kanal aramasi BASLATILMADI. Diger workflow tetikleyicilerinin denetimi ve kalici arsiv acik.


## 2026-10-31 KESIF TOPLU UYGULAMA / TEST KANITI
- V2 discover.py: dunya kaynagi metadatasinda Turkey kabulü ve bozuk dinamik kaynak envanterini sessizce atlamama: commit f579f29bf812f66dd4b04eb9b9a350086450cb36.
- v2/test_discovery_offline_regressions.py: 5 adet agsiz davranis testi: Turkey/TRT/AZ/world filtresi, AZ ulke adayligi, iki kaynaktan URL dedup ve source_ids, mevcut IBO URL haric tutma, EXTINF/EXTVLCOPT ayrıştırma. Commit 7a3ee60204710a280711fcfaddd183421b82d10c.
- v2/test_unified_safety_contract.py yeni test dosyasini tarama oncesi cagiriyor. Commit 30e52852559868002bf7689617bae0866e1e60e5.
- Yerel izole Python test calismasi: 5 test / 5 PASS (2026-10-31). GitHub dosyasindaki ilgili discover.py fonksiyonlari ayni icerikle yerelde calistirildi; BU tum repo veya Actions CI basarisi degildir.
- ACIK: tum workflow trigger audit, GitHub CI gercek sonuc, GitLab/Codeberg/genel web/belge/resmi site kesif adaptörleri, #60 regresyon kapsamı, sifreli kalici URL arsivi ve restore, toplu test altyapisi. Kullanici karari: bunlar tamamlanmadan GERCEK KANAL TARAMASI YOK; IBO playlistine dokunma.


## 2026-10-31 GITHUB ISLERI SIRALI UYGULAMA PLANI
1. Workflow ve Actions envanteri: tum V2 tetikleyicileri, bekleyen/calisan/basarisiz runlar, artifact hatalari ve olasi tarama tetiklemeleri; kanitsiz tamamlandi deme.
2. Koruma kapisi: 840 kanalli ana IBO playlist hash'i, 13 kategori, YEDEKLER iki orijinal kanal, YENILER, FAVORILER, EPG, logo, yedek ve geri alma testi.
3. Eski workflow davranissal esdegerligi ve besli sistem: K2/K5 dahil kalan farklar, PR #71'i merge etme, eski repoya dokunma.
4. Kaynak kesif altyapisi: GitHub/Gist, GitLab, Codeberg, Scribd, SlideShare, Internet Archive, resmi yayin siteleri, canli TV, YouTube, Turkce diaspora, AZ, Gunes TV/Rec TV/Gopik TV; tum adaptorleri offline fixture ile dogrula.
5. #60/#74 kaynak kaybi regresyonu: kabul filtresi, parser, limit, scope, provenance ve kaynak kaybi raporlarini test et.
6. Kalici erisim kontrollu sifreli URL arsivi: yedek, hash, restore, 2000'lik test karar defteri; restore kaniti olmadan tarama YOK.
7. Tum cevrimdisi testler ve Actions CI: hata varsa duzelt, tekrar test et, yesil kanitlari not et. Hazirlik CI ile gercek taramayi ayir.
8. SADECE tum kapilar gecildikten sonra kullanici onayiyla manuel tek kapsamli tarama, sonra IBO YEDEKLER 2000+2000.
Calisma kurali: bir asama kanitli yesil olmadan sonraki agir isi baslatma; tamamlanan commit/run/test kimliklerini buraya ekle. Ana IBO playlistine ve YEDEKLER'e tarama oncesi dokunma.


## 2026-10-31 GITHUB ISSUE SIRALI IS KUYRUGU
- #1 Actions tetikleyici ve run envanteri
- #2 Ana IBO playlist ve YEDEKLER koruma
- #3 K2/K5 besli sistem ve eski workflow davranis esdegerligi
- #4 TR/AZ dunya kesif adaptorleri
- #5 #60/#74 kaynak kaybi regresyonu
- #6 Sifreli kalici URL arsivi ve restore
- #7 Offline testler ve Actions kabul kapisi
- #8 En son manuel kapsamli tarama ve 2000'lik IBO partileri
Tum gorevler ACIK. Bir is kanitli bitmeden sonraki agir is baslatilmaz. GitHub issue olusturmak Actions testi baslatmaz; otomatik gece calismasi taahhudu yoktur. Ana IBO playlistine dokunma.


## 2026-10-31 OTOMATIK SIRALI ACTIONS HAZIRLIK TESTI
- .github/workflows/v2-ordered-preflight.yml olusturuldu: commit 9f5e525aadc554e2e2067740befc528911846158.
- Push main (v2/** degisikligi) ve workflow_dispatch ile tetiklenir. Sirali needs zinciri: compile -> protect -> discovery-tests -> safety. Onceki is basarisizsa sonraki calismaz. Sadece offline testler; GERCEK KANAL TARAMASI YOK.
- GitHub Issues #1-#8 hala uygulama backlog'udur: Actions bu issue'lari otomatik kodlayip kapatmaz. Diger adaptör, arsiv ve restore kodlari henuz tamamlanmadi.
- Yeni commit icin combined statuses bos dondu; Actions sonucu PASS diye onaylanmadi. Sonuc Actions ekranindan teyit edilecek.


## 2026-10-31 GECE OTOMATIK OFFLINE TESTLER
- v2-ordered-preflight.yml icin her gun 03:17 UTC schedule eklendi, commit 1905fbcd279e07b5d02eee58d976c83a6e0e7e7b. Push ve manuel tetikleme de korunur.
- Zincir compile -> protect -> discovery-tests -> safety; onceki job basarisizsa sonraki baslamaz. Kanal kesfi/playback yoktur.
- Bu sadece offline hazirlik test otomasyonudur; Issues #1-#8 kod islerini kendi kendine tamamlamaz. GitHub Actions run PASS sonucu henuz dogrulanmadi.


## 2026-10-31 TOPLU GUVENLI TARAMA KAPISI UYGULAMASI
- 39788e8: v2/archive_acceptance_gate.py; sifreli kalici arsiv geri yukleme onayi ve kaniti olmadan network kesif baslamaz.
- 6c76bbf: birlesik tarama workflow'unda GitHub kaynak kesfinden ONCE arsiv kabul kontrolu.
- 047c3cc: 4 cevrimdisi kabul kapisi senaryosu.
- d366741: bu testler sirali gece preflight zincirine eklendi.
- 4c38bdd: unified safety contract, arsiv kapisinin kesiften once oldugunu ve preflight testini dogrular.
- Bu kod degisiklikleri Actions PASS kaniti degildir. Arsiv saklama/sifreleme/gercek restore altyapisi henuz tamamlanmadi; onay degiskenleri ayarlanmadi. Gercek tarama yapilmadi, ana IBO playlisti degismedi.


## 2026-10-31 ARSIV GERI YUKLEME BUTUNLUK DUZELTMESI
- Commit 5e829870e30d7c2035e8f9a05923fbc913451e79: kabul kapisi artik restore dosyasinin varligini ve SHA256 digestini gercek byte'lar uzerinden denetliyor; yalnizca JSON boolean alanlarina guvenmiyor.
- Commit 977efb312fc17f80bfbe2031fcb4c421c0597dc3: offline testler gercek dosya, eksik dosya ve checksum uyusmazligi senaryolarini kapsiyor.
- Kod commitleri Actions PASS kaniti degildir. Kalici sifreli depo ve gercek backup/restore uygulamasi halen ACIK; gercek tarama YOK. Ana IBO playlistine dokunulmadi.


## 2026-10-31 YENI SOHBET DEVIR KAYDI — KANAL KESIF ONCELIKLI
- YALNIZCA Madsc55/MADSC55-TV-V2. Eski madsc-tv deposuna dokunma. Ana IBO playlisti (son bilinen 840 kanal), YEDEKLER'in 2 orijinal kanali, YENILER, FAVORILER, cihaz favorileri, EPG, logo ve yedekler korunacak; PR #71 merge edilmez.
- Kullanicinin asil hedefi: 20 kaynak grubunu ve 10 kesif motoru ozelligini TOPLU uygulamak; surekli kucuk test/plan commitleriyle oyalanmamak. Kaynak gruplari: TR M3U/M3U8; IPTV-org world/TR/AZ/tur/aze; Free-TV; GitHub/Gist; genel GitLab; Codeberg/diger hostlar; Scribd; SlideShare; Internet Archive; resmi TV siteleri; canli TV portallari; YouTube live; Azerbaycan; Avrupa Turk diaspora; dunya Turkce; Gunes TV/Rec TV/Gopik TV; TURKTV; Dearbulut; Onur Eroz; #60 kayip aday kurtarma. Motor: otomatik kaynak kesfi, provenance, gelismis parser, kaynak kaybi, dedup, dil/ulke, web sayfasi vs direct stream, sifreli kalici arsiv, eski-yeni karsilastirma, kaynak hata toleransi.
- 32 yapilandirilmis kaynak var, calisirliklari ve yeni kaynaklarla 32 shard playback dogrulanmadi. 4.955 eski calisan aday hash'i var, URL'ler kaynaklardan tekrar edinilmeli. Tarama ancak gercek sifreli kalici arsiv ve restore kabulunden sonra; ardindan 2000'lik IBO test partileri, kullanici onayi ile mevcut YEDEKLER'de.
- Son kod: 5e829870e30d7c2035e8f9a05923fbc913451e79 arşiv kabul kapisinda gercek restore dosyasi SHA256 kontrolu; 977efb312fc17f80bfbe2031fcb4c421c0597dc3 offline testleri yeni kanita uyarladi. GitHub Actions ordered-preflight #9 (run 41186910011) FAILURE discovery-tests; ardindan #10 (run 41186924198) SUCCESS, GitHub API ile dogrulandi. #9 tekrar calistirilmasin. #10: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/41186924198
- Onceki commitler: archive gate 39788e8; workflow gate 6c76bbf; tests 047c3cc; ordered CI d366741; safety assertion 4c38bdd; DEVAM_NOTU guncellemesi e25b625. Ordered preflight compile -> protect -> discovery-tests -> safety, gecelik schedule. Bu CI PASS yalnizca offline testleri kapsar, gercek tarama degil.
- SONRAKI ASIL IS: GitLab/Codeberg/Archive/belge platformlari/resmi TV/YouTube/diaspora kaynak adaptörlerini topluca KODLA, offline toplu test et; #60/#74 kaynak kaybi regression; gercek sifreli arsiv ve restore; acceptance gate; tek kapsamli tarama. Kullanici tekrar plan istemiyor, dogrudan kod/tespit ve toplu tamamlanma istiyor.
- Yeni sohbet basinda bu dosyanin son kaydini oku; GitHub Actions'in en son sonucunu denetle; eski repo veya canli IBO listesini degistirme.


## 31 Ekim 2026 — Kaynak envanteri çevrimdışı kabul kapısı
- `v2/test_source_inventory_contract.py` eklendi (`319b881`): keşif-only politika, benzersiz ID/URL, HTTPS/kimlik bilgisi kontrolü, çekirdek IPTV-org/Free-TV/Dearbulut/TURKTV/Onur Eröz kaynakları ve ülke-dil kanıtı ayrımı için çevrimdışı testler.
- `.github/workflows/v2-ordered-preflight.yml` discovery-tests aşamasına yeni test eklendi (`6f3aa30`); push sonrası Actions otomatik sıraya girer. Bu not yazılırken yeni run sonucu henüz doğrulanmadı.
- Ana playlist, YEDEKLER ve eski repo değiştirilmedi; gerçek ağ taraması başlatılmadı.
- Açık işler: 20 kaynak grubunun eksik adaptörleri; 10 keşif özelliğinin kapsamlı kabulü; gerçek kalıcı şifreli arşiv/geri yükleme; yeni Actions sonucunun kontrolü. Test eklemek bunları tamamlamaz.


## 31 Ekim 2026 — Kaynak kaybı denetimi CI entegrasyonu
- `v2/source_loss_audit.py` (`60d9304`): iki kaynak audit raporunu karşılaştıran salt-okunur CLI; SOURCE_MISSING, FETCH_FAILED, SOURCE_DROP durumları, varsayılan %50 düşüş eşiği; kritik düşüşte çıkış kodu 2.
- `v2/test_source_loss_audit.py` (`28a91a8`): #60→#74 örneği IPTV-org/Free-TV düşüşleri, eksik/hatalı kaynak, normal değişim, yinelenen ID ve eşik kontrolü çevrimdışı fixture testleri.
- `.github/workflows/v2-ordered-preflight.yml` (`d4ca6f7`) discovery-tests içine yeni testi sıraya aldı. Push tetiklemeli CI sonucu henüz okunmadı; başarılı iddiası yok.
- Bu araç otomatik gerçek kaynak taraması, eski URL kurtarma veya şifreli arşiv yerine geçmez. Ana playlist/YEDEKLER/eskidepo korunmuştur.


## 31 Ekim 2026 — Kaynak sayısı bozuk verisi regresyon düzeltmesi
- `v2/source_loss_audit.py` (`ec1814d`): eski taramadaki negatif/boolean/bozuk kaynak sayılarını kaynak kaybolsa bile karşılaştırmadan önce reddeder; güncel sayı da tam integer olmalıdır.
- `v2/test_source_loss_audit.py` (`d390eb6`): negatif eski sayı ve boolean yeni sayı için iki regresyon fixture eklendi.
- Testler zaten sıralı `v2-ordered-preflight.yml` içindeki discovery-tests aşamasına bağlıdır. Yeni CI sonucu henüz bağımsız doğrulanmadı; başarılı olarak sunma.
- Kalan büyük işler: kaynak adaptörlerinin tamamlanması, şifreli kalıcı gerçek URL arşivi ve geri yükleme, tüm Actions sonuçlarının kontrolü, tek izinli kapsamlı tarama. Playlist ve eski repo değiştirilmedi.


## 31 Ekim 2026 — Keşif motoruna önceki tarama kaynak kaybı raporu
- `v2/discover.py` (`506c303`): isteğe bağlı `--previous-report <onceki-candidates.json>` argümanı; önceki `source_audit` ile yeni audit karşılaştırılır, yeni `candidates.json` içinde `source_loss_audit` ve görünür uyarı üretilir. Salt-okunur karşılaştırmadır; playlist'e dokunmaz, gerçek tarama başlatmaz.
- `v2/test_discovery_offline_regressions.py` (`be569bf`): bu entegrasyonun kodda korunması için çevrimdışı regresyon denetimi; mevcut ordered-preflight discovery-tests adımına bağlı.
- Yeni GitHub Actions çalışmasının tamamlanma sonucu bu oturumda henüz doğrulanamadı; 'testler geçti' iddiası yok. Hâlâ eksik: belge platformları/genel kod hostları adaptörleri, şifreli kalıcı arşiv/restore ve tam kaynak kapsamı.


## 31 Ekim 2026 — Keşif CLI yanlış başarı / yanlış kayıp güvenlik düzeltmesi
- `v2/discover.py` (`e3ad12b`): `--offline --snapshot-output` ve `--offline --previous-report` kombinasyonları reddedilir; negatif `--limit` reddedilir; hiçbir kaynak başarıyla yüklenmediğinde snapshot çıkışı kapalıdır. Amaç boş test çıktısını gerçek kanal taraması ya da kaynak kaybı gibi göstermemektir.
- `v2/test_discovery_offline_regressions.py` (`f0bf096`): üç geçersiz CLI kombinasyonu için çevrimdışı fail-closed testleri. Zaten ordered-preflight discovery-tests aşamasına bağlı.
- Bu ortamda GitHub Actions run sonuçlarını doğrulayacak listeleme/dispatch aracı bulunamadı; container üzerinden GitHub erişimi de DNS nedeniyle başarısız. Testlerin gerçekten geçtiği iddia edilmiyor.
- Eksik adaptörler, şifreli kalıcı URL arşivi, gerçek restore testi ve kapsamlı tarama hâlâ tamamlanmadı. Ana playlist, YEDEKLER ve eski depo değiştirilmedi.


## 1 Kasım 2026 — doğrulanmış durum ve sıralı teslim planı
- Bu bölüm önceki 27 Ekim kayıtlarının **yerine geçen güncel durumdur**; önceki 1047 kanal / 2 YEDEKLER sayımı artık güncel değildir.
- V2 playlisti doğrudan okundu: **2840 kayıt**, **2002 YEDEKLER**, **838 diğer kategori kaydı**. Playlist içindeki 424 URL tekrarı farklı kategorilerdeki kasıtlı yayın tekrarlarını da kapsar; bütün listeyi benzersiz URL şartına bağlamak yanlıştır.
- YEDEKLER dışında hiçbir kategorinin sırası değiştirilmeyecek; yalnız YEDEKLER alfabetik olacak. İBO cihaz testi kullanıcıya aittir.
- Playlist güvenlik testindeki yanlış URL-tekillik koşulu ve ardından oluşan literal \\n sözdizimi hatası düzeltildi (93bea96, 8ef6483). Tarayıcıya YEDEKLER'e yeni kayıt eklenince yalnız bu kategoriyi yeniden sıralama eklendi (c222fe1). **Bu değişiklikler için yeni Actions başarısı henüz teyit edilmedi.**
- Geçmişteki Actions run 41189283457 içinde compile, protect, discovery-tests, safety işleri başarılıydı; **eski başarılı çalışma yeni commit'leri doğrulamaz**.
- YEDEKLER logoları tamamlanmadı; adayların gerçek IBO oynatımı henüz kullanıcı tarafından doğrulanmadı. Kaynak kapsamı ve eski kanalların kurtarılması tamamlandı denemez.

### Sıralı işler ve bitiş ölçütleri
1. **CI ve güvenlik:** Güncel main üzerinde derleme, playlist invariants, keşif ve güvenlik testlerini yeşil doğrula; orijinal 838 kaydı, iki ilk YEDEKLER kaydını ve tüm URL'leri koruyan değişmezleri güçlendir. Kırmızı job loglarını incelemeden tamamlandı deme.
2. **Kaynak envanteri:** v2/config/sources.json ile tüm keşif adaptörlerini denetle; Türkçe M3U/M3U8, IPTV-org, Free-TV, GitHub/Gist, GitLab, Codeberg, canlı TV siteleri, resmî yayınlar, YouTube, Azerbaycan ve diaspora kapsamını kaynak bazında raporla. Güneş TV, Rec TV, Gopik TV ve TURKTV/Dearbulut/Onur Eroz'u ayrıca doğrula.
3. **Kurtarma ve kayıp kontrolü:** #60 ve sonraki taramaları kaynak/URL bazında karşılaştır; kaybolan yayınları yeniden keşfet, her kaynağın ani düşüşünü raporla. Eksik URL'leri uydurma.
4. **Kalıcı arşiv ve gerçek tarama:** aday URL, kaynak, tarih, sınıflandırma ve test kanıtını kayıpsız sakla; geri yükleme ve canlı manifest/video testlerini doğrula. HTTP erişimi IBO cihaz testi değildir.
5. **Logolar ve sınıflandırma:** yalnız kanıtlı logo eşleştirmeleri; Türkçe/Azerice, ülke, yeni/mevcut, çalışan/belirsiz/çalışmayan etiketleri; farklı çalışan alternatif URL'leri koru.
6. **Toplu rapor ve kullanıcı testi:** kaynak bazında aday, doğrulanan, kaybolan ve yeni sayıları; kullanıcıya 2000'lik YEDEKLER partileri. Kullanıcı onayı olmadan ana İBO playlistini değiştirme.
- **Tamamlanma durumu:** Bu planın hiçbir aşaması güncel main üzerinde uçtan uca doğrulanmış olarak işaretlenmedi. Kod değişikliği ile başarılı çalışma kanıtı ayrı tutulacak.


## 2026-11-01 — CI gerçek çelişki düzeltmeleri (doğrulama bekliyor)
- Main playlist blob SHA `39259e7e8a16b47141ae17ac1d471eb695d8a50f`; önceki birleşik workflow `4b1c3...` sabitini kontrol ederek güncel playlisti yanlış reddediyordu. Workflow üç kontrolünde güncel blob SHA'ya geçildi: commit `696898c`.
- `v2-ordered-preflight.yml` içindeki beş keşif testinin `continue-on-error: true` ayarı kaldırıldı; hatalı testler artık CI'yi kıracak: commit `5c84046`.
- `v2/test_unified_safety_contract.py` güncel playlist SHA ve sıkı preflight koşuluna uyarlandı: commit `375e30a`.
- Eski run `41189283457` dört job SUCCESS idi fakat bu commitleri kapsamaz. Yeni main Actions sonuçları henüz doğrulanmadı; tamamlandı/yeşil iddiası yoktur.
- Playlist, YEDEKLER, YENİLER, FAVORİLER, cihaz favorileri, EPG ve eski depo değiştirilmedi. Sonraki adım: güncel CI job sonuçları ve başarısızsa logları; sonra kalan kod hatalarını düzelt.


## 2026-11-01 — #307 compile SyntaxError düzeltmesi
- Kullanıcının #307 compile logu: `v2/test_unified_safety_contract.py` satır 42, `SyntaxError: unexpected character after line continuation character`.
- Neden: önceki committe tek satır içine literal `\\nassert` yazılmıştı. Gerçek satır sonu ile değiştirildi; commit `67de3b8`.
- Yeni Actions PASS henüz görülmedi; compile/protect/discovery-tests/safety sonucun kontrolü sıradaki iş. Ana playlist ve YEDEKLER değiştirilmedi.


## 2026-11-01 — Logo Backup #5 push çakışması
- Kullanıcının paylaştığı #5 `backup` logunda `git push` `main -> main (fetch first)` nedeniyle exit 1; indirme adımı değil, eşzamanlı main ilerlemesi kaynaklı non-fast-forward reddi.
- `.github/workflows/v2-logo-backup.yml` commit `c83dd91`: logo commitinden sonra `git fetch origin main`, `git rebase origin/main`, `git push origin HEAD:main`; yarış halinde en fazla 5 güvenli deneme. Rebase çakışmasında abort ve kırmızı sonuç, asla force push yok.
- #5 eski run başarılı hale gelmez; sonraki logo backup run sonucunu ayrıca doğrulamak gerekir. Bu değişiklik mevcut playlist/YEDEKLER/cihaz favorilerini değiştirmez.


## 2026-11-01 — YEDEKLER Türk kanalları önceliği
- Ana playlist commit `4c8ebc4`: mevcut 2840 kaydın hiçbiri silinmeden 838 diğer kategori sırası korunarak, 2002 YEDEKLER içinde TRT 1 1440P QHD ve DHA CANLI 720P HD ilk iki sırada bırakıldı; adı açıkça Türkiye/TRT/Kanal 7/Kanal Avrupa/Show TV olan 14 kayıt hemen sonrasına alındı. Kalanlar sıralandı; başka ülkelerdeki ATV gibi belirsiz adlar Türk kabul edilmedi.
- Playlist yeni blob SHA `c6cda4d6e4d31fbcd46971b830ed55d474923ed8`; frozen SHA workflow ve safety sözleşmesinde güncellendi (`822995e`, `90b34dc`).
- Gelecekteki tarayıcı eklemeleri aynı Türkçe önceliği korusun diye `v2/real_ibo_scan.py` ve `v2/test_playlist_invariants.py` güncellendi (`41e8779`, `b9bb62f`), GEO-BLOCKED ad yazımı düzeltildi (`b83844b`, `756f0a5`).
- YEDEKLER içinde 18 kayıtta `tvg-logo` eksik: 30A TV Classic Movies, 6 Wise TV, Afra Film, America Paraguay, Arax TV, Arko TV, Armenia Premium, Arvan TV, Cafe Film, Canada One, CC-TV, Chosen TV English, DanceTV Algorhythm, Dej TV, Dove Channel, Dr G Medical Examiner, DreamWorks Channel Latin America, Grand Cinema. Orijinal logoları henüz kanıtlı bulunmadığından yanlış logo atanmadı. `v2/mirror_logos.py` sadece zaten tanımlı logo URL'lerini indiriyor; eksik 18 logo keşfi yapmıyor.
- Bu commitler için Actions yeşil sonucu henüz doğrulanmadı. İBO cihaz testi kullanıcıda.


## 2026-11-01 — #313/#314 compile ve playlist safety sözdizimi onarımı
- Kullanıcının #313 ve #314 ekran görüntüleri: `v2/test_playlist_invariants.py` satır 10, `SyntaxError: closing parenthesis ']' does not match opening parenthesis '('`. `v2/real_ibo_scan.py` içindeki aynı öncelik tuple'ında da aynı yazım yanlışı vardı.
- `v2/test_playlist_invariants.py` düzeltildi: `bd469d3`; `v2/real_ibo_scan.py` düzeltildi: `8e105e7`. Her iki dosyanın GitHub'daki son içeriği tekrar okunarak tuple kapanışı `)` doğrulandı.
- Playlist değiştirilmedi. 2002 YEDEKLER'in ilk iki kaydı TRT 1 ve DHA; sonraki 14 Türk yayın kaydı mevcut testin beklediği sıralamayla eşleşiyor. 838 diğer kayıt korunuyor.
- Yeni Actions PASS sonucu henüz görülmedi. Gelecek çalışma compile/protect/discovery-tests/safety aşamalarında ayrıca doğrulanmalı; hata varsa loguna göre onarılmalı.


## 2026-11-01 — Kanal keşfinde aday kaybını önleme
- `v2/real_ibo_scan.py` commit `5a66508`: kaynaklardan keşfedilen yeni adayların tamamı, HTTP/HLS kontrolü geçsin veya geçmesin, atomik olarak `v2/reports/ibo-candidate-inventory.jsonl` dosyasına yazılıyor. Kayıtlarda `http_hls_status` ve `ibo_device_tested: false` bulunuyor. Başarılı cihaz testi olarak sunulmuyor.
- Rapor artık aday envanteri konumunu ve HTTP/HLS doğrulanmamış/başarısız aday sayısını içeriyor. Kaynak erişim hataları mevcut raporda ayrıca tutuluyor.
- Ana playlist/YEDEKLER değişmedi. Bu adım yalnızca sonraki taramalar çalıştığında envanter üretir; henüz yeni gerçek tarama veya Actions yeşil sonucu doğrulanmadı.


## 2026-11-01 — Güncel playlist ve YEDEKLER logo denetimi
- GitHub'dan doğrudan okunan güncel `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`: 4.840 EXTINF kaydı; 838 diğer gruplar, 4.002 YEDEKLER. TRT 1 ve DHA YEDEKLER'in ilk iki sırasında.
- YEDEKLER içinde `tvg-logo` eksik/boş olan 33 kayıt bulundu (önceki 18 sayısı güncel değil). Tam isimler ve boş tvg-id bilgileri `v2/reports/yedekler-missing-logos.json` dosyasına kaydedildi, son düzeltme commit `3b45e31`.
- Eksik logolar henüz bulunup eklenmedi; doğrulanmamış logo tahmini yapılmadı. Ana playlist değiştirilmedi.
- Önceki CI yeşil run 41189283457 geçmişe ait; son commitlerin CI durumu hâlâ doğrulanmalı.


## 2026-11-01 — Kaynak geçmişini kaybetmeden tekilleştirme
- `v2/real_ibo_scan.py` commit `621e9ec`: aynı yayın URL'si birden çok kaynakta görülürse tek aday olarak tutuluyor, ancak tüm `source_ids` korunuyor. `ibo-candidate-inventory.jsonl` kayıtları kaynak listesini taşıyor; rapora `multi_source_candidates` sayısı eklendi.
- Bu kod değişikliği gelecek gerçek taramalarda etkili olur; yeni tarama ve Actions sonucu henüz doğrulanmadı. Ana playlist ve YEDEKLER değiştirilmedi.


## 2026-11-01 — Aşama 1: dünya Türkçe/Azerice IPTV keşfi genişletmesi
- `v2/discover.py` commit `fc39048`: dünya listelerindeki Türkçe/Azerice metaveri ipuçları daha geniş yakalanıyor; dil doğrulaması yapılmış sayılmıyor.
- `v2/config/sources.json` commit `8df9eb3`: IPTV-org Amerika, Afrika ve Okyanusya bölgesel listeleri dünya/diaspora keşfine eklendi; kaynak sayısı 32'den 35'e çıktı. Erişilebilirlik ve gerçek tarama çıktıları henüz doğrulanmadı.
- Korunan playlist, YEDEKLER, YENİLER, FAVORİLER ve cihaz favorileri değiştirilmedi. CI sonuçları doğrulanmadan aşama tamamlandı denmeyecek.


## 2026-11-01 — Keşif modülü düzeltmesi ve regresyon testi
- `v2/discover.py` commit `b51662f`: dünya listesindeki TR/AZ metaveri düzenli ifadesinin çift kaçış hatası düzeltildi.
- `v2/test_discovery_metadata.py` commit `77c5627`: dünya kaynaklarında Türkçe/Azerice metaveri eşleşmeleri, ilgisiz aday reddi ve birden çok kaynağın korunması için çevrimdışı regresyon testleri eklendi.
- GitHub Actions çalıştırma sonucu bu kayıtta henüz doğrulanmadı. Ana playlist, YEDEKLER ve favoriler değiştirilmedi.


## 2026-11-01 — Zorunlu CI keşif regresyon kapısı
- `.github/workflows/v2-ordered-preflight.yml` commit `f03f0db`: `v2/test_discovery_metadata.py` artık `discovery-tests` işinde zorunlu olarak çalışır; başarısızlıkta `safety` aşamasına geçilmez.
- Kaynak kaybı denetimindeki mevcut `v2/source_loss_audit.py` ve `v2/test_source_loss_audit.py` incelendi; önceki kaynaklara göre %50'den fazla düşüş ve kayıp/başarısız kaynak raporlanıyor. Bu modülün gerçek tarama baz çizgisi ayrıca doğrulanmalı.
- GitHub Actions sonuçları bu kayıt anında doğrulanmış değildir. Ana playlist, YEDEKLER ve favoriler değiştirilmedi.


## 2026-11-01 — Kaynak kaybı korumasında hata durumunu zorunlu kılma
- `v2/discover.py` commit `d9fb64a`: `--previous-report` ile kıyaslama kaynak kaybı bulursa rapor diske yazıldıktan sonra süreç başarısız çıkış koduyla sonlandırılır; sessizce başarılı kabul edilmez.
- `v2/test_source_loss_audit.py` commit `613f939`: %50 eşik sınırında regresyon testi eklendi.
- Önceki rapor olmadan karşılaştırma yapılmaz; gerçek tarama ve CI sonucu henüz doğrulanmadı. Ana playlist ve YEDEKLER değiştirilmedi.


## 2026-11-01 — Kanal dili aday sınıflandırması
- `v2/discover.py` commit `6185125`: keşif adaylarına `language_hint` (`tr_candidate`, `az_candidate`, `unknown`) ve `language_verified: false` eklendi. Coğrafi/metaveri işareti ses dili doğrulaması olarak gösterilmez.
- `v2/test_discovery_metadata.py` commit `844227c`: bu sözleşme için regresyon testi eklendi; mevcut zorunlu preflight zincirinde çalışır.
- Bu değişiklikler yalnızca keşif raporunu etkiler; ana İBO playlisti, YEDEKLER ve favoriler değiştirilmedi. CI başarısı henüz doğrulanmadı.

<!-- 2026-11-01 source inventory validation: 14fc9a1, tests: 3df167a -->


## 2026-11-01 — Kaynak envanteri doğrulama kaydı
- Kaynak kimlikleri ve HTTPS adresleri taramadan önce doğrulanıyor (`14fc9a1`).
- Tekrarlanan veya hatalı kaynaklar için çevrimdışı testler eklendi (`3df167a`).
- GitHub yazma kontrolü başarılı (`944ca8d`).
- Ana playlist ve YEDEKLER değiştirilmedi; Actions sonuçları henüz doğrulanmadı.


## 2026-11-01 — Güvenlik kapısı ve yazma doğrulaması
- `v2/discover.py` commit `0954621`: kaynak kaybı denetimi özel oynatma snapshot dosyası yazılmadan önce çalışır.
- `v2/test_discovery_offline_regressions.py` commit `16912ab`: denetimin dosya yazımından önce bulunduğunu kontrol eden test eklendi.
- Devir notuna doğrudan yazma yeniden çalışıyor. Korunan playlist ve YEDEKLER değiştirilmedi.
- GitHub Actions çalışmasının sonucu henüz doğrulanmadı.


## 2026-11-01 — Şifreli arşiv ve ana playlist güvenliği
- `v2/secure_archive.py` commit `6d9d2fd`: AES-256-GCM ve scrypt tabanlı şifreli envanter yedeği; atomik dosya yazımı, fsync ve geri yükleme doğrulaması.
- `v2/test_secure_archive.py` commit `d1297a8`: şifre çözme, yanlış parola, değiştirilmiş arşiv ve disk geri yükleme testleri.
- `v2/real_ibo_scan.py` commit `7e47203`: `--append-live` ile ana playlistin değiştirilmesi reddedilir.
- `.github/workflows/v2-ordered-preflight.yml` commit `322d049`: arşiv bağımlılığı ve zorunlu test adımı.
- Yerel şifreleme testleri 3/3 geçti; GitHub CI sonucu ve gerçek kanal envanterinin harici kalıcı arşivi henüz doğrulanmadı. İBO paketleri ve gerçek video/ses testi tamamlandı olarak işaretlenmedi.


## 2026-11-01 — Gerçek AV doğrulaması ve tarama envanteri şifreleme
- `v2/stream_probe.py` commit `0d51513`, düzeltme `950599b`: ffprobe ile video ve ses codec'lerini gerçekten sorgulama; HTTP 200 başarı sayılmaz. Yerel sistem ffprobe kontrolü `-nostdin` seçeneğinin desteklenmediğini gösterdi, kaldırıldı.
- `v2/test_stream_probe.py` commit `436ddff`: URL, ses/video, yalnız video ve timeout regresyon testleri; yerel test 4/4 başarılı.
- `v2/real_ibo_scan.py` commit `37726c3`: IBO aday ihracı için gerçek video+ses codec doğrulaması zorunlu.
- `v2/real_ibo_scan.py` commit `a597217`: envanter geçici düz metinden AES-GCM şifreli .enc arşive aktarılır; parola yoksa tarama başlamaz. Kalıcı harici yedek ve gerçek kaynaklarla uçtan uca tarama henüz yapılmadı.
- `.github/workflows/v2-ordered-preflight.yml` commit `124461a`: AV testleri CI'ya eklendi. İlgili commit için GitHub Actions çalıştırması sorgusunda henüz sonuç yoktu.
- Ana İBO playlisti ve YEDEKLER korunuyor. #60 kurtarma ve gerçek 1000/2000 paketleri tamamlanmadı.


## 2026-11-01 — IBO paket çıktısı ve eksik kaynak güvenliği
- `v2/real_ibo_scan.py` commit `c503035`: doğrulanmış tüm adayları disk üzerinde ayrı M3U partlarına yazıp `written_parts` ile gerçek dosya yollarını raporlar; ilk partla sınırlı değildir.
- Commit `755a29c`: M3U satır sonu kaçışları düzeltildi.
- Commit `8de4c46`: kaynak erişim hatası varsa tarama raporu yazılır ancak eksik kaynaklı sonuçtan IBO paketleri dışa aktarılmaz.
- Gerçek tarama sonucu, video/ses raporu, #60 kurtarma ve 1000/2000'lik gerçek çıktı henüz doğrulanmadı. Ana playlist, YEDEKLER ve favoriler değiştirilmedi.


## 2026-11-01 17:43 — Şifreli envanterden aday geri kazanımı
- `v2/real_ibo_scan.py` commit `2734c37`: önceki şifreli envanterde bulunan, ana listede olmayan ve yeni taramada kaybolmuş URL'ler yeniden aday havuzuna alınır ve ağ/video/ses testinden geçirilir. `recovered_from_previous_encrypted_inventory` raporlanır.
- Bu işlev #60'daki yalnız kimliği bilinen 4.955 URL'yi adres olmadan geri getiremez. Gerçek internet taraması bu ortamda DNS erişimi nedeniyle çalıştırılamadı; başarılı canlı AV sayısı veya M3U paket sayısı ileri sürülmüyor.


## 2026-11-01 — ZORUNLU ÇALIŞMA KURALI: Önce keşif kapsamı, sonra nihai AV taraması
- Kullanıcı kararı: Eksik kaynak entegrasyonları bitmeden yapılan taramalar yalnızca ARA TARAMA olarak etiketlenir; nihai/tam kapsamlı tarama veya proje tamamlandı diye sunulmaz.
- Önce TR/AZ/diaspora M3U kaynakları; IPTV-org, Free-TV, GitHub/Gist/GitLab/Codeberg, canlı TV web siteleri, resmî yayıncı siteleri, YouTube TR/AZ, Rec TV, Gopik TV, Güneş TV, Scribd ve erişilebilir diğer açık kaynakların keşif kapsamı incelenip ortak aday envanterine bağlanır. YouTube sayfa URL'si doğrudan IBO yayın URL'si sayılmaz.
- Sonra #60 geçmiş kayıplar için gerçek URL kurtarma, tekrar ayıklama, TR/AZ aday sınıflandırması, logo eşleştirme ve ana playlistle karşılaştırma tamamlanır. Kaynak/metaveri ipucu ses dili doğrulaması olarak gösterilmez.
- Ancak bundan sonra nihai geniş AV doğrulaması, şifreli arşiv/geri yükleme ve 2000'lik gerçek İBO test paketleri üretilir. Mevcut ara tarama kanıtları ve doğrulanmış adaylar kaybedilmez.
- Koruma: yalnızca MADSC55-TV-V2; ana MADSC55_TV_IBO_CALISANLAR_TEST.m3u8, YEDEKLER, YENİLER, FAVORİLER ve cihaz favorileri değiştirilmez. YEDEKLER ilk iki sıra TRT 1 1440P QHD ve DHA CANLI 720P HD korunur. PR #9 izinsiz birleştirilmez. İBO Player cihaz testlerini kullanıcı yapar.
- 2026-11-01 başarılı önceki ara tarama: 12.148 yeni URL adayı, 4.098 ffprobe AV doğrulanmış aday, 3 adet 2000 sınırına göre M3U parçası; bu sonuçlar nihai kapsam kanıtı değildir.


## 2026-11-13 — Zorunlu düzeltme: nihai taramadan önce entegrasyon kabulü
- Kullanıcı teyidi: #34 kaynak adaptörleri, dünya kapsamı, resmî yayıncılar, YouTube Live, M3U/M3U8, logo ve EPG eşleştirmesi tam bağlanıp kabul edilmeden yeni tarama **nihai/toplu dünya taraması** olarak sunulmayacak.
- 2026-11-13 run 43412576224: 13.735 yeni URL adayı, 4.301 FFmpeg AV doğrulanmış URL, 88 başarılı kaynak; bu **ARA TARAMA** kanıtıdır, benzersiz kanal veya dünya çapında eksiksiz kapsam kanıtı değildir.
- PR #19 merge 6cd8dbc: GitHub/GitLab/Codeberg/official/YouTube/M3U aday keşfi workflow'a eklendi; metadata adayları AV kanıtı değildir. GitLab/Codeberg/official/YouTube çıktıları henüz gerçek FFmpeg taramasına tümüyle aktarılmadı.
- Kabul için kalanlar: dünya kaynaklarının akış URL'lerine çözülmesi ve FFmpeg'e verilmesi; kaynak başına başarı/hata ve ülke kapsam raporu; YouTube canlı metadata ile oynatılabilir yayın ayrımı; kanal kimliği/logo/EPG eşleştirme kanıtı; zorunlu entegrasyon testleri; en son tam tarama, şifreli yedek/geri yükleme, gerçek İBO test paketleri.
- Hiçbir ara test tamamlanmış nihai kabul sayılmayacak. Ana İBO listesi, YEDEKLER/YENİLER/FAVORİLER korunacak.


## 2026-11-13 — #34 bozuk aday URL regresyonu (PR #31)
- `v2/discovery_34.py`: GitHub/GitLab/Codeberg ve curated adaylarda null, sayı, liste veya nesne URL alanları güvenli biçimde atlanır; keşif döngüsü çökmez.
- `v2/test_discovery_34.py`: bozuk dış URL alanları için çevrimdışı regresyon eklendi.
- PR #31 merge commit `0ba9dd81b3ef8007e03a9efdcc392bf4d2d551c2`. Actions run `43448805524`: Production Security Gate, stage 6 offline acceptance ve Discovery 34 offline acceptance iş adımları SUCCESS.
- Bu sonuç canlı Codeberg API, tüm kaynakların FFmpeg girişine bağlanması, gerçek AV kanıtı veya nihai dünya taraması kabulü değildir. #34 açık kalır. Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi.


## 2026-11-13 — #34 kaynak raporu entegrasyon doğrulaması (PR #46)
- `v2/discovery_34_integrate.py`: official/YouTube/M3U raporlarının kök ve satır koleksiyonları doğrulanır; hatalı satırlar atlanır, geçerli adaylar korunur, hatalı koleksiyon biçimleri fail-closed hata üretir.
- `v2/test_discovery_34_integrate.py`: karışık bozuk/geçerli satırlar ve geçersiz koleksiyon tipleri için regresyon eklendi.
- PR #46 merge commit `06a26a6aff41ded43cb1e3e78abe14080cc6fb9e`; Actions run `43449834934` SUCCESS; #34 offline adapter/integration acceptance ve Stage 6 paket/arşiv regresyon adımları SUCCESS.
- Bu yalnızca mevcut rapor dosyalarının çevrimdışı normalizasyon kabulüdür; canlı API, her sağlayıcının gerçek yayın URL'sine çözülmesi, FFmpeg AV, logo/EPG üretim eşlemesi veya nihai dünya taraması değildir. #34 ve gerçek yayın gerektiren görevler açık kalır. Korunan listelere dokunulmadı.


## 13 Kasım 2026 — Güncel main üzerinde Aşama 2/3 offline kimlik ve kurtarma entegrasyonu kabul edildi
- PR #70 squash merge `8a2abf3f74073a5ea6a34c949260ac0c26556b80`.
- Main üzerinde Stage 2/3 modülleri: `identity_metadata.py`, `recovery_queue.py`, `stage2_integration.py`, `stage3_identity_recovery.py`, `stage3_metadata_acceptance.py`, `stage3_recovery_queue.py`; `discover.py` metadata ipuçlarını rapora ekler, `consolidate_inventory.py` sunulan URL SHA-256 değerini doğrular, `real_ibo_scan.py` ve `stream_probe.py` scanner/probe sözleşmesine bağlanır.
- Mevcut onaylı Production Security Gate'e Stage 2/3 offline regresyon grubu eklendi. Actions run `43454977935` ve `43454976797`: SUCCESS. Her ikisinde güvenlik kilidi, playlist invariants, task-ledger integrity, Stage 6 offline paket/arşiv, Stage 2/3 kimlik/EPG/kurtarma ve #34 offline entegrasyon adımları PASS.
- İlk denemede bulunan uyumsuzluklar (main scanner dynamic source validator kaybı, bozuk FFprobe JSON türleri, Stage 3 scanner test sözleşmesi) düzeltilip tam gate yeniden çalıştırıldı.
- Bu kabul offline kod/entegrasyon kabulüdür. Canlı yayınlarda yeni FFmpeg görüntü+ses kanıtı, gerçek dış kaynak API doğrulaması, bağımsız harici arşiv geri yüklemesi ve gerçek 1000/2000 İBO üretimi değildir. #15/#17–#21, #28–#34 nihai kabulü açık tutulur. Yeni kanal taraması yapılmadı; ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi.


## 13 Kasım 2026 — PR #71 görev defteri ve devam notu ana dala alındı
- PR #71 squash merge `02e5792c209149e98ec4e14d77c087f9d8faf49b`.
- PR #71 için Production Security Gate run `43455192478`: SUCCESS. Görev defteri bütünlüğü, güvenlik kilidi, korunan İBO invariantları, Stage 6 offline paket/arşiv, Stage 2/3 offline kimlik-EPG-kurtarma ve #34 offline adaptör testleri PASS.
- Bu run dokümantasyon ve defter bütünlüğü kabulüdür; canlı #34 API sözleşmesi, gerçek yayın AV, yeni kanal taraması veya gerçek 1000/2000 paket üretimi değildir.
- Ana dalın bu kayıt güncellemesinden sonraki gözlenen commit'i `02e5792c209149e98ec4e14d77c087f9d8faf49b`. Görev defterinde 34 görev: 21 completed, 13 in_progress; açık işlere completed statüsü verilmedi.


## 13 Kasım 2026 — #34 canlı API hata kaynağı ayrıştırıldı
- Önceki gerçek Actions canlı sözleşme koşusu `43319831631` iş kayıtları incelendi: GitHub API `ok` ve 20 aday, GitLab API `ok` fakat 0 aday, Codeberg API `HTTPError` nedeniyle başarısız. Bu sonuç tüm üç kaynağın canlı kabulü değildir.
- Güncel `main` üzerindeki `v2/discovery_34_live_contract.py`, HTTP durum kodunu `HTTP_<code>` biçiminde, sağlayıcı ve endpoint host ile raporlar; 408/425/429/5xx için en fazla üç deneme uygular. 403 kalıcı erişim/izin engeli olarak tekrar denenerek başarıya çevrilmez. `v2/discovery_34.py` Codeberg için Forgejo `/api/v1/repos/search` yolunu ve `data` yanıt listesini bekler.
- Harici API dokümantasyonu Forgejo/Codeberg repository-search endpoint'inin `/api/v1/repos/search` olduğunu ve `data` alanlı yanıt kullandığını doğruluyor; dolayısıyla mevcut kanıt, endpoint/JSON şema hatasından çok CI çıkışının Codeberg tarafından 403 ile reddedilmesiyle uyumlu. Bu, Codeberg'in kendi tarafında kalıcı arıza olduğu anlamına gelmez.
- Güncel main üzerinde canlı sözleşme yeniden çalıştırılmadı; mevcut GitHub bağlantısı workflow_dispatch başlatma yetkisi sağlamıyor. Bu nedenle #34 canlı kabulü açık bırakıldı; hata gizlenmedi, Codeberg başarısızlığı başarı sayılmadı. Yeni kanal taraması ve playlist değişikliği yapılmadı.


## 13 Kasım 2026 — #34 Codeberg blocker kaydı ana dala alındı
- PR #79 squash merge `2d2bd9193cf06fbd81077912e4e4d434316e7c5e`.
- Actions `43455836114`: SUCCESS. Güvenlik, playlist invariants, görev defteri, Stage 6 offline paket/arşiv, Stage 2/3 kimlik-EPG-kurtarma ve #34 offline adaptör adımları PASS.
- Bu koşu canlı Codeberg API çağrısı değildir. #34 açık: önceki canlı koşuda Codeberg HTTPError; güncel main canlı API tekrar çalıştırılmadı. GitHub Actions bağlantısı workflow_dispatch başlatma sağlamıyor.


## 13 Kasım 2026 — #34 altı arama terimli canlı sözleşme altyapısı
- PR #86 squash merge `ec02cb3993f54d42d3b3a4a71670eb50c87c6adc`.
- Actions `43457308527`: SUCCESS. Çevrimdışı güvenlik, görev defteri, Stage 2/3, Stage 6 ve #34 adapter/integration regresyonları PASS.
- `v2/discovery_34_live_contract.py` artık yalnızca `turkish-iptv` örnek terimini değil, `QUERIES` içindeki altı terimin tamamını GitHub/GitLab/Codeberg için ayrı ayrı kontrol ediyor. Sağlayıcı ve sorgu bazında başarısızlıkları görünür kılıyor; HTTP status/reason, Retry-After ve rate-limit kalan sayısını güvenli biçimde raporluyor; response body veya gizli veri yazmıyor.
- Yeni offline testler altı terim kapsamını ve Codeberg 403 tanılamasını doğruladı. Bu Actions koşusu canlı sağlayıcı çağrısı değildir; Codeberg canlı API sonucu henüz alınmadı. #34 açık kaldı.
- Yeni kapsamlı kanal taraması yapılmadı; ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi.


## 2026-11-13 — encrypted archive restore size-bound acceptance (current main)
- PR #89 merged as `207f5c3f4a83cc1bb716deddf1344cf8c1f36e16`; head `3396cb0806da203aae336d3b3b3083bc198632a5`; Production Security Gate run `43457399513` SUCCESS. All grouped steps passed, including Stage 2 identity metadata, Stage 6 archive/package regressions, Stage 2/3 offline identity/EPG/recovery, Discovery 34 offline adapters and protected IBO invariants.
- `v2/secure_archive.py`: `decrypt` now rejects encrypted blobs larger than the format header + MAX_INPUT plaintext + AES-GCM tag before decryption. `v2/test_secure_archive.py` covers the upper bound in addition to malformed/truncated, tamper, round-trip and same-path cases.
- Offline/security acceptance only. Does not close #28–#33 real production package/independent restore gates, #15 unmatched historical identities, #17–#21 final mapping/live evidence, or #34 live provider/AV/archive gate. No scan or playlist write; protected lists unchanged.


## 13 Kasım 2026 — Güncel main Production Security Gate ve canlı #34 teşhisi
- Main commit `478aba262b0b37c39019a85bcc3abfc812b04208` için Actions run `43458337072`: offline Production Security Gate SUCCESS; ayrı `live-discovery-diagnostic` işi SKIPPED. Bu run canlı sağlayıcı kanıtı değildir.
- Canlı altı-terim denetimi ayrı olarak main commit `436d5492b71394a2958b08cc8895156f5c111ed0` üzerindeki Actions run `43458069505` ile yapıldı. Ana Production Security Gate SUCCESS; ayrı canlı diagnostic işi Codeberg HTTP 429 nedeniyle FAILURE oldu (iş `continue-on-error` olduğundan offline ana gate başarılı kaldı).
- GitHub: altı sorgunun tamamı başarılı; aday kayıtları sırasıyla 11, 20, 20, 20, 12, 19 (toplam 102 ham kayıt; benzersiz kanal sayısı değildir). GitLab: altı sorgunun tamamı başarılı, 0 aday. Codeberg: altı sorgunun tamamında HTTP 429; her sorgu üç denemeye kadar sürdü, Retry-After/rate-limit kalan başlığı yoktu.
- PR #117 squash merge `eda23b30c3cc05a019e79e42235234488110d4f1`; Actions run `43458662138` SUCCESS. İlk tükenmiş 429 sonrasında sağlayıcı devre kesicisi açılır, kalan sorgulara istek gönderilmez; sorgular skipped olarak raporlanır ve genel durum error kalır.
- Codeberg için sayısal ve HTTP-date Retry-After desteği 60 saniye üst sınırıyla main'de mevcut. Devre kesici düzeltmesiyle yeni tek seferlik canlı doğrulama bu dokümantasyon commitinden sonra tetiklenecek; Codeberg başarılı yanıt vermeden #34 kapatılmaz.
- PR #130 squash merge `3fc54210d22d6dd52bf97c85dae2fe7576102bf7`; Actions run `43459495298` SUCCESS. XMLTV timezone offset sınırları ve geçersiz programme start/stop aralıkları için üç yeni test PASS; EPG bütün kaynaklarının gerçek içerik kabulü değildir.
- Stage 6 (#28–#33) offline paketleme, M3U doğrulama, şifreli arşiv/geri-yükleme regresyonları; Stage 2/3; #34 offline adapter ve güvenlik/invariant kapıları PASS. Gerçek FFmpeg AV, bağımsız harici depodan restore veya gerçek 1000/2000 kanal paketi değildir.
- Görev defteri 21 completed / 13 in_progress olarak korundu; gerçek yayın kanıtı, bağımsız harici geri yükleme ve gerçek paket kanıtları olmadan görev kapatılmadı.
- Yeni kapsamlı kanal taraması yapılmadı. Ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi.


## 13 Kasım 2026 — canlı keşif ve gerçek AV kanıtlarının yeniden denetimi
- PR #128 birleştirildi (`e0d533e5f17996c02f614b33cbf9a3966e7611f7`). Güncel Production Security Gate ve Stage 2/3 + Stage 6 + #34 çevrimdışı kabulü run `43459603986` içinde PASS.
- Aynı run'ın tek seferlik canlı metadata tanılama işi: GitHub altı sorgunun tamamında geçerli yanıt verdi; ham sonuç sayıları `11, 20, 20, 20, 12, 19` (toplam 102 ham eşleşme; sorgular arası tekilleştirme yapılmadı). GitLab altı sorguda da geçerli boş listeler döndürdü. Codeberg `turkiye.m3u` sorgusunda üç sınırlı denemeden sonra HTTP 429 verdi; devre kesici kalan beş terimi atladı. 30/60 saniyelik geri çekilme Codeberg sınırını kaldırmadı. Bu canlı iş non-blocking olarak başarısız; ana güvenlik işi başarılı.
- #34 kodu tüm altı terimi kapsıyor, HTTP 429 sonrası sağlayıcıya tekrar tekrar yüklenmiyor; Codeberg canlı kabulü açık. Tam kanal taraması yapılmadı, playlist değişmedi.
- Eski gerçek dünya AV raporu run `42216075104`, artifact `13524765368`: 35.327 aday, 13.884 mevcut-run FFmpeg video+ses decode, 9 RSA-sealed shard. Aynı rapor tarihî 4.955 hash'in 4.949'unu worldwide raporla eşleştiriyor; 3.080 tarihî hash için AV decode kanıtı var. Ancak `historical_broadcaster_identity_verified=false` olduğu için #15 kapanmaz.
- Ayrı #24 run `43241168321` restore receipt: 801 AV sonuç (800 TR/AZ), 7.819 arşiv kaydı geri yüklendi. Bu rapor ile worldwide raporun hash örtüşmesi henüz hesaplanmadı; sayılar toplanmadı.
- 1000/2000 gerçek paketler henüz üretilmedi. Worldwide URL shard'ları RSA-3072 alıcı public key ile mühürlü; açma işlemi kullanıcıya ait private key gerektiriyor ve bu private key depoda bulunmuyor. Ana İBO/YEDEKLER/YENİLER/FAVORİLER korunuyor. Sentetik paketler gerçek teslim sayılmadı.

## 13 Kasım 2026 — Stage 5 kanıt kapısı ve #34 sorgu ölçümü güncellemesi
- PR #134 Stage 5 evidence-gated IBO export/final-acceptance code and offline regressions squash merge 917dcddaff863ae56f9099a0539d63b6f85765c9; main Production Security Gate run 43460202117 SUCCESS, including Stage 5 evidence-gate tests.
- Bu kabul yalnızca kanıt kapısının ve dışa aktarma doğrulama kodunun çevrimdışı testidir. Gerçek 1.000/2.000 kanal paketi, FFmpeg AV, IBO cihaz oynatımı veya kullanıcı onayı yerine geçmez; #31–#33 açık kalır.
- PR #132 sorgu sayımı düzeltmesi squash merge ee2471b28804fb7c2c212f83f62d73d06566bed9; offline Production Security Gate run 43460164276 SUCCESS. queries_checked gerçek ağ çağrılarını sayar; queries_total ve queries_skipped ayrıdır.
- Canlı run 43459603986 sonucu: GitHub 6/6 geçerli, 102 ham aday satırı; GitLab 6/6 geçerli boş liste; Codeberg ilk sorguda HTTP 429/3 deneme, kalan beş sorgu atlandı. Codeberg için başarılı canlı kabul yok; #34 açık.
- Worldwide tarama kapsamı seçeneği --worldwide mevcut main'de etkinleştirilebilir; offline kapsam testi geçti. Bu seçenekle yeni tarama başlatılmadı.
- Ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi; yeni kapsamlı kanal taraması yapılmadı.


## 13 Kasım 2026 — worldwide kaynakların AV tarama hattına bağlanması
- PR #141 squash merge `703bf12d3cb3e61cf4b5e9505350ed6dd698f302`: GitHub 403 rate-limit exhaustion da sağlayıcı devre kesicisini açar; sıradaki beş sorguya istek gönderilmez.
- PR #144 squash merge `6c10d7d3467a145931ca05c91942db8a930a1faf`: workflow yalnızca read-only `github.token` ile GitHub API sorgular; token yalnızca `api.github.com` host'una gönderilir. Public Gist'lerin son 200 kaydı içinde M3U/M3U8/TXT dosyaları için bounded arama ve parse eklendi. Main Production Security Gate run `43462401762` SUCCESS.
- PR #145 squash merge `50d839b3c1e2860921105768aa3450bc02e04a7e`: GitLab ve Codeberg public repo arama/tree/raw M3U adaptörleri; altı terim, repo/dosya limitleri, 429/403 rate-limit circuit breaker ve offline regresyonlar. Unified discovery report ve manual scan workflow'una bağlandı. Main Production Security Gate run `43463214901` SUCCESS.
- PR #142 squash merge `6ffa52d24271c161c573052594b765e185357ca8`: GitHub/Gist M3U kaynak raporu birleşik keşif raporuna ve scanner'ın M3U feed girişine bağlandı.
- PR #143 squash merge `d0d2b4a53ebca4f210b55640689c26f859201c3d`: kritik AV kabul düzeltmesi. Scanner artık yalnızca ffprobe stream metadata'sına bakarak AV verified saymaz; gerçek video frame ve audio frame decode için `verify_decoded_av` başarılı olmalıdır. Main Production Security Gate run `43461691392` SUCCESS.
- PR #146 squash merge `078aafaf0e5d16ea57aae042e81b55d10736e08f`: official broadcaster directory worldwide moduna genişletildi; YouTube Live ve official site sayfaları yt-dlp ile doğrudan HTTPS HLS URL'lerine çözülür; signed URL'ler yalnızca authenticated encrypted raporda saklanır. Scanner şifreli raporu bellekte açar ve FFmpeg gerçek ses+görüntü decode olmadan kabul etmez. Manual scan workflow'u `--worldwide`, birleşik M3U adayları ve şifreli direct stream raporuyla hazırlandı. Main Production Security Gate run `43464677927` SUCCESS.
- PR #147 squash merge `d970a0da1f73e3bdd3552c193a144d9ded9a0be1`: 340 dakikalık manuel workflow bütçesine göre dünya çapı tarama aday tavanı 3.000'e ayarlandı; gerçek 1.000/2.000 paket üretim hedefleri ayrı kanıt kapısında kalır.
- Main canlı diagnostic run `43464785708`: read-only token sonrası GitHub 6/6 sorgu başarılı (11,20,20,20,12,19 ham eşleşme; toplam 102, benzersiz kanal sayısı değildir). GitLab 6/6 sorgu başarılı fakat 0 aday. Codeberg ilk sorguda HTTP 429 verdi; bir sorgu denendi, kalan beş sorgu circuit breaker ile atlandı. Offline ana güvenlik işi SUCCESS, ayrı canlı diagnostic FAILURE. Codeberg canlı kabulü yok; #34 açık.
- Tarama workflow'u yalnızca `workflow_dispatch` ile başlar ve bu değişiklikler sırasında çalıştırılmadı. Yeni kapsamlı kanal taraması yapılmadı. M3U kaynaklarının bulunması/ayrıştırılması playback kabulü değildir; YouTube/official resolver adayları da FFmpeg decode öncesi verified sayılmaz.
- Görev defteri 21 completed / 13 in_progress olarak kaldı: #15, #17–#21, #28–#34 açık. #15 tarihî yayıncı kimliği; #17–#21 nihai metadata/EPG/kategori/çözünürlük ve gerçek yayın kanıtı; #28–#33 gerçek paket, harici restore ve cihaz kabul kanıtı; #34 Codeberg canlı API ve tüm kaynakların gerçek AV kabulini bekler.
- Ana İBO, YEDEKLER, YENİLER ve FAVORİLER'e yazılmadı; hiçbir görev gerçek kanıt olmadan kapatılmadı.


## 13 Kasım 2026 — YouTube Live worldwide sorgu ve bölge dağılımı
- PR #149 squash merge `2d828e24805bcd41900c4e9212fb5d134068a7dc`. YouTube Live arama kümesi 18 TR/AZ sorgusunu koruyarak 12 dünya sorgusu ekledi (Afrika, Asya, Avrupa, Latin Amerika, Arapça, Hintçe, İspanyolca, Fransızca, Portekizce, Japonca/Korece ve uluslararası haber/TV). Her aday TR/AZ/WORLD bölge etiketi taşır; birleşik rapor ve şifreli doğrudan HLS resolver bu etiketi korur.
- Resolver bütçesi bounded ve dengeli: en çok 60 YouTube live adayı (TR/AZ/WORLD için 20/10/30 başlangıç kotası) ve en çok 60 official site adayı (ülke başına önce bir aday, kalan bütçe round-robin). Direct URL'ler authenticated encrypted dosyada saklanır; FFmpeg gerçek video frame + audio frame decode olmadan AV verified sayılmaz.
- Main Production Security Gate run `43466178239` SUCCESS; YouTube sorgu bölgesi, resolver bütçesi, encrypted round-trip ve scanner intake offline regresyonları PASS. Canlı YouTube keşfi veya geniş kanal taraması bu gate içinde çalıştırılmadı.
- Manuel worldwide scan workflow'u 3.000 aday tavanıyla hazırdır; `workflow_dispatch` dışında tetiklenmez ve henüz çalıştırılmamıştır.
- Son canlı sağlayıcı tanısı `43464785708`: GitHub token ile 6/6 başarılı ve 102 ham eşleşme; GitLab 6/6 geçerli boş sonuç; Codeberg ilk sorguda HTTP 429, kalan beş sorgu circuit breaker ile atlandı. Codeberg canlı kabulü açık kaldı.
- Görev defteri 21 completed / 13 in_progress; #15, #17–#21, #28–#34 gerçek yayın, paket, bağımsız restore ve cihaz kanıtları bekliyor. Ana İBO/YEDEKLER/YENİLER/FAVORİLER değişmedi; yeni tarama ve playlist yazımı yok.


## 13 Kasım 2026 — #19 EPG yanlış kimlik ataması ve program zamanı koruması (PR #155)
- `v2/build_epg.py` artık yalnızca bire bir `tvg-id` eşleşmesini veya tek anlamlı normalize edilmiş EPG isim eşleşmesini kullanıyor. Aynı ada birden çok XMLTV kaynağı karşılık gelirse önceki gibi en çok programa sahip kaynağı seçip yanlış rehber atamıyor; eşleşme atlanıyor ve `ambiguous_entries_skipped` ile raporlanıyor.
- Rehber dışa aktarımında zaman damgaları `epg_integrity.parse_xmltv_time` ile ayrıştırılıyor. Geçersiz UTC ofseti, eksik/ters başlangıç-bitiş ve sıfır süreli programlar dışa alınmıyor; gerçek +0300 saat farkı göz önüne alınıyor.
- `v2/test_build_epg.py` yeni çevrimdışı testleri ve `.github/workflows/v2-main-production-safety-gate.yml` içinde zorunlu kabul bağlantısı eklendi.
- PR #155 merge commit `5ec41d2e98930f6610c592ccf458b6bcf8c694e9`; head `49dab604eae5a57640157512d2994818c58f392c`; Actions run `43479698309` SUCCESS. Stage 2/3 kimlik/EPG/kurtarma, Stage 5/6 paket ve arşiv, #34 çevrimdışı keşif ve ana İBO güvenlik korumaları SUCCESS.
- Bu yalnızca çevrimdışı EPG eşleştirme/yayınlama doğrulamasıdır; 303 EPG boşluğunun giderildiği, gerçek EPG kaynaklarının tamamının güncel olduğu veya #19 nihai kabulünün geçtiği anlamına gelmez. #19 açık kalır. Yeni kanal taraması yapılmadı; ana İBO, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi.

## 13 Kasım 2026 — #19 XMLTV program aralığı kabulü (PR #156)
- PR #156 squash merge `5842d47a3617ccd3bc523632144e0c0eaffc0b9d` ile `identity_metadata.verify_epg_ids` program uygunluğu için tekil XMLTV channel ID, iki geçerli UTC tarih/saat alanı ve `stop > start` şartlarını zorunlu kılar. EPG ID tam eşleşmesi ile geçerli program aralığı ayrı kanıtlar olarak tutulur.
- Eksik `stop`, geçersiz saat/ofset, ters/sıfır süreli aralık ve duplicate channel regresyonları eklendi. İlk PR denemesi Stage 2 test fixture'ında eksik `stop` nedeniyle FAIL oldu; fixture gerçek zaman aralığıyla düzeltildi. Son PR Actions `43480044886`: SUCCESS; ilgili Stage 2, Stage 3, Stage 5/6, #34 ve ana İBO korumalarının tamamı PASS. Merge sonrası ana dal run `43480208051`: SUCCESS.
- Gerçek XMLTV kaynaklarındaki 303 eksik eşleşme giderilmiş sayılmaz ve #19 görevi gerçek kaynak/kanal kanıtı olmadan kapatılmadı. Yeni tarama yok; ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi.


## 13 Kasım 2026 — Stage 5 FFmpeg decode kanıtı ve özel İBO koruması (PR #162)
- PR #162 squash merge `86fe138f793ff42148a34faa6b4ca249dc6ee65f`, ana dal güvenlik kapısı Actions `43480354832` SUCCESS; PR kabul koşusu `43480221367` SUCCESS.
- Kanıt dosyası yalnızca ffprobe akış başlıklarını taşımasıyla kabul edilmiyor: yerel FFmpeg framemd5 çıktısında hem görüntü kareleri hem ses örneklerinin gerçekten decode edilmesi gerekiyor. Kimlikte `tvg-id` ile `channel_id` eşitliği aranıyor.
- Dışa aktarım sadece yeni `private-*.m3u8` dosyasına, O_EXCL/O_NOFOLLOW + 0600 ile yapılır; korunan ana İBO, YEDEKLER, YENİLER, FAVORİLER üzerine yazma yok.
- Yanlış kimlik, sahte kanıt, çakışan dosya ve yalnız görüntü akışı regresyonları PASS. GitHub runner'da FFmpeg bulunmadığı için yerel klip entegrasyon testi SKIPPED; çevrimdışı mock regresyonları PASS. Gerçek 1.000/2.000 kanal paketleri veya cihaz AV kabulü yapılmadı; #31–#33 açık.


## 13 Kasım 2026 — Stage 5 (#31–#33) medya kanıtı tekilliği ve kabul
- PR #176 squash merge `1951340476326f5812072b1161b8795e2c5f04a2`; PR Actions run `43481008490` SUCCESS; merge sonrası main Production Security Gate run `43481158009` SUCCESS (Stage 5 regresyonları, Stage 2/3/6, #34 offline ve korunan İBO kontrolleri).
- `v2/stage5_evidence_export.py`: ayrı kanal kimlikleri aynı SHA-256 medya kanıtını iki kez kullanamaz. Geçersiz kütüphane hedef değerleri (0, negatif, boolean, >2000, metin) reddedilir. Üretim CLI hedefleri yalnızca 1000 ve 2000 olarak kalır.
- `v2/test_stage5_evidence_export.py`: iki farklı dosya adıyla aynı medya baytlarını yeniden kullanan iki kanal kimliği için fail-closed regresyon eklendi; testler gerçek kanal delili değildir.
- Eşzamanlı oturumların ana dala aldığı daha güçlü Stage 5 korumaları (yerel FFmpeg protocol whitelist, tvg-id/channel-id eşlemesi, private-*.m3u8, O_EXCL/O_NOFOLLOW ve 0600) korunmuştur. Eski kodu geri getirecek PR #165 ve PR #169 birleştirilmeden kapatıldı.
- Gerçek 1000/2000 AV/doğrulama paketi, harici bağımsız şifreli geri yükleme ve IBO cihaz kabulü hâlâ eksik. #31–#33 nihai kabul açık; 34 görevde 21 completed ve 13 in_progress. Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi ve yeni kanal taraması yapılmadı.


## 13 Kasım 2026 — Stage 5 yerel FFmpeg video+ses çözümleme testi zorunlu CI kabulü
- PR #177 squash merge `aa6b5b3f18b89c28a994a6f90484e18f879b14c1`. PR Actions `43481199861` SUCCESS; main Actions `43481413229` SUCCESS.
- GitHub Ubuntu runner'ında FFmpeg/FFprobe eksikse paketler kurulur. Yerel testte 1 saniyelik sentetik test medyası üretip gerçek decode üzerinden hem video frame hem ses örneği doğrulanır. `test_local_ffmpeg_decodes_both_real_fixture_tracks ... ok` ile bu kez atlanmadan geçti.
- Yalnızca test aracı için üretilen sentetik medya gerçek yayın veya gerçek İBO paketi kabul edilmedi. #31–#33 ve diğer gerçek yayın kanıtı bekleyen görevler açık. Yeni kapsamlı kanal taraması yapılmadı; ana İBO/YEDEKLER/YENİLER/FAVORİLER'e dokunulmadı.


## 13 Kasım 2026 — Stage 5 özel M3U çıktı koruması (PR #184)
- `v2/stage5_evidence_export.py` özel veya signed gerçek yayın URL'lerini içerebilen M3U test dosyalarının Git deposu içine, `v2/reports` dâhil, yazılmasını reddeder. Yalnızca depo dışındaki `private-*.m3u8` hedefler kabul edilir; `O_EXCL/O_NOFOLLOW` ve `0600` korumaları değişmedi.
- `v2/test_stage5_evidence_export.py` repo içindeki hedefin hiçbir dosya yaratılmadan reddedildiğini kontrol eder.
- PR #184 merge commit `c400b1f3aff3744c65f110e41629cabc5ed90596`; Actions run `43481525275` SUCCESS. Stage 2/3 kimlik/EPG, Stage 5 yerel FFmpeg video+ses decode, Stage 6 paket/arşiv, #34 offline ve ana İBO güvenlik kapıları geçti.
- Daha önce birleştirilen farklı kanalın aynı kanıt SHA-256'sını yeniden kullanamaması kuralı korunarak eşzamanlı Stage 5 değişiklikleriyle çakışma giderildi; PR #180 zorla birleştirilmeden kapatıldı.
- Bu altyapı güvenlik kabulü, mevcut 4.301 URL'lik M3U parçaları için gerçek cihaz oynatımı, bütün kanalların bağımsız AV/kimlik kabulü veya harici üretim geri yüklemesi anlamına gelmez. #28–#33 açık kalır. Yeni toplu tarama veya korunan İBO/YEDEKLER/YENİLER/FAVORİLER dosyası değişikliği yapılmadı.


## 13 Kasım 2026 — #19 farklı EPG kaynaklarında tekrarlanan XMLTV ID koruması
- PR #202 birleştirildi: `e5a233b8c281208b5ebc4662f741968002819d38`; PR CI `43484557050` SUCCESS, main CI `43484812015` SUCCESS.
- Aynı XMLTV channel ID birden fazla feed'de veya tek feed içinde birden fazla kez bildirilirse kanaldaki programlar eşleştirmeden çıkarılır. Bildirilmeyen program id'leri, XML DTD/ENTITY ve signed feed hata sorgu parametreleri reddedilir/redakte edilir. Yeni çevrimdışı regresyonlar PASS.
- Aynı PR'da #28–30'un eski test fixture'ındaki eksik `decoded_av_verified` ve `decode_status` alanları güncellendi; üretim kanıt standardı düşürülmedi.
- Gerçek EPG kaynak yayını taranmadı. 303 önceki EPG boşluğu ve bağımsız yayıncı kimliği kanıtı hâlâ açık. #19 completed yapılmadı. Ana İBO/YEDEKLER/YENİLER/FAVORİLER değişmedi.

## 13 Kasım 2026 — #19 ve Stage 6 kabul düzeltmeleri (son Actions)
- #19 EPG güvenliği: PR #172 merge `eb827b9c0bc4fe7eef507b8637ef37284be91dbd`; geçerli program aralığı/tekil XMLTV kimlik kanıtı ile ham EPG eşleşmesi ayrı raporlanır, DTD/ENTITY engellenir. PR Actions `43480892500`, main Actions `43481012343`: SUCCESS. 303 gerçek EPG açığı kaldı; #19 açık.
- Stage 6/M3U: PR #194 merge `8dff642a1e3d3dbf6b4aa133b323fc7bdfdfb7b6`, Unicode C1/format ayırıcılarla sahte M3U satır enjeksiyonunu ve şifreli JSONL envanterde bozuk türlerin paketi çökertmesini engeller. PR Actions `43483502608` SUCCESS.
- Ana dal run `43483992949` eşzamanlı yeni `decoded_av_verified + DECODED_AV` kabul kuralı nedeniyle geçersiz test fixture'ı üzerinden FAILED. Üretim kuralı gevşetilmeden PR #203 merge `70a6925566c37fdd7e31b85a3b7903790aacb1c0` ile test kanıtı düzeltildi; PR run `43484486032` ve main run `43484653370` SUCCESS.
- Kaydedilmiş gerçek 4.301 URL'lik M3U paket parçaları ve yapısal SHA/EXTINF denetimi, bütün kanalların güncel ses+görüntü/kimlik ve IBO cihaz kabulü değildir. #28–#33 açık. Kapsamlı yeni tarama ve ana İBO, YEDEKLER, YENİLER, FAVORİLER üzerinde yazma yapılmadı.
