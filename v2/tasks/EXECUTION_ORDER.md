# V2 yürütme sırası — kullanıcı kararı (9 Kasım 2026)

Bu belge mevcut 33 görevin durumunu değiştirmez. Kanıtlanmamış hiçbir görev tamamlandı olarak işaretlenmez.

## 1. Kanal keşif altyapısı
- Mevcut `v2/discover.py`, resmî yayıncı, GitHub/Gist, GitLab, Codeberg, Scribd, SlideShare, Internet Archive, IPTV-org, TR/AZ ve YouTube referans entegrasyonlarının kurulumunu ve kaynak kapsamını doğrula.
- Önce çevrimdışı, salt-okunur ve küçük örnekli smoke kontrolüyle arama yolunun çalıştığını doğrula; gerçek AV doğrulaması olmadan kanal kabul etme.
- Eksik entegrasyonları tamamla. Kaynak ve kimlik geçmişini koru.

## 2. Diğer sistem eksiklerini tamamla
- Bağımsız kod, arşiv, güvenlik, kimlik, EPG, kategori, dışa aktarma ve iş akışı görevlerini bağımlılık sırasıyla tamamla.
- Dış erişim/kimlik bilgisi gerektiren engelleri açık bırak; bağımsız göreve geç.
- Her değişikliği güncel HEAD ve görev sahipliği denetimiyle yalnız `madsc/v2-discovery-bulk-20261031` dalına gönder; çakışan Codex/saatlik yürütücüyü ezme.

## 3. En son kapsamlı genel kanal araması
- Sistem işleri tamamlanmadan genel, maliyetli, uzun canlı taramayı **başlatma**.
- Dünya geneli ve TR/AZ m3u/m3u8, resmî canlı yayın ve YouTube referanslarını kapsa; yalnız yetkili, güvenli kaynakları tara.
- FFmpeg ile gerçek görüntü+ses kanıtı olmayan adayları çalışıyor diye işaretleme.

## 4. Genel taramadan sonra son kabul testleri
- Toplu regresyonlar, zorunlu GitHub Actions işlerinin aynı SHA üzerinde sonuçlanması, şifreli AV arşivi ve güvenli dışa aktarma doğrulansın.
- IBO Player cihaz testi (#32) yalnız kullanıcının gerçek cihaz kanıtıyla tamamlanabilir.
- Sonuçları `v2/tasks/state.json`, kanıt URL'lerini `DEVAM_NOTU.md` ile mutabık tut; yalnız kabulü kanıtlanan görevleri kapat.

## Korunan kapsam
`main`, PR #9, ana IBO listesi, kategoriler, tarihî 4.955 kimlik ve YEDEKLER/YENİLER/FAVORİLER değişmez. #3, #4, #6 ertelenmiş; #34 en son. Bu belge yürütme talimatıdır, başarı kanıtı değildir.
