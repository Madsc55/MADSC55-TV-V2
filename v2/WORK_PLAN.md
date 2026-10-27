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
