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
