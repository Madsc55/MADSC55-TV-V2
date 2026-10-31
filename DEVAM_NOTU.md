# MADSC55 TV V2 — TEK DEVAM NOTU

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


## 31 Ekim 2026 — Toplu kaynak keşfi geliştirme dalı / PR #9
- Güvenli çalışma dalı: `madsc/v2-discovery-bulk-20261031`; **draft PR #9**, merge YOK. Ana playlist/YEDEKLER/YENİLER/FAVORİLER/cihaz favorileri ve eski repo değiştirilmedi.
- `v2/webpage_source_discovery.py`: herkese açık HTTPS HTML sayfalardan sadece `.m3u`/`.m3u8` linklerini ayrıştıran bağımsız adaptör; URL kimlik bilgisi, HTTP ve özel portlar reddedilir. `v2/test_webpage_source_discovery.py`: çevrimdışı güvenlik testleri.
- `v2/discover.py`: `kind=html` kaynakları için sayfadaki en fazla 30 playlist linkini keşfeder, ayrı kaynak kimliği ve kaynak audit kaydı üretir; HTML asla oynatılabilir kanal sayılmaz. Henüz kaynak konfigürasyonuna doğrulanmamış HTML URL eklenmedi; gerçek uçtan uca tarama yapılmadı.
- `.github/workflows/v2-ordered-preflight.yml`: yeni HTML testi sıralı discovery-tests aşamasına eklendi; `pull_request` tetikleyicisi de eklendi. PR #9 açıldı; commit üzerinden yapılan ilk workflow sorgusunda henüz run dönmedi. CI başarısı doğrulanmadı.
- Kalan: gerçek kaynak URL'lerinin doğrulanması ve adaptör envanteri, şifreli kalıcı URL arşivi + gerçek restore kanıtı, Actions sonuçlarının incelenmesi, tam kaynak taraması. Merge yapma; güvenli arşiv olmadan gerçek kanal taraması yapma.


## 31 Ekim 2026 — M3U EXTINF ayrıştırma düzeltmesi
- `v2/discover.py` (`c170c43`): kanal adında virgül olduğunda `rsplit` ile adın kaybolmasını önler; tırnak içindeki grup virgüllerini atlayıp ilk tırnak-dışı virgülü kanal adı ayıracı kabul eder.
- `v2/test_discovery_offline_regressions.py` (`ba7bbbf`): `group-title="News, Turkey"` ve `Channel, Extra` örneği ile çevrimdışı regresyon testi. Ordered-preflight discovery-tests aşamasında çalışacak.
- Çalıştırma sonucu henüz doğrulanmadı. Draft PR #9 açık; merge yapılmadı. Ana playlist ve YEDEKLER değiştirilmedi.


## 31 Ekim 2026 — Kaynak kaybı ve güvenli snapshot düzeltmeleri
- `cf417943`: TR/AZ kaynaklarındaki dolu `tvg-id` değerleriyle dünya kaynaklarındaki aynı kanal kimliğini eşleştirerek yalnızca adında Türkçe anahtar kelime olmayan dünya varyantlarının elenmesini azaltır. Sadece TVG ID eşleştirilir; genel kanal adları üzerinden kör kabul yapılmaz.
- `8ec7a155`: dünya eşleşmesi ve genel ad yanlış pozitifleri için iki çevrimdışı regresyon testi.
- `68521ae8`: şifrelenmemiş token içeren `--snapshot-output` üretimini güvenli arşiv/restore tamamlanana kadar fail-closed kapatır. Bu seçenek şimdi açıkça CLI hata koduyla durur.
- Bu çalışma gerçek tarama veya eski #60 sayısına geri dönüş kanıtı değildir. Testlerin yeni commit üzerinde başarı durumu ayrıca doğrulanmalı; PR #9 merge edilmedi. Eski depo ve ana playlist korunuyor.


## 31 Ekim 2026 — IPTV-org kaynak genişletmesi
- `0fcad824`: IPTV-org resmî PLAYLISTS.md dokümanında belirtilen `raw/tr`, `raw/az`, `sources/tr`, `sources/az`, Central Asia, West Asia, International ve Worldwide olmak üzere 8 ek keşif girdisi; toplam statik kaynak 40. URL yapıları belgelenmiştir; her uç noktanın canlı HTTP erişimi bu commit ile doğrulanmamıştır.
- `e3d8a093`: yalnızca public HTTPS M3U kaynakları veya konfigürasyonda `kind=html` olarak açıkça belirtilmiş public HTTPS sayfalar kabul edilir. `localhost`/private IP kaynağı engeli.
- `--snapshot-output` şifreli arşiv kurulana dek kapalıdır. Canlı kaynak taraması ve playback testi yapılmadı. Ana İBO playlist, YEDEKLER ve eski repo korunur. PR #9 merge edilmedi.


## 31 Ekim 2026 — GitLab/Codeberg genel keşif
- `v2/forge_source_discovery.py`: kamuya açık GitLab ve Codeberg proje sonuçları ile açıkça listelenmiş M3U/M3U8 dosya yollarını ayrıştıran, sınırlı ve salt-okunur adaptörler.
- `v2/run_forge_source_discovery.py --scan-public-forges`: API aramalarını çalıştıran isteğe bağlı komut; `v2/reports/forge-source-discovery.json` içine yalnızca kaynak referanslarını, hata ve proje sayısını kaydeder. Otomatik playlist aktarımı yoktur; GitLab API raw URL'leri mevcut M3U fetch izin listesine otomatik dahil değildir.
- `v2/test_forge_source_discovery.py`: beş çevrimdışı test, sıralı CI'a eklendi.
- Önceki GitHub Actions #41189996226 dört aşamada PASS; bu yeni modüller için Actions sonucu ayrıca bekleniyor. Gerçek forge taraması henüz çalıştırılmadı. Ana İBO playlist ve YEDEKLER korunur; PR #9 merge edilmedi.


## 31 Ekim 2026 — Şifreli arşiv altyapısı
- `v2/encrypted_archive.py`: AES-256-GCM ile her kayıt için rastgele nonce, doğrulamalı şifreleme, append-only JSONL, 0600 dosya yetkisi, fsync ve doğrulamalı restore.
- `v2/test_encrypted_archive.py`: şifreli roundtrip, ekleme, URL token gizliliği, bozulma ve yanlış anahtar testleri. CI discovery-tests aşamasına `cryptography` kurulumu ve test eklendi.
- `v2/discover.py --encrypted-archive PATH`: eski şifresiz `--snapshot-output` kapalı kalır; şifreli arşiv seçeneği eklenmiştir. Tarama öncesi `V2_ARCHIVE_KEY_HEX` ve `archive_acceptance_gate.check()` ile bağımsız kalıcı yedek/restore kanıtı zorunlu; başarısız kaynak setinde arşiv reddedilir. Gerçek arşiv restore onayı ve canlı tarama henüz yapılmadı.
- PR #9 merge edilmedi; ana IBO playlist, YEDEKLER, YENİLER, FAVORİLER korunur.


## 31 Ekim 2026 — YouTube ve resmî web canlı yayın referansları
- `v2/live_page_discovery.py`: HTML'deki YouTube canlı kanal/video sayfalarını ve canlı yayın sayfası bağlantılarını salt-okunur olarak ayıklar. Sonuçlar yalnızca referanstır; oynatılabilir IPTV URL veya yayın çalışıyor kanıtı değildir.
- `v2/test_live_page_discovery.py`: çevrimdışı YouTube, resmî sayfa, tekrar, private IP, credential ve HTTP güvenlik testleri; CI'a eklendi.
- Henüz canlı site tarayıcısına bağlanmadı, resmî kanal sahipliği doğrulanmadı, gerçek YouTube canlı durum kontrolü yapılmadı. Bu adımlar açık kalır.


## 31 Ekim 2026 — Kritik keşif veri kalitesi ve arşiv düzeltmeleri
- `dearbulut-online` dünya listesi `scope=TR` yerine `scope=world`: yabancı kanalların topluca Türk kanalı sayılması engellendi. Kaynak sözleşmesine regresyon testi eklendi.
- `discover.py` içinde devre dışı bırakılmış olsa da kalan şifresiz `private-playback-snapshot.json` yazma kodu tamamen kaldırıldı.
- Şifreli arşive symlink üzerinden yazma reddedildi; regresyon testi eklendi.
- Önceki YouTube/web keşif değişiklikleri GitHub Actions #41190479762: SUCCESS. Yeni düzeltmelerin CI doğrulaması ayrıca bekleniyor.
- Canlı tarama, şifreli yedek restore kanıtı ve oynatma testi henüz yapılmadı. Ana İBO playlist, YEDEKLER, YENİLER ve FAVORİLER korunuyor; PR #9 merge edilmedi.


## 31 Ekim 2026 — GitLab/Codeberg keşif sonuçlarını kontrollü bağlama
- `v2/forge_source_review.py`: kamuya açık GitLab raw API ve Codeberg M3U URL'lerini güvenli biçimde doğrulama, tekilleştirme ve sadece SHA256 onayı olan kaynakları seçme.
- `v2/discover.py`: `v2/reports/forge-source-discovery.json` raporunu okuyabilir; yalnızca `v2/config/approved-forge-source-sha256.json` içindeki tam URL SHA256 onayı olan girdileri aday kaynak listesine ekler. Varsayılan onay listesi boş, otomatik aktarım yok.
- `v2/test_forge_source_review.py` beş çevrimdışı test CI'a eklendi. Önceki CI #41190601977 SUCCESS; bu değişikliklerin sonucu henüz ayrıca doğrulanmadı.
- GitLab/Codeberg canlı taraması henüz yapılmadı; kanal oynatma doğrulaması yapılmadı; PR #9 merge edilmedi. Ana playlist ve YEDEKLER korunur.


## 31 Ekim 2026 — Kaynak erişilebilirliği ön kontrolü
- `v2/source_availability_audit.py --audit-public-sources`: kaynak dosyalarının HTTPS/HTTP durumunu ve ilk 1024 bayttaki M3U başlığını kontrol eder; stream URL'lerine bağlantı kurmaz, kaynak URL/token değerlerini rapora yazmaz.
- Redirect güvenlik kontrolü, HTTP hata ayrımı ve `v2/test_source_availability_audit.py` testleri CI'a eklendi.
- Bu araç gerçek yayın testi değildir. Kaynak denetimi henüz çalıştırılmadı; şifreli arşiv onayı, toplu kanal taraması ve IBO testleri açık kalır.
- Önceki CI #41190756178 SUCCESS; yeni kod için CI henüz doğrulanmadı. Ana playlist/YEDEKLER korunur; PR #9 merge edilmedi.


## 31 Ekim 2026 — Manuel gerçek kaynak denetimi hazırlığı
- `.github/workflows/v2-manual-source-audit.yml`: yalnızca elle başlatılan, ayrı `source availability` ve `GitLab/Codeberg` genel kaynak referansı taramaları; 20 dk iş süresi, read-only izinler, 14 günlük rapor artifact'ları. Otomatik kanal yayın testi veya playlist değişikliği yok.
- `discover.fetch` açıkça incelenmiş GitLab raw M3U API uç noktalarını kabul eder; özel ağ/HTTP kaynaklarını reddeden `v2/test_fetch_source_gate.py` CI'a eklendi.
- Önceki CI #41191157932 SUCCESS. Bu yeni değişiklikler için CI henüz doğrulanmadı; manuel workflow henüz çalıştırılmadı.
- Önemli: gerçek source-audit ve forge taraması için GitHub Actions arayüzünden manuel dispatch gerekir; mevcut araçlarla dispatch yapılmadı. Ana İBO playlist ve YEDEKLER korunur; PR #9 merge edilmedi.


## 31 Ekim 2026 — API/HTML keşif giriş güvenliği
- Önceki CI #41191731166 dört aşamada başarılı.
- `v2/run_forge_source_discovery.py`: GitLab/Codeberg API çağrıları sadece güvenilir HTTPS hostlarına yapılır; farklı hosta/HTTP'ye yönlendirmeler reddedilir. `v2/test_forge_api_safety.py` testleri CI'a eklendi.
- `v2/webpage_source_discovery.py`: HTML index sayfasının kendisi de public HTTPS, portsuz/443, credential'sız ve fragment'sız olmalı; regresyon testi eklendi.
- Bu güvenlik düzeltmeleri henüz gerçek dış ağ taraması değildir. Manuel Actions workflow henüz başlatılmadı; sonuçlar ve şifreli arşiv restore kanıtı bekleniyor. Ana İBO playlist ve YEDEKLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Şifreli arşiv geri yükleme dosya güvenliği
- Önceki CI #41191926265 SUCCESS.
- `v2/encrypted_archive.py`: geri yüklemede symlink reddi, `O_NOFOLLOW`, sadece normal dosya ve sahibine özel izinler (0600) şartı; yazmada da normal dosya kontrolü.
- `v2/test_encrypted_archive.py`: symlink restore ve 0644 izinli restore reddi testleri eklendi.
- Bu değişikliklerin CI sonucu henüz kontrol edilmedi. Bağımsız dayanıklı yedek/restore kanıtı hâlâ gerekli; gerçek tarama başlamadı. Ana İBO playlist ve YEDEKLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Tek komutla kaynak keşfi koordinatörü
- Önceki CI #41192434838 SUCCESS.
- `v2/run_all_discovery.py --run-all --encrypted-archive <private-path>` eklendi. Sıra: 1) kayıtlı kaynak erişilebilirliği, 2) GitLab/Codeberg kamuya açık kaynak referans keşfi, 3) şifreli arşiv zorunlu M3U aday taraması; isteğe bağlı `--previous-report` ile kayıp denetimi.
- Ağdan önce bağımsız restore kanıtı `archive_acceptance_gate.check()` ve AES anahtarı doğrulanır. Aşama başarısızsa devam edilmez. Varsayılan forge onay listesi boş olduğundan yeni keşfedilen forge URL'leri otomatik oynatılabilir sayılmaz.
- `v2/test_run_all_discovery.py` sıralama, fail-closed, onay önkoşulu ve başarı akışı testleri CI'a eklendi.
- ÖNEMLİ EKSİK: YouTube/resmî canlı sayfa keşfi, GitHub/Gist yeni keşfi, oynatma testi, cihaz test grupları bu tek komut akışına henüz dahil değildir. Tam kapsamlı arama olarak tanıtılmamalıdır. Gerçek çalıştırma yapılmadı; CI sonucu yeni commit için bekleniyor.
- Ana İBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Dünya kaynaklarındaki TR/AZ alternatiflerini koruma
- Önceki tek-komut CI #41192597596 SUCCESS.
- `v2/discover.py`: TR/AZ kaynaklarından bilinen tvg-id kimlikleri tek fonksiyonda toplanıyor; dünya listelerinde aynı tvg-id'ye ait alternatif yayın adresleri artık yalnızca rapora değil, şifreli arşive de yazılıyor. Genel isimli, kimliği eşleşmeyen dünya kanalları kabul edilmiyor.
- `v2/test_cross_source_archive_parity.py` ve sıralı CI testi eklendi.
- `v2/encrypted_archive.py` restore tüm şifreli dosyayı `readlines()` ile belleğe yüklemek yerine satır satır doğruluyor.
- Son commit CI henüz doğrulanmadı. Gerçek tam tarama ve bağımsız yedek/restore kanıtı bekliyor. Ana İBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Canlı sayfa/YouTube referans keşfi tek komuta bağlandı
- Önceki düzeltme CI #41193528343 SUCCESS; #98 test hatası düzeltildi.
- `v2/run_live_page_discovery.py` ve boş, onay gerektiren `v2/config/live-pages.json` eklendi. Açıkça onaylı public HTTPS sayfalardaki YouTube ve canlı sayfa bağlantıları sadece SHA256/kind olarak raporlanır; URL tokenları rapora yazılmaz, oynatılabilir kanal sayılmaz.
- `v2/run_all_discovery.py` sırası artık: kaynak erişim kontrolü, GitLab/Codeberg keşfi, onaylı canlı sayfa referans keşfi, şifreli M3U aday taraması. Offline testleri CI'a eklendi.
- KAPSAM SINIRI: `live-pages.json` şu anda boş; dolayısıyla gerçek resmî site/YouTube kapsamı henüz oluşmadı. GitHub/Gist yeni kaynak keşfi ve otomatik stream playback testi hâlâ eksik. Arşiv restore kanıtı olmadan gerçek tarama başlamaz. Yeni CI sonucu henüz doğrulanmadı.
- Ana İBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Kapsamı yanlış tamamlandı göstermeme
- CI #41193892945 kontrol sırasında compile/protect/discovery-tests SUCCESS; safety henüz çalışıyordu.
- `v2/run_live_page_discovery.py`: boş resmî canlı sayfa onay listesi raporda `NO_APPROVED_PAGES` olarak görünür. 100 sayfa üstü sessizce kesilmez, tarama reddedilir.
- `v2/run_all_discovery.py`: şifreli arşiv hedefinin normal dosya olması da zorunlu; dizin hedefi reddedilir.
- İki regresyon testi eklendi. Yeni CI sonucu henüz doğrulanmadı. Gerçek kaynak taraması yapılmadı; onaylı canlı sayfa listesi boş, bağımsız yedek/restore kanıtı bekliyor.
- Ana İBO playlist ve YEDEKLER değişmedi, PR #9 merge edilmedi.


## 31 Ekim 2026 — GitHub kaynak keşfi tek komuta bağlandı
- Önceki CI #41193990362 SUCCESS.
- Mevcut `v2/github_source_discovery.py` GitHub M3U kaynak tarayıcısı `v2/run_all_discovery.py` akışına ikinci aşama olarak bağlandı. Artık sıra: erişilebilirlik, GitHub, GitLab/Codeberg, onaylı canlı sayfa referansları, şifreli M3U aday keşfi.
- GitHub API çağrılarında HTTPS api.github.com hostu, güvenli yönlendirme ve 2MB yanıt sınırı eklendi. `v2/test_github_source_safety.py` ve koordinatör sıra testleri CI'a eklendi.
- SINIR: GitHub/Gist tam kapsamı garanti edilmez; GitHub mevcut repo arama tarayıcısı Gist API aramasını ayrı yapmıyor. GitHub arama sonuçlarında 320 repo/320 dosya sınırı var. Onaylı canlı sayfa listesi hâlâ boş; restore kanıtı ve gerçek tarama henüz yok. Son CI sonucu doğrulanmadı.
- Ana IBO playlist ve YEDEKLER değişmedi, PR #9 merge edilmedi.


## 31 Ekim 2026 — GitHub Gist kaynak keşfi
- Önceki CI #41199407417 SUCCESS.
- `v2/github_source_discovery.py`: ilgili GitHub depo sahiplerinin herkese açık Gist metadata uç noktasından `.m3u/.m3u8/.txt` kaynaklarını aday olarak keşfetme eklendi. En fazla 30 sahibi ve mevcut 320 dosya üst sınırını kullanır. Adaylar doğrudan IBO listesine eklenmez.
- KAPSAM: Gist genel arama API'si olmadığı için yalnızca ilgili repo sahiplerinin public Gist'leri taranır; tüm Gist'ler taranmış sayılmaz. Son değişikliğin CI sonucu henüz doğrulanmadı; gerçek dış ağ taraması henüz çalıştırılmadı.
- Ana IBO playlist ve YEDEKLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Eksik kaynak taramasını başarı saymama
- Önceki CI #41199619053 SUCCESS.
- GitHub/Gist ve GitLab/Codeberg tarayıcıları, kaynak/API hataları rapora kaydedildikten sonra artık başarısız çıkış koduyla durur; birleşik koordinatör sonraki aşamaya geçmez. Önceden kısmi kaynak taraması başarılıymış gibi devam edebiliyordu.
- `v2/test_partial_scan_fail_closed.py` CI'a eklendi. Yeni CI sonucu henüz doğrulanmadı.
- KAPSAM: Ağ geçici hataları birleşik taramayı durdurabilir; güvenli tekrar deneme/işaretleme ve kalıcı keşif rapor arşivi henüz eksik. Gerçek tarama ve bağımsız restore kanıtı yok.
- Ana IBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Şifreli restore kanıtı güvenliği
- Önceki CI #41200181346 SUCCESS.
- `v2/archive_acceptance_gate.py` artık kanıt JSON'u için sembolik bağlantıyı reddeder; geri yüklenen şifreli arşiv için de sembolik bağlantıyı ve owner-only olmayan dosya izinlerini reddeder.
- `v2/test_restore_evidence_safety.py` CI'a eklendi; yeni CI sonucu henüz doğrulanmadı.
- Kalan kritik işler: kanıt dosyası bayrakları kendi başına bağımsız yedek varlığını kanıtlamaz; gerçek harici depolama/restore denemesi ve onay gereklidir. Gerçek toplu tarama yapılmadı. Onaylı canlı site listesi boş, playback testi eksik.
- Ana IBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — CI #41201107681 hata düzeltmesi
- `discovery-tests` FAILURE: `test_archive_acceptance_gate.py` test fikstürü geri yükleme dosyasını varsayılan 0644 izinleriyle oluşturuyordu; yeni güvenlik kapısı 0600 istiyor. Eksik dosya hata mesajı da değişmişti.
- Fikstür 0600 yapıldı ve eksik dosya beklentisi güncellendi; güvenlik kapısı gevşetilmedi. Düzeltme commit: a3d634065dd8f2e36f7ddd0b53d9fa439c35b7de.
- Yeni CI sonucu henüz doğrulanmadı. Gerçek tarama çalıştırılmadı; IBO ve YEDEKLER korunuyor.


## 31 Ekim 2026 — Önceki şifreli arşiv kayıtlarıyla tekilleştirme
- CI #41201354786: compile/protect/discovery-tests SUCCESS; safety kontrol anında in_progress.
- `v2/discover.py`: şifreli arşiv mevcutsa önce restore edilerek önceki URL kayıtları okunur; yeni taramada aynı URL tekrar append edilmez. Restore hata verirse tarama fail-closed kalır.
- `v2/test_archive_incremental_dedup.py` eklendi ve CI'a bağlandı. Yeni CI sonucu henüz doğrulanmadı.
- Kalan: gerçek bağımsız backup/restore kanıtı, canlı site onaylı envanteri, playback testi, gerçek ağ taraması ve önceki taramalara karşı regresyon incelemesi.
- Ana IBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — CI #41201539996 düzeltmesi
- `discovery-tests` FAILED: `test_archive_incremental_dedup.py` cryptography paketi kurulmadan çalıştırılmış; `ModuleNotFoundError: cryptography`. Paket yükleme aşaması testin önüne taşındı (commit d373bae349268bf55b27aa97769a59c5517a2f24).
- Bu hata arşiv tekilleştirme algoritmasının başarısız olduğunu göstermez; CI bağımlılık sırası hatasıdır. Yeni CI sonucu henüz doğrulanmadı.
- Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor; PR #9 merge edilmedi.


## 31 Ekim 2026 — GitHub/Gist kaynak onay kapısı
- CI #41202989680 SUCCESS.
- `v2/discover.py`: GitHub/Gist raporunda keşfedilen kaynaklar artık doğrudan gerçek taramaya alınmaz; güvenli HTTPS playlist URL'si ve tam URL SHA256'sının `v2/config/approved-github-source-sha256.json` onay listesinde bulunması gerekir. Varsayılan onay listesi boştur. GitLab/Codeberg'deki ayrı onay modeliyle eşdeğer güvenlik uygulanır.
- `v2/test_github_source_approval.py` CI'a bağlandı. Yeni CI henüz doğrulanmadı.
- Onaylanmamış yeni kaynaklar kaybolmaz: kaynak referans raporunda aday olarak kalır; ancak yayın URL'leri taranmış sayılmaz. Gerçek tarama ve bağımsız yedek/restore kanıtı hâlâ yok.
- Ana IBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Kapsam raporlarının dürüst durum etiketleri
- Önceki CI #41205709023 SUCCESS.
- `v2/source_availability_audit.py`: erişilebilen/erişilemeyen kaynak sayıları ve `COMPLETE` / `PARTIAL_SOURCE_AVAILABILITY` etiketi eklendi. Bir kaynak HTTP hatası verirken bütün kaynaklar sağlıklıymış gibi raporlanmaz.
- `v2/run_live_page_discovery.py`: onaylı canlı sayfa hatalarında `PARTIAL_APPROVED_PAGES` etiketi eklendi.
- İki ilgili offline test güncellendi. Yeni CI henüz doğrulanmadı.
- Gerçek bağımsız yedek ve restore onayı olmadan gerçek şifreli kanal taraması başlatılmadı. Ana IBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Genel rapor metadata sızıntısı önleme
- Önceki CI #41205904839 SUCCESS.
- `v2/discover.py`: public candidate JSON'a yazılan name/tvg_id/group/logo alanlarında tam HTTPS URL'leri ve token/apikey/password/secret/auth/signature/sig/key biçimli değerler maskelenir, alanlar 512 karakterle sınırlandırılır. Şifreli özel arşivde orijinal kaynak metadata'sı korunur.
- `v2/test_public_metadata_redaction.py` CI'a eklendi; yeni CI henüz doğrulanmadı.
- Eksik gerçek kaynak taraması, bağımsız backup/restore onayı, canlı sayfa kaynak onayları ve playback doğrulaması devam eden işlerdir. Ana IBO playlist, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — CI #153 / run 41206103747
- `discovery-tests` FAILED: `test_public_metadata_redaction.py` iki hata; Python raw regex içinde `\\S` ve `\\s` kullanıldığı için URL ve token maskelenmedi. `v2/discover.py` içindeki desenler `\S` ve `\s` olarak düzeltildi (commit cc504a3f79cca0235941df6324e07c9baa27d55c). Derleme ve playlist koruma testleri başarılıydı, safety önceki hatadan dolayı atlandı.
- Son commitin CI sonucu henüz doğrulanmadı. Ana IBO playlist, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Şifreli arşiv yedekleme/geri yükleme aracı
- Önceki CI #41206405986 SUCCESS.
- `v2/archive_backup_restore_drill.py`: mevcut AES-GCM arşivini ayrı dizine özel izinlerle kopyalayıp SHA256 ve kayıt bazında restore eşitliğini doğrulayan açıkça çalıştırılan yardımcı eklendi. Token taşıyan plaintext rapor yazmaz, mevcut dosyaları üzerine yazmaz, hedef symlink'leri reddeder.
- `v2/test_archive_backup_restore_drill.py` CI'a eklendi. Yeni CI henüz doğrulanmadı.
- ÖNEMLİ: ayrı dizin yedeği bağımsız/uzak dayanıklı depolama kanıtı değildir; gerçek bağımsız yedek onayı ayrıca gerekir. Gerçek tarama başlatılmadı. Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor, PR #9 merge edilmedi.


## 31 Ekim 2026 — Yerel yedek kanıtı güvenlik kapısı
- CI #41206705403 SUCCESS.
- `archive_acceptance_gate.py`: yerel ayrı dizin yedekleme aracının ürettiği `backup_scope=local_separate_directory_not_independent_storage` kanıtı, bağımsız dayanıklı yedek olarak kabul edilmez; gerçek ağ taraması için fail-closed kalır.
- `test_archive_acceptance_gate.py` regresyonu eklendi; yeni CI henüz doğrulanmadı.
- Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor; PR #9 merge edilmedi.


## 31 Ekim 2026 — Genel kaynak envanteri ve kapsam doğruluğu
- Önceki CI #41209148660 SUCCESS.
- `v2/discover.py`: offline / hiç kaynak yok / eksik / tam kaynak çekme için açık `coverage_status`, ayrıca `failed_source_count` raporlanır. Şifreli arşiv modunda eksik kaynak fail-closed kalır.
- `v2/run_public_inventory.py`: şifreli arşiv onayı gerektirmeden yalnızca mevcut 40 M3U kaynağının erişilebilirlik metadata'sını kontrol eden ayrı komut; eksik kaynak varsa nonzero exit ve rapor. Stream playback testi değildir.
- `v2/test_run_public_inventory.py` eklendi ve CI'a bağlandı. Yeni CI sonucu henüz doğrulanmadı.
- Gerçek ağ taraması ve bağımsız backup/restore onayı bekliyor. Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor; PR #9 merge edilmedi.


## 31 Ekim 2026 — HTML M3U kaynak indeksi keşfi
- Önceki CI #41209805958 SUCCESS.
- `v2/run_webpage_playlist_discovery.py`: yalnızca açıkça onaylı genel HTTPS HTML indekslerinde M3U/M3U8 referansları bulur; public rapora yalnız SHA256 ve kaynak ID yazar; token içeren tam URL yazmaz, otomatik taramaya veya İBO'ya eklemez.
- `v2/config/playlist-index-pages.json` varsayılan boş onay listesi, `v2/test_run_webpage_playlist_discovery.py` offline regresyonu ve `v2/run_all_discovery.py` entegrasyonu eklendi. Yeni CI sonucu henüz doğrulanmadı.
- Onaylı HTML kaynak listesi henüz boş; gerçek kaynak taraması, bağımsız arşiv yedeği ve playback doğrulaması tamamlanmadı. Ana IBO/YEDEKLER/YENİLER/FAVORİLER korunuyor, PR #9 merge edilmedi.


## 31 Ekim 2026 — Koordinatör testindeki altıncı aşama
- CI #41210006846 ilk kontrolde in_progress (compile/protect success, discovery-tests queued).
- HTML M3U indeks keşfi altıncı aşama olarak `run_all_discovery.py` içine eklendiğinden `test_run_all_discovery.py` içindeki eski 5-aşama beklentisi 6'ya, arşiv keşif aşaması indeksi 5'e düzeltildi (commit 47043c2785cae3131a8e4cd69e1b40b598d3d761).
- Son CI henüz doğrulanmadı. Ana IBO, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Kaynak erişilebilirlik durumunun doğruluğu
- 6 aşamalı koordinatör düzeltme commit'i 47043c2785cae3131a8e4cd69e1b40b598d3d761 için Actions #41210098077 SUCCESS.
- `source_availability_audit.py`: hiç kaynak tanımlı değilse `NO_CONFIGURED_SOURCES`, hiçbir kaynak erişilebilir değilse `NO_SOURCES_REACHABLE`, karışık sonuçta `PARTIAL_SOURCE_AVAILABILITY`, tüm kaynaklar başarılıysa `COMPLETE`.
- `run_public_inventory.py` boş kaynak listesiyle yanlışlıkla başarılı tamamlanamaz. İlgili offline regresyon testleri güncellendi.
- Son commit CI henüz doğrulanmadı. Bu kontroller stream playback değildir; gerçek tam tarama ve bağımsız şifreli yedek kanıtı hâlâ gerekli. Korunan listelere dokunulmadı, PR #9 merge edilmedi.


## 31 Ekim 2026 — Yerel backup dayanıklılık düzeltmesi
- Önceki Actions #41211016352 SUCCESS.
- `v2/archive_backup_restore_drill.py` yerel farklı dizindeki kopya için `durable=false` raporlar; bağımsız kalıcı yedek iddiası kaldırıldı. `v2/test_archive_backup_restore_drill.py` bu durumu doğrular. Kabul kapısı ayrıca `backup_scope` yerel ise reddeder.
- Gerçek tarama için bağımsız yedek ve restore kanıtı hâlâ gereklidir. Son CI sonucu bekliyor. Korunan IBO/YEDEKLER/YENİLER/FAVORİLER değiştirilmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Gist M3U keşif regex düzeltmesi
- Önceki Actions #41211136199 SUCCESS.
- `v2/github_source_discovery.py` Gist dosya adı eşleşmesindeki çift ters eğik çizgi (`\\\\.`) düzeltildi; `.m3u`, `.m3u8`, `.txt` uzantıları artık doğru eşleşebilir. Bu hata Gist keşfini sessizce kaçırıyordu.
- `v2/test_gist_filename_discovery.py` ve CI adımı eklendi. Yeni CI henüz doğrulanmadı.
- Ana IBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi. Gerçek kaynak taraması ve bağımsız şifreli yedek doğrulaması bekliyor. PR #9 merge edilmedi.


## 31 Ekim 2026 — GitHub kaynak keşfi API hata toleransı ve testleri toplama
- Kullanıcı GitHub M3U Source Discovery #11 başarısız ekranını bildirdi; tam job loguna erişilmediğinden spesifik HTTP hatası kesinleştirilmedi.
- `v2-github-source-discovery.yml`: her push ile maliyetli GitHub API keşif taraması başlatan tetik kaldırıldı; schedule/manual kaldı. Toplu CI `v2-ordered-preflight.yml` çalışır.
- `github_source_discovery.py`: API/kaynak erişim hatalarında başarılı bulgular korunur, `coverage_status=PARTIAL_API_ERRORS`, `errors`, `playback_verified=false` raporlanır; kısmi tarama asla tam kapsama diye sunulmaz.
- `test_github_partial_discovery.py` eklendi ve toplu CI'ya bağlandı. Bu davranış veri taraması için kısmi rapor, güvenlik onayları için fail-closed politikasını değiştirmez.
- Ana IBO/YEDEKLER/YENİLER/FAVORİLER korunuyor; PR #9 merge edilmedi. Son CI henüz doğrulanmadı.


## 31 Ekim 2026 — Toplu kısmi kaynak dayanıklılığı
- Önceki toplu CI #41212171051 SUCCESS.
- GitLab/Codeberg API hataları başarılı kaynak referanslarını artık düşürmez; `coverage_status=PARTIAL_API_ERRORS` raporlanır.
- Kaynak erişim denetimi hata verdiğinde koordinatör sonraki bağımsız aşamaları çalıştırır; şifreli arşiv güvenlik preflight kontrolü zorunludur.
- En az bir kaynak başarıyla yüklendiğinde şifreli arşiv, başarısız diğer kaynaklar yüzünden tüm başarılı adayları kaybetmez; `archive_source_set_partial=true` ile eksik kapsamı açıkça bildirir. Hiç kaynak erişilebilir değilse arşivleme reddedilir.
- Toplu CI testleri: `test_run_all_discovery.py` ve yeni `test_partial_source_coverage.py`; yeni CI sonucu henüz doğrulanmadı.
- Ana İBO, YEDEKLER, YENİLER, FAVORİLER korunuyor; PR #9 merge edilmedi. Bağımsız yedek onayı ve gerçek tarama henüz tamamlanmadı.


## 31 Ekim 2026 — CI #203 hata düzeltmesi ve toplu testlerin birleştirilmesi
- CI #41212322181 başarısızlık logu: `test_partial_scan_fail_closed.py::test_forge_main_fails_on_partial_result` eski `SystemExit` beklentisi nedeniyle FAIL; GitLab/Codeberg artık kısmi taramayı raporlayıp korur.
- Eski test yeni kısmi rapor davranışına uyarlandı; API hata bilgisi raporda açıkça kalır, tam kapsama iddiası yoktur.
- `v2-ordered-preflight.yml` PR bazlı concurrency ve `cancel-in-progress: true` ile eskimiş eşzamanlı testleri iptal ederek tek güncel toplu çalışmayı tercih eder.
- Son CI henüz doğrulanmadı; ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor, PR #9 merge edilmedi.


## 31 Ekim 2026 — Resmî yayın sayfaları ve HTML kaynak indeksleri kısmi tarama dayanıklılığı
- CI #41212487179: compile/protect/discovery-tests/safety SUCCESS.
- `run_live_page_discovery.py` ve `run_webpage_playlist_discovery.py` kısmi sayfa erişim hatasında başarılı referansları saklar ve `PARTIAL_APPROVED_PAGES` raporlar; otomatik oynatılabilir kanal ithalatı yoktur.
- İki modülün testlerine başarı+başarısız sayfa kombinasyonu eklendi. Kaynak URL'leri, gizli tokenlar veya canlı IBO listesi rapora taşınmaz.
- `live-pages.json` ve `playlist-index-pages.json` henüz boş: doğrulanmış resmî HTTPS sayfaları eklenmeden bu kategoriler taranmış sayılamaz.
- Son CI henüz doğrulanmadı; ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor; PR #9 merge edilmedi.


## 31 Ekim 2026 — İlk doğrulanmış resmî canlı sayfa kaynakları
- Toplu CI #41212797762 SUCCESS.
- `v2/config/live-pages.json` boş olmaktan çıkarıldı: AzTV `https://www.aztv.az/` (kurumun resmî FAQ'sı canlı yayınları doğruluyor) ve TRT1 `https://www.trt1.com.tr/` (resmî yayın akışında canlı izle bulunuyor). Bunlar HTML referans keşfi içindir, M3U veya doğrulanmış oynatılabilir yayın değildir.
- `test_run_live_page_discovery.py` kaynak envanteri benzersiz ID ve güvenli HTTPS kontrolünü toplu CI içinde yapar.
- HTML playlist-index sayfa envanteri hâlâ boş; doğrulanmamış URL eklenmedi. Gerçek ağ taraması ve şifreli bağımsız arşiv kabulü bekliyor. Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor; PR #9 merge edilmedi.
