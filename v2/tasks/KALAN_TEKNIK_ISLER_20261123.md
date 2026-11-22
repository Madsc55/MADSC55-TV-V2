# MADSC55 TV V2 — Kalan teknik işler ve kabul planı (23 Kasım 2026)

Bu belge kullanıcının önceki 15 ekran görüntüsündeki talepleri ve devam konuşmasındaki ek işleri tekrar kaybetmemek için tutulur. **34 görevin state.json içinde completed olması teknik kabulün tamamlandığı anlamına gelmez.** Bu dosya ayrı bir teknik açık işler kaydıdır; görev statülerini değiştirmez.

## Değişmez kurallar
- Tek kanonik liste: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`. Yeni playlist veya YEDEKLER_TEST oluşturma.
- Ana kategoriler, kanal kimlikleri ve sıra korunur; değişiklikler kanıta ve açık yetkiye dayanır.
- 685 RECHECK_REQUIRED kanalın güvenlik kilidini kaldırma, belirsiz sonuçla silme.
- Daha önce çıkarılan 48 engelli kanalı geri getirme; eski ilk-1003 koruma kuralını yeniden uygulama.
- Eski taşımaları tekrar çalıştırma; aynı URL/SHA kimliğini ikinci kez ekleme.
- Gerçek yayın taraması ve İBO Player cihaz kabulü kullanıcı isteğiyle **son test aşaması**; HTTP salt-okunur raporu bunun yerine geçmez.

## Öncelikli işler — gerçek kabul gerektirir
1. **HTTP taraması:** PR #637 birleştirilmiş olduğu kullanıcı tarafından bildirildi. `Main Playlist HTTP Health Report (Read Only) #2` ekran görüntüsünde main / `53e0a03`, 33m34s `In progress`. Tamamlama, artifact, başarısızlık, HTTP 404/503/timeout/unknown ayrımı ve sonuçların kilitli kayıtları koruyan güvenli değerlendirmesi doğrulanacak. **Bu ekran görüntüsü PASS değildir.** Rapor tamamlanmadan otomatik silme yapılmaz.
2. **Actions ve otomasyon:** Offline CI / Production Security Gate güncel main koşuları, önceki hata→düzeltme→başarı zinciri, Master Engine, süre sınırı, retry/backoff, izleme ve hata raporları uçtan uca denetlenecek (#23,#25,#26,#24). Geçmiş 101 PASS ve Security SUCCESS güncel canlı yayın kanıtı değildir.
3. **Kaynak keşfi ve envanter (#3–#14,#34):** GitHub, Gist, GitLab, Codeberg, YouTube canlı TV, resmî yayıncı sayfaları, M3U/M3U8, Türkiye/Azerbaycan/dünya kaynakları; rate-limit, erişim engelleri, kaynak kimliği, hash/URL çapraz eşleştirmesi ve eski kayıtların güvenilirliği. 35.327 aday/13.884 tarihsel AV kanıtı yeni ve benzersiz kanal sayısı değildir. Doğrulanmamış kaynak eklenmez.
4. **Kimlik, kurtarma ve kalite (#15–#21):** Eksik 6 yayıncı/kimlik kaydı; tarihsel kaynak kimliklerinin doğrulanması; kurtarma ve güvenli yeniden deneme kuyruğu; 303 tarihsel EPG açığı ve güncel XMLTV eşleşmeleri; gerçek çözünürlük, görüntü/ses, yayın devamlılığı, kanıt zaman damgası. Tarihsel rakamlar güncel yeniden sayılacak.
5. **Türk/Yabancı sınıflandırması:** Türkçe kanal adı ve TR/TURK/TÜRK/Türkiye/Kıbrıs ipuçları tek başına yeterli değil. Türkiye, KKTC, Azerbaycan ve diğer Türkî kaynaklar; Türkçe adı olmayan yayınlar; ASR konuşma dili, OCR ekran yazısı, WebVTT/altyazı, ses+görüntü ve yayıncı kimliği ile kanıt dereceli karar. 20.000 kayda kadar toplu inceleme kodu ile gerçek kabulü ayır. Kesinleşmeyen kayıtları otomatik taşımama.
6. **Arşiv otomasyonu:** 18.074 özgün arşiv kimliğinin tek listede korunması; tarihsel dağılım YEDEKLER 1.792, ANA ARŞİV 15.574, TÜRK 424, YABANCI 284, diğer 838. 2.500'lük YEDEKLER paket döngüsü, taşımanın kaynak gruptan düşmesi, sıradaki paketin ANA ARŞİV'den gelmesi, mükerrer önleme, idempotent işlem ve geri alma/restore kabulü. İBO Player kullanıcı testi sistem işleyişinden ayrı.
7. **685 belirsiz kanal ve medya güvenliği:** 1.107 WORKING / 685 RECHECK_REQUIRED tarihsel raporunu güncel kanıtla karıştırma. Salt-okunur retry planı, DNS/IP pinleme, FFmpeg yerel dosya izolasyonu, HLS/DASH segment/anahtar kaynak güvenliği ve gerçek yayıncı örneği kabulü; kilit açma ancak tüm güvenlik şartları sağlandığında.
8. **Logolar ve EPG:** Yalnız gerçek ve doğrulanmış yayıncı logoları; doğrulanmamış 6 logo eşleşmesi ve geçmişte bildirilen eksik logo sayıları yeniden kontrol edilecek. EPG için kesin XMLTV kanal/program eşleştirmeleri ve 303 tarihsel açığın güncel sonucu belgelenecek.
9. **Yedekleme ve restore:** Stage 4 tarihsel Google Drive bağımsız restore PASS ile ayrı Türk özel Fernet kasasının eksik harici restore kabulünü birbirine karıştırma. Ana liste, kategori, URL hash, arşiv ve bağımsız yedekten geri dönüş zinciri izole ortamda kanıtlanacak.
10. **İBO paketleri (#28–#30):** Tarihsel 1.000 / 2.000 / 4.301 paket çalışmalarını gerçek ses+görüntü kanıtı, kaynak kimliği ve M3U bütünlüğü ile karşılaştır; sentetik veya yalnız HTTP erişimi olan kayıtları gerçek oynatılabilir kanal diye sayma. Kullanıcının güncel tek playlist kuralını ihlal edecek ayrı üretim listesi yayımlama.
11. **Son kabul (#31–#33,#8,#10):** Güvenlik kapıları ve arşiv kabulü sonrası gerçek canlı AV taraması (tüm ilgili kategoriler, ANA/TÜRK/YABANCI arşivleri dahil), Türk/Yabancı son karar, İBO Player gerçek cihaz testi ve son teslim raporu.

## Çalışma sırası
A. Devam eden HTTP Health Report #2 sonuçlarını doğrula, varsa çökme/hata düzelt; güvenli salt-okunur raporu al.
B. HTTP taramasından bağımsız altyapı: Actions, güvenlik, keşif, kimlik, EPG/logo, arşiv/restore ve paket hazırlığını kanıtla.
C. En son yetkilendirilmiş canlı AV / dil / tüm kategoriler taraması, 685 retry ve İBO Player kabulü.
D. Her maddeyi **kanıt bağlantısı + tarih + run/commit + kabul sonucu** olmadan DONE işaretleme. GitHub PR merge / issue kapatma ile teknik kabulü ayır.

## Durum
Bu kayıt bir **iş planı**, tamamlama beyanı değildir. HTTP Health Report #2'nin son durumu henüz burada doğrulanmadı. Playlist ve `v2/tasks/state.json` bu not nedeniyle değiştirilmez.
