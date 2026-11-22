# MADSC55 TV V2 — Birleşik yapılacak işler

23 Kasım 2026 — Proje sahibinin onayladığı 12 aşamalı çalışma planı. **Yalnız plan kaydıdır; tamamlanmış test veya canlı yayın kabulü değildir.** 34 eski görevin idari kapanışı korunur; kanıt eksikleri ayrıca izlenir.

## 12 aşama (tamamlanma kanıtı bekliyor)
1. [ ] PR #641/#642/#650 ve tüm güncel PR/CI/güvenlik kapısı durumunu doğrula
2. [ ] Ana playlist sayıları, 654 silme, 685 korunan kimlik ve kategori envanterini uzlaştır
3. [ ] YEDEKLER, ANA ARŞİV, TÜRK, YABANCI ve diğer bütün kategorileri tarama kapsamına al
4. [ ] Onaylı kaynaklardan yeni kanal keşfi, provenans, URL/kimlik deduplikasyonu
5. [ ] HTTP 404/403/429/503/timeout sınıflandırması, kesintisiz raporlama
6. [ ] Gerçek video/ses/HLS testi; HTTP 200 AV kanıtı değildir; İBO kabulü ayrı
7. [ ] Kontrollü tekrar deneme; 685 SECURITY HOLD ve FFmpeg/HLS OS ağ izolasyonu korunacak
8. [ ] Kesin ölüleri kanıtla temizle, doğrulanmış adayları ekle; rollback ve CI
9. [ ] 2.500'lük YEDEKLER döngüsü, ANA ARŞİV/TÜRK/YABANCI taşıma ve paketler
10. [ ] Türkçe ses/altyazı, tarihsel 303 EPG ve 4.745 logo açığını güncel kanıtla yeniden say
11. [ ] Harici şifreli bağımsız restore, otomatik bakım, geçmiş raporları ve kaldığı yerden devam
12. [ ] Tüm kategoriler, güvenlik, gerçek AV, İBO cihaz ve envanter nihai kabulü

## Birlikte ele alınacak ek eksikler
- 685 kanal güvenlik kilidi, #497 HLS/FFmpeg alt bağlantı ağ izolasyonu; güvenli kabul olmadan canlı retry yok.
- 654 silme sonrası envanter; 404/503 yeniden değerlendirme; Codeberg/GitLab 429; tarihsel YouTube SIGN_IN_REQUIRED.
- 20.148 tarihsel kuyruk / 3.766 eşleşme / 16.367 dışarıda / 15 fark uzlaştırması; güncel sayımla doğrula.
- Tarihsel 303 EPG, 4.745 logo ve gerçek yayıncı/dil/altyazı kanıtı eksikleri.
- Yetkili Fernet kasası için harici gerçek şifreli yedek ve bağımsız restore; anahtarları kaydetme.
- Kanal bazında son tarama zamanı, HTTP/AV sonucu, hata nedeni, deneme geçmişi, kaynak/provenans; kesintiden devam.

## Değişmez kurallar
- Tek ana playlist: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`; yeni playlist açma.
- Kategorileri ve sıralamayı koru; doğrulanmamış kanal ekleme, belirsiz kanal silme; 48 tarihsel dışlanan kanalı geri getirme.
- 685 SECURITY HOLD güvenli kabul olmadan kaldırılmayacak.
- Önceden tamamlanan işler tekrarlanmayacak; PR #650 planıyla kapsam birleştirilecek.
- Her aşama ancak CI/Production Security Gate, gerçek envanter ve gerektiğinde AV/cihaz/restore kanıtıyla tamamlandı işaretlenecek.
