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
