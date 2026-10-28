# V2 güvenli toplu doğrulama iş planı

## Tamamlananlar
- Canlı IBO playlisti, favoriler ve iki özgün yedek korunur.
- GitHub/M3U kaynak listesi 17 kaynak olarak yapılandırıldı.
- Dünya çapında kaynak keşfi, Türkçe aday taraması, HTTP probe, kısa decoder, çözünürlük, kararlılık, logo ve EPG kontrolleri mevcut.
- YouTube canlı yayın keşfi ve metadata kontrolü mevcut.
- Arama workflow'u salt okunur; hiçbir aday otomatik canlı IBO listesine eklenmez.
- GitHub Actions concurrency kuyruğu çakışmaları azaltacak şekilde güncellendi.

## Öncelik sırası
1. Her çalışmanın Actions sonucu ve artifact raporunu kontrol et. Başarılı workflow ile doğrulanmış kanal sayısını karıştırma.
2. Her kaynak için erişim, toplam kanal, tekrar, canlı listede bulunan ve test edilen sayılarını raporla. Hatalı/ölü kaynakları işaretle; kaynak bulunması kanalın çalıştığı anlamına gelmez.
3. Adayların HTTP ve kısa video decoder kontrollerini kaynak bazında yap; uzun süreli kararlılığı ayrı değerlendir.
4. YouTube'da yalnızca resmî ve gerçekten canlı yayınları incele. YouTube watch URL veya süresi dolan imzalı HLS URL'lerini kalıcı IBO adresi gibi ekleme. Gerekirse yasal, güvenilir yenileme mekanizmasını ayrıca tasarla ve test et.
5. Kanal kimliği, yayın içeriği, çözünürlük, ses, logo, EPG ve doğru kategori eşleşmesini doğrula.
6. Kullanıcı onayından sonra yalnızca doğrulanan yeni kanalları önce ayrı test listesine, sonra uygun kategori ve ULUSAL-HEPSİ'ye aktar.
7. Son aşamada kategori sayaçları, favoriler, özgün iki YEDEKLER ve playlist güvenlik testlerini yeniden çalıştır.

## Kabul koşulları
- Mevcut canlı IBO, favoriler ve özgün iki YEDEKLER hiçbir keşif çalışmasında değişmez.
- Adaylar raporda; otomatik playlist yazımı yok.
- Eksik testler başarı gibi raporlanmaz.
- Her yayın için kaynak ve test kanıtı saklanır; token/özel URL'ler kamuya açık JSON raporlarında paylaşılmaz.

## 28 Ekim 2026 — birleşik keşif zinciri devir notu
- Yeni GitHub depo/M3U kaynak keşfi ana `V2 Turkish Stream End-to-End Discovery` workflow'unun ilk aşamasına bağlandı.
- `v2/github_source_discovery.py` raporu `v2/reports/github-source-discovery.json` üretir; `v2/discover.py` bu rapordaki en fazla 80 yeni HTTPS kaynağı yapılandırılmış 17 kaynakla birleştirir, M3U içindeki kanal kayıtlarını ayıklar ve canlı IBO'yu değiştirmeden aday raporuna alır.
- Ardından mevcut IPTV-org TR aday taraması, HTTP, ffprobe kısa decoder, çözünürlük, kararlılık, kalite karşılaştırması, resmî TV sitesi, YouTube canlı yayın, EPG, logo ve güvenlik testleri aynı workflow'da devam eder.
- Sınır: YouTube canlı yayın sayfaları henüz kalıcı IBO uyumlu akışa dönüştürülmez; kaynaklardan keşfedilen tüm kanallar henüz tek tek ffprobe doğrulamasına alınmaz. Bunlar sonraki entegrasyon işidir. Başarılı workflow bütün adayların çalıştığı anlamına gelmez.
- Canlı playlist, FAVORİLER ve özgün iki YEDEKLER korunur. Otomatik yayın ekleme kesinlikle yoktur.

## 28 Ekim 2026 — toplu test takip notu
- Birleşik tarama run 40605265927 kontrol edildi: kısa decoder doğrulaması aşamasında çalışıyordu; tamamlandı sonucu henüz doğrulanmadı.
- Kaynak bazında M3U kayıt sayısı, farklı stream URL sayısı ve kaynak erişim hatası `v2/reports/candidates.json` içindeki `source_audit` alanına eklendi. Bu geliştirme sonraki workflow çalışmasında doğrulanmalı.
- Kalan kritik işler: GitHub'dan keşfedilen her yeni kaynak için kanalların ayrı playback testlerine girmesi; YouTube resmî canlı yayınları için IBO'da sürdürülebilir adres yöntemi; tüm raporların birleştirilmiş kabul özeti.
- Arama işlemleri canlı IBO ve özgün YEDEKLER'e otomatik yazamaz.

## 28 Ekim — hızlandırılmış kabul sırası
1. **Tamamlandı (kod):** GitHub kaynak keşfi + 17 kayıtlı kaynağı birleşik aday havuzuna alma; kaynak bazında sayım ve hata raporu.
2. **Tamamlandı (kod; Actions sonucu bekleniyor):** `v2/all_source_playback.py` her erişilebilir M3U kaynağından en fazla dört yeni URL seçer, toplam 100 akışı ffprobe ile kısa video/ses/çözünürlük kontrolüne sokar. Kaynak başına ve URL hash'i bazında rapor üretir; bu **örnekleme**, tüm yayınların doğrulanması değildir.
3. **Devam eden:** Birleşik workflow'un bütün aşamalarının tamamlanması, artifact raporları ve canlı playlist güvenlik testlerinin kontrolü.
4. **Eksik:** Örneklemeyi kademeli tam kapsama yükseltmek (maliyet/süre/kota kontrolü); bütün adaylar için kimlik, içerik, kararlılık ve tekrar doğrulaması.
5. **Eksik:** YouTube için resmî canlı yayın ve yenilenebilir/kalıcı IBO uyumlu kaynak bulma; watch URL veya geçici imzalı HLS kalıcı yayın diye eklenmeyecek.
6. **Kabul:** Tek özet, başarısızlıkların ayrı listesi, manuel onaydan önce canlı playlistte sıfır değişiklik.

## 28 Ekim 2026 — test sonuçları ve kalan öncelikler
- Run 40606347272: V2 Turkish Stream End-to-End Discovery **success**; 40605519678: Health and Discovery **success**; 40605519505: Worldwide Channel Discovery **success**; 40604652483: GitHub source discovery **success**. Workflow başarısı tüm stream'lerin canlı olduğu anlamına gelmez.
- `v2/all_source_playback.py` ana workflow'da mevcut: yapılandırılmış + GitHub'da bulunan kaynaklardan kaynak başına en fazla 4, toplam en fazla 100 yeni stream'i ffprobe ile örnekler; **bütün kanalların testi değildir**.
- `v2/final_validation_summary.py` artık kaynak erişimi, GitHub yeni M3U dosyaları, aday sayısı, örneklenen stream ve video doğrulama sayılarını tek raporda toplar. Değişiklik yeni Actions koşusunda doğrulanacak.
- Öncelik 1: En yeni Actions run'ın sonucunu ve `final-validation-summary.json` içeriğini doğrula; hata varsa düzelt.
- Öncelik 2: Kaynakların tüm adayları için bütçeli, parçalara bölünmüş HTTP/ffprobe taraması ve tekrar denemeleri; kaynak bazlı tam kapsam sayacı. 100 örneklemi tüm yayın testi diye sunma.
- Öncelik 3: Resmî YouTube canlı yayınları için sürdürülebilir, yetkili IBO-uyumlu akış çözümü; imzalı geçici URL'yi kalıcı playlist'e ekleme.
- Öncelik 4: Kimlik, içerik, ses/video, gerçek çözünürlük, EPG, logo, kararlılık ve kategori kanıtlarıyla ayrı test listesi oluştur.
- Öncelik 5: Kullanıcı onayından sonra canlı listeye güvenli ekleme; 840 giriş, 13 kategori, FAVORİLER ve özgün iki YEDEKLER başlangıç bütünlüğünü koru.

## 28 Ekim — tek komut test listesi entegrasyonu
- `v2/build_verified_test_playlist.py` eklendi: kısa decoder ile video kanıtı olan, canlı IBO'da aynı URL ile bulunmayan adaylardan ayrı `v2/reports/short-decoded-review-only.m3u8` üretir. Bu liste **geçici inceleme listesidir**, kanal kimliği ve uzun süreli çalışma henüz kesin değildir.
- Ana birleşik workflow bu listeyi otomatik üretir ve artifact olarak sunar; kullanıcıya yedi ayrı komut gerekmez.
- Öncelik: yeni workflow'un sonucunu kontrol et, ardından tam kapsamlı parçalı yayın doğrulaması ve YouTube kalıcı uyumunu tamamla. Korunan canlı listeye otomatik ekleme yoktur.

## 28 Ekim — dört parçalı test sonuçları
- Run 40660958068: **success**, dört shard'ın artifact'ı da mevcut (0,1,2,3). Bu başarı adayı doğrulanan kanal sayısına eşit değildir; raporların içindeki `sampled` ve `video_decoded` sayıları ayrıca okunmalıdır.
- Run 40660159911: **success**; ayrı `short-decoded-review-only.m3u8` üretimi dahil birleşik zincir başarıyla bitti, artifact mevcut.
- Run 40660910249: son kontrol sırasında **in_progress**; sonuç bekleniyor.
- Sonraki öncelik: dört shard raporunu tek kabul özetine birleştirmek, kapsam dışı aday sayısını hesaplamak, eksik kanalları sonraki partilere almak, YouTube IBO kalıcılığı ve kimlik/EPG/logo eşleştirmelerini kanıtlamak.
- Canlı IBO, FAVORİLER ve YEDEKLER'e otomatik yazma yok.

## 28 Ekim — ölçülmüş toplu doğrulama sonucu
- Run 40662300708 dört playback shard ve aggregate işleri **success**. Aggregate job logu: **1.000 farklı URL hash'i test edildi, 414'ünde video doğrulandı, 586'sında video doğrulanamadı**. Bunlar kanal kimliği veya kalıcı yayın garantisi değildir.
- Run 40660910249 birleşik kanal arama **success**; 40660159911 ayrı inceleme playlisti dahil **success**.
- Sıradaki iş sırası: (1) test edilmemiş adayların kapsama hesabı ve sonraki partiler; (2) 586 başarısızın kontrollü tekrar denemesi; (3) 414 görüntülü adayın ses, kimlik, çözünürlük, EPG/logo ve kararlılık doğrulaması; (4) resmî YouTube IBO uyumluluğu; (5) yalnızca kanıtlı adayların ayrı onay listesi. Canlı IBO'ya otomatik aktarım yok.

## 28 Ekim 2026 — YENİ SOHBETE DEVİR / TEK KOMUT ÖNCELİĞİ
**Kullanıcının kesin talebi:** Yalnızca **"Kanalları ara"** demesi yeterli olacak. Ayrı "ara", "test et", "EPG kontrol et", "liste oluştur" komutları istemiyor. Tek tetikleme altında keşif → tüm yeni adayların bütçeli/parçalı doğrulaması → başarısız tekrar denemesi → ses/görüntü/çözünürlük/kimlik/kararlılık → EPG/logo/kategori/tekrar kontrolü → ayrı IBO inceleme listesi → tek sonuç raporu **otomatik ve sıralı** tamamlanmalı. Ayrı test workflow'larını sürekli tetiklemek çözüm değildir. **Sonraki asistan önce bunu ana birleşik workflow'a bağlamalı; yeni bağımsız test workflow'u açmamalı.** Kullanıcı kısa ve net Türkçe ilerleme istiyor; gereksiz aşama anlatılmasın.

**Güvenlik:** Ana repo `Madsc55/MADSC55-TV-V2`, main. Canlı `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, FAVORİLER, YEDEKLER'deki iki özgün TRT 1 1440P QHD ve DHA CANLI 720P HD korunacak; otomatik canlı playlist değişikliği veya yeni kanal importu yok. Ayrı test listesi salt okunur keşif çıktısı. YouTube watch URL/geçici imzalı HLS'yi kalıcı IBO yayını diye ekleme.

**Mevcut kod:** Ana workflow `.github/workflows/v2-turkish-stream-review.yml` kaynak/GitHub/YouTube/resmî site/EPG/logo keşfini ve 100 örnek ffprobe testini, TR kısa decoder, inceleme listesini, güvenlik testlerini çalıştırıyor. `v2/build_verified_test_playlist.py` geçici `v2/reports/short-decoded-review-only.m3u8` oluşturuyor (tam doğrulanmış sayılmamalı). Ayrı `.github/workflows/v2-batched-playback.yml` 4 shard × 2 page, shard başına 250 örnek kapasitesi; `v2/all_source_playback.py` shard ve `PLAYBACK_PAGE` destekliyor; `v2/aggregate_playback_shards.py` kanıtları birleştiriyor. **Ancak bu sekizli toplu kontrol henüz ana tek komutlu workflow'a bağlanmadı.** Ana eksik budur.

**Doğrulanmış sonuç:** run 40662300708 success, 1.000 farklı URL test, 414 VIDEO_DECODED, 586 video doğrulanamadı. Bu sonuç bütün adayları veya 414 tam onaylı kanalı ifade etmez. run 40660159911 ve 40660910249 birleşik workflow success. 
**28 Ekim son kontrol:** 40665346855 batched playback **failure**; 40665323600 **success**; 40665377633 **in_progress**; 40665323555 birleşik **in_progress**; 40665873146 birleşik **pending**. Bunların sonuçlarını yeniden kontrol et, başarısız işin logunu inceleyip düzelt; başarı varsayma.

**Yeni sohbette kesin iş sırası:**
1. Son Actions run'larını ve 40665346855 hatasını incele; hatayı düzelt.
2. Ana `V2 Turkish Stream End-to-End Discovery` workflow'unda tek tetiklemeyle toplu sayfalı/shard yayın testlerini başlat, bağımlılıkla bekle, tek aggregate raporu üret; kaynak keşfi ile toplu testin aynı aday anlık görüntüsünü kullanmasını sağla. Yinelenen pahalı işlerden kaçın.
3. 414 görüntülü adayın ses, kimlik, kararlılık, EPG/logo/kategori kontrollerini ve 586 başarısızın sınırlı tekrar denemesini otomatik zincire ekle. Tüm adayların kapsanmadığı durumlarda eksik sayısını açıkça raporla.
4. Ayrı geçici IBO test listesi ve tek nihai kanıt raporu üret; YouTube kalıcı uyumluluğunu ancak yetkili sürdürülebilir akış varsa onayla.
5. Tek komut çalıştır, bitişini kontrol et, gerçek sayı ve güvenlik sonucunu kullanıcıya kısa bildir; WORK_PLAN.md'yi güncel tut.

**Önemli:** Son kullanıcı bu sohbetin dolduğunu, yeni sohbete geçip hiçbir şeyi unutmadan devam etmek istediğini söyledi. Yukarıdaki hedef ve eksikler devir notudur.

## 28 Ekim 2026 — yeni sohbet Actions kontrolü
- `49cc5a9` commit'i ana `.github/workflows/v2-turkish-stream-review.yml` dosyasına 4 shard × 2 page playback matrix, artifact indirme ve aggregate adımını **eklemiş**. Önceki devir notundaki 'henüz bağlanmadı' ifadesi artık güncel değil.
- Run `40665873146` son kontrolde **pending**; run `40665323555` **in_progress**. Bunlar tamamlandı veya başarılı diye sunulamaz.
- Eski toplu run `40665346855` **failure**: sekiz playback işi success, `aggregate` işinin `Merge and validate shard evidence` adımı failure. `40665377633` sonraki toplu run **success**. Eski hatanın kök sebebi log olmadan kesinleştirilemez.
- Ana workflow hâlâ her shard içinde GitHub kaynak keşfini yeniden çalıştırıyor; aynı aday snapshot'ı garanti edilmiyor. Ayrıca `review` job'u `if: always()` ile eksik/başarısız shard sonrasında da başlayabiliyor. Öncelik: tek keşif artifact'ı paylaşımı, başarısız shard'ı açık raporlama, bütçeli tekrar denemesi, gerçek kapsama ve metadata doğrulaması.
- Canlı IBO, FAVORİLER ve iki özgün YEDEKLER'e yazma yapılmadı.

## 28 Ekim — kullanıcı ekran görüntüsü ve hata düzeltmesi
- Run `40665346855` aggregate logu kesin hata: `Duplicate shard index: 0`; 8 playback job success. Sonraki run `40665377633` success.
- `v2/aggregate_playback_shards.py` artık shard anahtarını `(page, shard_index)` olarak sayısal normalleştiriyor ve eksik shard indeksini açık hata olarak raporluyor (commit `09a9eb0`).
- Ana workflow 8 playback matrix ve review aggregate zincirini zaten içeriyor. Tek komutun tüm kabul koşulları henüz tamamlanmadı: aynı keşif snapshot'ı, başarısızların retry, tam kapsam ve aday metadata kanıtı eksik. Ayrı workflow'ları tetikleyerek çözüm üretme.

## 28 Ekim — toplu zincir sağlamlaştırma
- Ana birleşik workflow'da sekiz playback shard başarısızsa review artık `if: always()` ile devam etmiyor; yanlış başarılı rapor önleniyor (commit `5182c4c`).
- `final_validation_summary.py` sekiz shard'ın `all-source-playback-aggregate.json` sonucunu öncelikli okuyor; toplam farklı test, decoded, not decoded ve batch bilgilerini raporluyor (commit `36b2546`). Önceki tek `all-source-playback.json` dosyasını zorunlu sanma hatası giderildi.
- Son kontrol: birleşik run `40666379703` pending; `40665873146` pending; `40665323555` in_progress. Başarı teyidi yok.
- Sıradaki eksikler: tek kaynak snapshot'ı, bütçeli başarısız retry, tüm aday kapsama ve aday başına metadata/kimlik/kararlılık doğrulaması. Canlı playlist'e dokunma.

## 28 Ekim — kesin tek birleşik görev kabul sözleşmesi
Kullanıcı talebi: tek tetikleme, tüm kaynakları tara, tüm adayları listele; aday başına kimlik, oynatma, ses, video, EPG, logo, kategori kontrolü; başarısızları 3 kez yeniden dene; eksik kaynakları yeniden tara; ara rapor yayımlama; yalnızca finalde `approved`, `rejected`, `pending_review` ayrımlı tek rapor; tüm işler tamamlanmadan workflow success verme.
Mevcut ana workflow bu sözleşmeyi henüz tam uygulamıyor: 4x2 sınırlı örnekleme, kaynak snapshot farkları, yalnızca sınırlı kararlılık örneği ve kimlik kanıtı eksik. Kısmi örneklem başarı değildir. Sonraki kod değişiklikleri mevcut `.github/workflows/v2-turkish-stream-review.yml` içinde yapılmalı; bağımsız test workflow'u oluşturulmamalı. Canlı IBO, FAVORİLER ve iki özgün YEDEKLER salt okunur.
