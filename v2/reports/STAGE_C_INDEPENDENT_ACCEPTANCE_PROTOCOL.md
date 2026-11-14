# Aşama C — Bağımsız üretim kabul protokolü (#31, #32, #33)

Bu protokol **testin yapıldığına dair kanıt değildir**. Ana İBO, YEDEKLER, YENİLER ve FAVORİLER üzerinde yazma işlemi yapılmaz. Gerçek cihaz ve bağımsız geri yükleme kanıtları üretilene kadar görevler `in_progress` kalır.

## #31 — Android cihazda gerçek görüntü + ses
- Gerçek Android cihazın ve İBO Player sürümünün kimliğini (kişisel veri içermeden), test zamanını, kullanılan M3U parçasının SHA-256 değerini kaydet.
- İBO Player'a gerçek `IBO_AV_VERIFIED_*_PART*.m3u8` paketini yükle; seçilen her kanal için **görüntü ve sesin aynı oynatma oturumunda** bulunduğunu doğrula. Yalnız HTTP 200, ffprobe, emülatör veya sentetik medya cihaz kabulü sayılmaz.
- Kanal kimliği, başlangıç/bitiş zamanı, oynatma sonucu, video ve ses kanıtı dosyalarının yolları, SHA-256 değerleri ve hata günlüğünü üret. Başarısız kanalları başarılı olarak etiketleme.
- Önerilen kanıt: `v2/evidence/stage-c/device-playback.json` + gerçek cihaz ekran/ses kayıtları (hassas bilgiler temizlenmiş).

## #32 — Bağımsız şifreli arşiv geri yüklemesi
- Üretimden **ayrı** izole hedef ortam kullan; ana kayıtlar ve mevcut arşivler üzerine yazma.
- Arşivin kaynak kimliği, sürümü, indirilen baytların SHA-256 değeri, şifreli arşiv bütünlük testi ve çözme sonucunu kaydet. Gizli anahtarları veya parolaları rapora yazma.
- Geri yüklenen kayıt sayısını, kimlikleri ve mümkünse kayıt hash'lerini kaynak manifest ile karşılaştır; kayıp, mükerrer ve bozuk kayıt sayılarını ayrı göster.
- Çalıştırma ortamı kimliği, başlangıç/bitiş zamanı, komut çıkış kodları, günlük ve sonuç dosyalarının SHA-256 değerlerini kaydet.
- Önerilen kanıt: `v2/evidence/stage-c/independent-restore.json` + bağımsız geri yükleme logları.

## #33 — Son kabul kapısı
- #31 ve #32 kanıt dosyaları gerçekten mevcut, okunabilir ve SHA-256 eşleşmeleri doğrulanmış olmalı.
- Her iki testte `passed=true` ve gerçek ortam/cihaz doğrulaması bulunmalı; `skipped`, `mock`, `unknown` veya eksik alan **başarısız** sayılmalı.
- 1.000/2.000'lik M3U paketleri, `#EXTM3U` başlığı, `#EXTINF`+URL çiftleri, URL tekrarları, manifest sayıları ve SHA-256 değerleri açısından yeniden karşılaştırılmalı.
- Son raporda kabul edilen/edilmeyen yayınlar, hata listesi, kullanılan artifact/Actions bağlantıları, kanıt hash'leri ve bağımsız onay zamanı yer almalı.
- Yalnız bütün zorunlu kanıtlar başarıyla doğrulanırsa `state.json` içindeki #31, #32, #33 görevleri `done` yapılabilir; aksi hâlde açık bırakılır.

## Mevcut kanıtın sınırı
13 Kasım 2026 Actions `43412576224` artifact `14033805492`: raporda 4.301 AV doğrulanmış URL, 1.000/2.000 M3U bütünlüğü, `playback_verified_on_device=false` ve yalnız Actions içi `archive_restore_test_passed=true` kayıtlı. Bu artifact tek başına #31 veya #32'nin bağımsız kabulü değildir.
