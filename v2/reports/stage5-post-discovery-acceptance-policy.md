# Aşama 5 — #31, #32, #33: keşif sonrası kabul politikası

Karar tarihi: 2026-11-12. Kapsam: MADSC55 TV V2; eski Madsc-Tv deposu değildir.

## Sıralama ve kapsam

1. Önce 34 görevlik sistemin kanal keşif **altyapısı** hazırlanır ve çevrimdışı test edilir.
2. #34 kapsamındaki Türkiye/Azerbaycan/dünya çapında toplu keşif gerçekleştirilir. Kaynaklar GitHub, Gist, GitLab, Codeberg, resmî yayın siteleri, YouTube canlı yayınları ve M3U/M3U8 bağlantılarıdır.
3. Ancak yeni toplu keşif sonuçları için gerçek video **ve** ses çözümleme kanıtı toplanır. HTTP 200, EPG, isim benzerliği, ffprobe mock'u veya önceki kanallar yeni kanıt sayılmaz.
4. #31 son toplu kabul: gerçek keşif → AV kanıtı → şifreli arşiv → bağımsız geri yükleme → değişmez playlist kontrolleri; bağımlılıkların tamamı doğrulanmış olmalıdır.
5. #32 gerçek İBO Player cihazında kullanıcı tarafından oynatma/görüntü/ses testi ve kanıtı; otomasyon kullanıcı onayını taklit edemez.
6. #33 son şifreli arşiv bütünlüğü, gerçek geri yükleme, kabul koşuları, cihaz kanıtı ve dışarıda bırakılan kayıtlarla teslim raporu.

## Şimdi yapılabilecek işler

- #31 için toplu kabul testlerinin kodunu ve Actions entegrasyonunu hazırla; **yalnızca sentetik/çevrimdışı fikstürlerle** regresyon testleri yap.
- #32 için kullanıcı cihaz testi kanıt alanlarını ve kabul şablonunu hazırla; gerçek cihaz sonucu üretme.
- #33 için rapor şablonu, şifreli arşiv bütünlüğü ve geri yükleme kontrolünü hazırla; gerçek teslimi tamamlandı gösterme.

## Yasaklar ve koruma

- Eski kayıp kanal taramasını veya sistemdeki eski kanalların yeniden AV kabulünü bu aşamanın işi olarak başlatma.
- Eski kanalları kullanarak ibo_1000.m3u veya ibo_2000.m3u paketlerini doldurma; yeterli yeni ve kanıtlı kayıt yoksa eksik bırak.
- Ana İBO playlistini, YEDEKLER/YENİLER/FAVORİLER'i veya korumalı favorileri değiştirme.
- #31, #32, #33'ü gerçek kabul kanıtı olmadan kapatma. **Altyapı hazır** ile **nihai kabul tamamlandı** ayrı durumlardır.

Bu politika kullanıcı tarafından özellikle istenen kanal araması sonrası toplu kabul sırasını kaydeder.
