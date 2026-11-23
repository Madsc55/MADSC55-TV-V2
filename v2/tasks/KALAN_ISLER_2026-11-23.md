# MADSC55 TV V2 — 23 Kasım 2026 güncel kalan işler ve proje sahibi kararları

Bu kayıt, 23 Kasım görüşmesindeki son talimatları önceki planların üzerine işler. Yalnız takip belgesidir; ana playlist, kanal kimlikleri, workflow ve güvenlik kilitleri değiştirilmez.

## Kesin kararlar
- Tek kanonik playlist: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`. Yeni playlist/test playlisti açılmayacak.
- Proje sahibi ANA ARŞİV'in alfabetik sıralamasının tamamlandığını teyit etti. Tekrar sıralama işi açılmayacak. Bu teyit ayrıca main üzerinde teknik doğrulama yerine geçmez.
- Proje sahibi ANA ARŞİV'i YEDEKLER'in hemen altına taşıma isteğinden vazgeçti. #660/#661/#662/#663 kapsamındaki yer değiştirme işlemleri **iptal**; mevcut kategori sırası korunacak, otomatik uygulanmayacak.
- 48 daha önce çıkarılmış kanal geri eklenmeyecek. Kategoriler, diğer arşivler ve kanal meta verileri izinsiz değiştirilmez.
- Gerçek yayın/İBO testleri son aşamada; 685 tarihsel belirsiz kanal için SECURITY HOLD izinsiz kaldırılmaz.
- Daha önce tamamlanmış kod/CI işleri yeniden yapılmaz; idari tamamlanma gerçek teknik kabul sayılmaz.

## Güncel takip listesi (12 başlık)
1. Main kanonik playlist gerçek envanteri: toplam, YEDEKLER, ANA ARŞİV, diğer kategoriler ve sayaç etiketlerini uzlaştır. Son işlem kayıtlarındaki 18.337 toplam / 1.107 YEDEKLER / 15.703 ANA ARŞİV değerlerini main üzerinde doğrula; #657/#658 uygulama ve CI durumunu teyit et.
2. Otomatik kanal keşfi: onaylı kaynaklar, güvenli aday alma, tekrarların ayıklanması ve uçtan uca çalışmanın kanıtı.
3. HTTP sağlık taraması: uzun taramanın hatasız tamamlanması; 404/503/timeout için ayrı karar ve kanıt, tek başına ağ hatasını ölü kanal saymama.
4. GitLab/Codeberg 429: sağlayıcı başına güvenli hız sınırı/backoff; erişim engeli kalan kaynakların açık raporu.
5. Kimlik/URL uzlaştırması: tarihsel 20.148 kuyruk, 3.766 eşleşme, 16.367 playlist dışı ve aradaki 15 kimlik farkını satır bazında açıklama; mükerrer URL önleme.
6. EPG: 303 tarihsel eksik eşleşme ve kalan program/ID eşleştirmelerinin yeniden kanıtlanması.
7. Logolar: güncel eksik sayısını yeniden say; yalnız resmî/doğrulanmış gerçek logolar, tahmini/rastgele logo yok.
8. Türkçe/yabancı ayrımı: ses, dil, altyazı, Türkiye/KKTC ve diğer Türkî yayın ölçütleri; isim/ülke tek başına kesin kanıt değil.
9. Otomatik karar zinciri: tarama → kanıt → karar → uygun TURK/YABANCI arşivine güvenli taşıma; taşınanların YEDEKLER'den düşmesi, ana liste bütünlüğü, yetkili PR ve CI kontrolü.
10. Şifreli özel kasa: mevcut yetkili harici depoda gerçek backup/revizyon, bağımsız checksum, anahtar erişimi ve izole restore kabulü; eski Stage 4 restore kanıtını bu kasanın kabulü sayma.
11. Güvenli canlı AV/FFmpeg: HLS alt istekleri için OS düzeyi egress izolasyonu kabul edilmeden 685 canlı retry açma; iki denemeli kanıt, görüntü+ses doğrulaması ve hatalı kesin karar önleme.
12. Gerçek İBO Player cihaz testi ve nihai sistem kabulü: kanonik liste, kanal oynatma, kategori, paket/arşiv ve CI güvenlik sonuçlarını uçtan uca doğrula.

## İş sırası
Aşama 1: envanter, kimlikler, HTTP, kaynaklar, EPG, logolar.
Aşama 2: keşif/sınıflandırma/karar/arşiv otomasyonu.
Aşama 3: şifreli yedek, güvenlik ve üretim kabulü.
Aşama 4: güvenli canlı AV, gerçek İBO Player ve nihai kabul.

## Tamamlanma yüzdesi
#655 içindeki %75 tamamlandı / %25 kaldı yalnızca tarihsel planlama tahminidir. Son değişikliklerden sonra yeni ölçülmüş yüzde yok. 34 ana görevin idari kapanışı %100 teknik başarı değildir. Nihai yüzde, her bir açık kabul maddesinin güncel main/Actions/gerçek cihaz kanıtıyla hesaplanacak.

## Sonraki çalışma kuralı
İşleri tek tek kanıtla; başarılı olanları kapat, eksik kalanları açık tut. Playlist'e yazan değişiklikler güvenlik kapısından geçmeden birleştirilmez. Bu dosya yalnızca güncel planı ve kullanıcının iptal kararlarını kalıcı kayda geçirmek için hazırlanmıştır.
