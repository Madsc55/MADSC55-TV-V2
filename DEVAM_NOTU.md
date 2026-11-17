## 17 Kasım 2026 — SOHBET DEVİR / KALDIĞIMIZ YER (YENİ SOHBETTE İLK OKUNACAK KAYIT)

### Proje ve kesin kullanıcı talimatı
- Yalnızca **MADSC55 TV V2**. Kullanıcı bu sohbeti sadece V2 soru/işleri için kullanıyor.
- Ana İBO playlistine, mevcut canlı listeye ve YEDEKLER kategorisine **dokunma**. 18.074 YEDEKLER kanalını henüz tarama, taşıma, sıralama veya silme.
- Kullanıcının istediği yeni sistem: YEDEKLER'deki kanalları daha sonra toplu analiz etmek; ses/görüntü çalışıyor mu, Türkçe konuşma var mı, ekranda Türkçe yazı/OCR var mı, Türkçe altyazı var mı tespit etmek; sonuçları Türkçe çalışan / yabancı çalışan / çalışmayan / belirsiz gibi inceleme depolarında sınıflamak. Ana arşiv tüm kanalları tutmaya devam edecek. Otomatik tahminler kanalı kendiliğinden onaylamamalı.
- **Sıkı iş sırası:** (1) güvenli DNS/redirect/egress tasarımı ve doğrulaması; (2) otomatik testleri gerçek ortamda çalıştırıp tüm hataları düzeltmek ve PASS kanıtını saklamak; (3) gerçek yayınlarda AV decode + ASR Türkçe konuşma + OCR + altyazı örneklemesi ve tek raporda uçtan uca kabul; ancak bunlardan sonra 18.074 YEDEKLER taraması. İlk 1003 ana kanal korunacak. Başarısız veya çalıştırılmamış testleri tamamlandı sayma.

### GitHub çalışma konumu
- Repo: `Madsc55/MADSC55-TV-V2`
- Geliştirme dalı: `plan/18074-kanal-akilli-test-arsiv-20261117`
- PR: #365 — https://github.com/Madsc55/MADSC55-TV-V2/pull/365
- Ana çalışma notu: bu dosya, `DEVAM_NOTU.md`.
- Bu geliştirmeler özellik dalında tutuldu; PR merge edildiği doğrulanmadı. Yeni sohbette önce PR head, branch ve Actions durumunu yeniden kontrol et.

### Bu sohbette kaydedilen teknik ilerlemeler
- `v2/backup_speech_evidence.py`: ASR dil tahminlerini yalnızca hash temelli inceleme ipucu olarak içeri alır; otomatik Türkçe onayı vermez.
- `v2/backup_text_hint_import.py`: OCR ve altyazı ipuçlarını güvenli şekilde içeri alır; ham metni saklamaz, otomatik onay vermez.
- `v2/backup_archive_offline.py`: AV, ASR, OCR ve altyazı ipuçlarını tek offline raporda birleştirmek için `--speech` ve `--text-hints` seçenekleri eklendi. Mevcut raporların üzerine yazma engellendi.
- `v2/spoken_language_sample_review.py`: faster-whisper tabanlı ASR örnekleyicisi; snapshot ve playback hash kimlikleri birebir eşleşmeli, tekrarlı kimlikler reddedilir; bu doğrulama ağır model yüklenmeden önce yapılır; ortak URL doğrulaması kullanır; rapor üzerine yazılmaz.
- `v2/backup_text_sampler.py` ve `v2/backup_text_batch.py`: OCR/altyazı örneklemesi; URL kontrolleri, örnek sınırları, rapor güvenliği; FFmpeg protokol whitelist eklendi.
- ASR/OCR ipuçları en çok 16 örneklik batch olarak içeri alınır. Bu yalnızca tek örnekleme paketi sınırıdır; 18.074 envanter hedefini azaltmaz.
- ASR ve OCR örnekleyicileri `MADSC55_SECURE_EGRESS_CONFIRMED=1` olmadan ffmpeg çağırmayı reddedecek şekilde fail-closed düzenlendi. Bu değişken tek başına ağ izolasyonu sağlamaz; yalnızca gerçek, doğrulanmış egress/proxy kurulduktan sonra ayarlanmalı.
- FFmpeg protokol whitelist: `file,http,https,tcp,tls,crypto`. Bu DNS rebinding ve HTTP redirect SSRF riskini tek başına çözmez; bazı HLS kaynaklarında protokol uyumluluğu testi gerekir.
- Ortak URL doğrulaması yerel/özel IP, localhost, kimlik bilgisi, kontrol karakteri, fragment, hatalı port, tek etiketli iç host ve bozuk DNS label reddi içerir; IPv6 literal desteği korunmuştur. DNS rebinding ve yönlendirme riskleri hâlâ ağ seviyesinde egress kısıtı gerektirir.
- Son kaydedilen güvenlik/URL düzeltme commitleri: `f65629e592c0cdb78e5e3044a77bf8da174859fd`, test `f33a57e83ef8aa6fbca9cc1271dcdb77e278dd03`, IPv6 uyum düzeltmesi `8e86f590c27ccc6c26c4a73a330f3bf4b19de12b`; son not commit'i `1707dd607d631675ed279079f164ec459f25c24f`. Daha yeni değişiklikler olabilir; yeni sohbette branch HEAD'i doğrula.

### Test ve CI durumu — önemli ayrım
- En son kayıtta **71 yazılı otomatik test senaryosu** olduğu belirtiliyor. Bu sayı yalnızca yazılmış testleri ifade eder; testlerin çalıştırıldığı veya geçtiği anlamına gelmez. Yeni sohbette test listesi ve test runner'dan gerçek sayıyı doğrula.
- Yerel çalışma ortamında `github.com` DNS çözümleme hatası görüldü (`Could not resolve host: github.com`); bu nedenle 71 testin yerel PASS koşumu elde edilmedi.
- GitHub Actions run `44108249163`, commit `274a8604ab6e305fdbb571752cdbaff45fa00af3` için **completed/success** idi. Bu yalnızca V2 Main Production Security Gate; `Verify suspended publishers, no cron and immutable IBO` başarılı, `live-discovery-diagnostic` skipped. Bu run 71 yeni offline testin PASS olduğunu kanıtlamaz.
- Bir önceki güvenlik run `44102300785` de SUCCESS olarak raporlandı; aynı şekilde yeni testlerin tümünü çalıştırdığına dair kanıt değil.
- Gerçek yayınlarda AV/ASR/OCR/altyazı uçtan uca kabulü henüz tamamlanmadı. Örnek ASR workflow'unun mevcut olması tüm 18.074 kanalı test ettiği anlamına gelmez.

### Yeni sohbette ilk yapılacaklar
1. Bu devir notunu ve PR #365'in güncel head/merge durumunu oku; son commitleri ve branch'i doğrula.
2. `v2/run_backup_archive_tests.py --verbose` komutunun tüm test modüllerini gerçekten topladığına bak; eksik/bozuk test importlarını düzelt.
3. Repo için güvenilir GitHub Actions test workflow'u kullanarak tüm offline testleri çalıştır; log ve test sayısını kaydet. Güvenlik gate'i bu testlerin yerine sayma.
4. Ağ güvenliğini gerçekçi şekilde çöz: ffmpeg'in DNS çözümleme ve redirect sonrası özel IP'ye ulaşmasını ağ katmanında engelleyen güvenilir egress/proxy veya izole runner kur; yalnızca env bayrağına güvenme. SSRF/DNS rebinding/redirect testleri ekle.
5. Sınırlı, izinli gerçek yayın örnekleriyle AV decode, ASR, OCR, altyazı ve birleşik rapor kabulünü çalıştır; kanıtları anonim hash ile kaydet. Ses/video başarıları ve dil ipuçlarını birbirinden ayır; otomatik kesin Türkçe onayı verme.
6. Her aşamanın sonucunu bu dosyaya ekle. Tüm ön koşullar PASS olmadan 18.074 YEDEKLER taramasına geçme.

**Kullanıcıya açık durum:** Geliştirme kodları GitHub özellik dalına kaydedildi. Sistem henüz bitmiş veya kabul edilmiş değil. Ana İBO ve YEDEKLER'e dokunulmadı. Yeni sohbet bu kayıttan devam etmeli; kullanıcıdan aynı bilgileri tekrar isteme.

---

## 17 Kasım 2026 — URL DNS etiket doğrulaması ve IPv6 koruması

Ortak URL denetiminde boş DNS etiketleri, tire ile başlayan/biten etiketler ve alt çizgi gibi geçersiz karakterler reddediliyor. IPv6 adreslerinin iki noktalı sözdizimi ayrıca korunuyor. Yeni regresyon testi eklendi: **71 yazılı test**, PASS doğrulaması yok. Bu oturumda `git ls-remote` yeniden denendi, `Could not resolve host: github.com` hatası alındı. Bu nedenle gerçek test koşumu ve gerçek yayın kabulü hâlâ açık. DNS rebinding/redirect için ağ seviyesi izolasyon hâlâ zorunlu. Ana İBO ve YEDEKLER değiştirilmedi.

---

## 17 Kasım 2026 — ffmpeg protokol sınırı

`backup_text_sampler.py` (OCR ve altyazı) ile `spoken_language_sample_review.py` (ASR) ffmpeg çağrılarına `-protocol_whitelist file,http,https,tcp,tls,crypto` eklendi; diğer protokoller bu iki örnekleyicide varsayılan olarak açılmıyor. **Bu, DNS/HTTP redirect SSRF korumasının yerini tutmaz** ve bazı HLS kaynakları ek protokol gerektirdiğinde başarısız olabilir; başarısızlık kanıt olarak kabul edilmeyecek. Ortamda GitHub DNS çözümlemesi tekrar başarısız olduğundan 70 offline test hâlâ çalıştırılamadı; gerçek yayın kabulü de yapılmadı. Ana İBO/YEDEKLER değişmedi.

---

## 17 Kasım 2026 — Güvenli ağ çıkışı teyidi yoksa örnekleme durduruluyor

OCR/altyazı örnekleyicisi ve gerçek ASR örnekleyicisi, `MADSC55_SECURE_EGRESS_CONFIRMED=1` açıkça verilmedikçe güvenilmeyen URL'leri ffmpeg'e aktarmıyor. OCR yolu `SECURE_EGRESS_NOT_CONFIRMED` ile kanıtsız döner, ASR yolu çalışmayı durdurur. Yeni offline test eklendi: **70 yazılı test**, çalıştırılmış PASS sonucu henüz yok. **Bu ortam değişkeni ağ izolasyonunu kendi başına sağlamaz**; yalnızca güvenli proxy/egress kurulduktan ve doğrulandıktan sonra yetkili operatör tarafından ayarlanmalıdır. DNS rebinding/redirect için gerçek ağ seviyesi koruma ve uçtan uca yayın kabulü açık kalıyor. Yerel shell `github.com` DNS çözemediği için tüm testler burada henüz çalıştırılamadı. Ana İBO/YEDEKLER değişmedi.

---

## 17 Kasım 2026 — Yayın URL giriş kontrolü ek sertleştirme

Ortak `v2/backup_text_sampler.valid_url` denetimi artık geçersiz/taşan portları, tek etiketli iç ağ benzeri DNS adlarını ve `.invalid` uçlarını reddeder; ASR ve OCR/altyazı örnekleyicileri aynı kontrolü paylaşır. Bir yeni regresyon testi eklendi: **69 yazılı test**, çalıştırılmış PASS kanıtı henüz yok. DNS rebinding ve HTTP redirect kaynaklı SSRF riskleri yalnızca URL sözdizimiyle çözülemez: ffmpeg için ağ seviyesinde güvenli egress veya güvenilir proxy zorunlu. Ana İBO ve YEDEKLER'e dokunulmadı. Önce bu koruma ve gerçek test/AV-ASR-OCR-altyazı kabulü, sonra 18.074 tarama.

---

## 17 Kasım 2026 — ASR giriş doğrulamasını model yüklemesinden öne alma

`v2/spoken_language_sample_review.py` artık snapshot/playback hash kümesi, tekillik ve yayın seçimi kontrollerini **faster-whisper modelini yüklemeden önce** yapıyor. Hatalı raporlarla gereksiz model yüklenmiyor; mevcut `test_spoken_language_sample_review.py` uyumsuz kimlik reddini kapsıyor. Yerel ortamda `github.com` DNS çözümlenemedi; **68 testin PASS kanıtı henüz yok**. Ağ egress ve gerçek yayın kabulü hâlâ açık. Ana İBO/YEDEKLER değiştirilmedi.

---

## 17 Kasım 2026 — Kullanıcının kesin iş sırası ve durdurma koşulu

**ÖNCELİK DEĞİŞMEZ:** (1) DNS rebinding/redirect ve ffmpeg ağ çıkışı güvenliğini gerçekten kapat ve test et; (2) `python v2/run_backup_archive_tests.py --verbose` ile **68 yazılı testin** tamamını çalıştır, hata varsa düzelt, PASS kanıtını sakla; (3) gerçek yayınlardan ses/görüntü decode, Türkçe konuşma ASR, OCR ve altyazı kanıtlarını birleştirerek gerçek uçtan uca kabul yap. **Bu üç iş PASS olmadan** 18.074 YEDEKLER kanal taramasına, Türk kanalı sıralamasına, ilk 1003 kanalı izleyen liste yerleştirmesine veya ana İBO playlist mutasyonuna geçme. Otomatik güvenlik CI'nin başarısı 68 testin PASS olduğu anlamına gelmez. Yapılan tüm değişiklikleri ve kalan engelleri bu dosyada tut; başarısız/çalıştırılmamış testleri bitmiş gösterme.

---

## 17 Kasım 2026 — ASR örnekleme URL giriş koruması

Gerçek konuşma örnekleyicisi `v2/spoken_language_sample_review.py` artık yalnızca `http` öneki kontrolü yapmak yerine ortak `backup_text_sampler.valid_url` denetimini kullanıyor: yerel/özel IP adresleri, localhost, gömülü kullanıcı/parola, kontrol karakterleri ve `file:` URL'leri reddediliyor. Yeni güvenlik testi eklendi: **68 yazılı test**, henüz PASS koşumu yok. **Önemli:** DNS adı yeniden çözümleme ve HTTP yönlendirme yoluyla özel ağlara erişim riski hâlâ tamamen kapatılmış değil; güvenli ağ egress'i olmadan güvenilmeyen yayınlarda ffmpeg çalıştırılmamalı. Yerel shell GitHub DNS çözümlemesi yine başarısız oldu. Ana İBO/YEDEKLER değişmedi.

---

## 17 Kasım 2026 — Güvenlik CI gerçek sonuç teyidi

GitHub Actions **44108249163** (V2 Main Production Security Gate), commit `274a8604ab6e305fdbb571752cdbaff45fa00af3` için **completed/success**. `Verify suspended publishers, no cron and immutable IBO` işi başarılı, `live-discovery-diagnostic` işi skipped. Bu koşum, yeni 67 backup-archive Python testinin tamamını çalıştırdığını kanıtlamaz; onlar için `python v2/run_backup_archive_tests.py --verbose` çalıştırılıp gerçek PASS çıktısı saklanmalı. Mevcut playlistler değiştirilmedi. Gerçek yayın kabulü ve güvenli egress tamamlanmadan 18.074 YEDEKLER taşıması yapılmayacak.

---

## 17 Kasım 2026 — ASR/OCR/altyazı veri alımı sınırları

ASR ve OCR/altyazı kanıt içe alma köprüleri artık tek raporda **en fazla 16 örnek** kabul ediyor; örnekleyicilerin mevcut 1–16 güvenlik sınırıyla uyumlu. İki taşma regresyon testi eklendi. **67 yazılı test**; çalıştırılmış PASS kanıtı hâlâ yok. 18.074 envanter taraması bu sınırla karıştırılmamalı: 16 sınırı gerçek yayın örneklemesinin *tek partisi* içindir, tüm envanter sayısı değildir. GitHub PR #365 üzerinde, ana İBO/YEDEKLER değiştirilmedi. Öncelik: gerçek Python test koşumu, güvenli ağ çıkışı, gerçek AV/ASR/OCR/altyazı kabulü, sonra tarama.

---

## 17 Kasım 2026 — Gerçek ASR örnekleyicisinde kritik tutarlılık düzeltmesi

`v2/spoken_language_sample_review.py` mevcut snapshot ve playback kayıtlarını önceden **yalnızca sayıyla** karşılaştırıyordu; aynı sayıda ama farklı kanallara ait raporlar yanlış eşleşebilirdi. Artık URL SHA256 kümelerinin tam eşleşmesi ve tekilliği zorunlu. Ayrıca mevcut ASR raporunun üzerine yazma engellendi (`open("x")`). `v2/test_spoken_language_sample_review.py` iki güvenlik regresyonu eklendi ve test çalıştırıcısına bağlandı. **65 yazılı test**; henüz çalıştırılmış PASS kanıtı yok. GitHub branch PR #365, ana playlist ve YEDEKLER'e dokunulmadı. Gerçek AV/ASR/OCR/altyazı kabulü, ağ egress güvenliği ve test çalıştırması sırada.

---

## 17 Kasım 2026 — Dört sinyalin birleşik entegrasyon testi

`v2/test_backup_archive_integration.py` içine yeni uçtan uca test eklendi: aynı kanalda AV doğrulaması + ASR Türkçe ipucu + OCR Türkçe ipucu + altyazı Türkçe ipucu tek anonim raporda birleşir, ancak operatörce doğrulanmadığı için `UNCERTAIN` kalır. Ham metin ve URL rapora sızmaz. **63 yazılı test**; gerçek PASS sonucu henüz yok. Yerel shell `github.com` DNS çözemediği için repo klonlanıp burada test edilemedi. Önce 63 Python testini gerçek koşumla doğrula, sonra gerçek yayın AV/ASR/OCR/altyazı kabulü ve ağ egress güvenliği, sonra 18.074 YEDEKLER taraması. Ana İBO ve YEDEKLER değişmedi.

---

## 17 Kasım 2026 — OCR + altyazı entegrasyonu tamamlanan kod bağlantısı

Yeni `v2/backup_text_hint_import.py`, mevcut `backup_text_batch.py` raporundaki OCR ve Türkçe altyazı ipuçlarını URL SHA256 ile güvenli biçimde içe alır. `v2/backup_archive_offline.py` yeni isteğe bağlı `--text-hints` argümanıyla AV, ASR, OCR ve altyazı inceleme ipuçlarını **tek JSON raporunda** sunar; ham URL/metin taşınmaz ve hiçbir ipucu otomatik Türkçe onayı vermez. `v2/test_backup_text_hint_import.py` beş negatif/pozitif senaryo eklendi; test çalıştırıcısına bağlandı. **62 yazılı test** (57+5); PASS henüz kanıtlanmadı. Birleştirme kodu hazır olsa da gerçek yayın örneklemesi, model kabulü, güvenli ağ egress'i ve 18.074 kanal taraması henüz yapılmadı. Ana İBO/YEDEKLER değişmedi.

---

## 17 Kasım 2026 — Mevcut gerçek ASR çalışma yolu tespit edildi
`.github/workflows/v2-spoken-language-existing-snapshot.yml` ana dalda zaten mevcut ve manuel `workflow_dispatch` ile çalışıyor. Önceki Actions çalışması 40948768782'nin oynatma ve özel snapshot artifact'larını indiriyor; 16 akıştan 15'er saniyelik `faster-whisper` konuşma örneklemesi yapıp `existing-snapshot-spoken-language-evidence` adlı anonimleştirilmiş artifact yayımlamayı hedefliyor. Bu workflow'un geçmiş artifact'larının hâlâ indirilebilirliği, gerçekten başarılı çalışması ve güncel 18.074 envanteri kapsaması **doğrulanmadı**. Bu yol tüm envanterin kabulü değildir. GitHub DNS bağlantısı bu oturumdaki yerel shell'de başarısız; burada Python regresyonları çalıştırılmadı. DNS/redirect egress riskleri açık; normal yayın alan adlarını bütünüyle kapatacak geçici kod değişikliği geri alındı. Sonraki adım: uygun GitHub Actions çalışma/kanıt yoluyla 57 offline testin gerçek PASS çıktısı ve ardından sınırlı gerçek ASR+OCR+altyazı kabulü. Ana playlist/YEDEKLER değişmedi.
---

## 17 Kasım 2026 — Rapor koruması ve test çalıştırma engeli

`v2/backup_archive_offline.py` mevcut sonuç raporunu artık **asla üzerine yazmaz**; `open("x")` kullanır. `v2/test_backup_archive_offline.py` mevcut raporun içeriğinin korunduğunu doğrulayan yeni test içerir. Toplam **57 yazılı test** (49 temel + 6 ASR + 1 entegrasyon + 1 rapor koruması). GitHub güvenlik CI başarısı bu 57 Python testinin PASS olduğu anlamına gelmez. Bu oturumdaki yerel ortam GitHub DNS erişimi sağlamıyor; testler bu ortamda henüz çalıştırılmadı. Eksik: güvenilir Python test çalıştırması, gerçek yayınlarda AV+ASR+OCR+altyazı kabulü, güvenli DNS/redirect egress, ardından 18.074 YEDEKLER taraması. Ana İBO ve YEDEKLER'e dokunulmadı.

---

## 17 Kasım 2026 — ASR ipuçlarının raporda korunması

Önceki offline entegrasyonda ASR ipuçları içe alınıyor ama sonuç raporuna taşınmıyordu. `v2/backup_archive_offline.py` düzeltildi: isteğe bağlı `--speech` raporundan yalnızca `url_sha256`, `spoken_turkish_hint` ve **false** `language_evidence_verified` alanları ile `speech_review_hint_count` çıkar; ham URL, konuşma metni ve otomatik dil onayı yok. `v2/test_backup_archive_integration.py` bu çıktıyı doğrulayan assert'lerle genişletildi. **56 yazılı test**, koşulmuş PASS kanıtı henüz yok. Ana playlist ve YEDEKLER değişmedi. Öncelik: gerçek test koşumu, ASR+OCR+altyazı+AV kabulü, ardından 18.074 taraması.

---

## 17 Kasım 2026 — ASR ipucu offline kabul hattına bağlandı

`v2/backup_archive_offline.py` artık isteğe bağlı `--speech` parametresiyle mevcut `spoken_language_sample_review.py` ASR raporunu `backup_speech_evidence.import_speech_hints` üzerinden alır; URL/metin rapora yazılmaz; ASR Türkçe tahmini tek başına Türk kanalını **asla onaylamaz**. `v2/test_backup_archive_integration.py` yeni uçtan uca negatif kabul senaryosu eklendi. **56 yazılı test**; yerel/CI Python test çalıştırması henüz kanıtlanmadı. GitHub güvenlik koşusu `44102300785` önceki committe SUCCESS idi; yeni HEAD için ayrı kontrol gereklidir. **Eksik:** gerçek ASR/AV/OCR/altyazı örneklemesi, test koşum kanıtı, DNS/redirect egress güvenliği. Kullanıcı isteği gereği YEDEKLER 18.074 ve ana İBO playlisti değiştirilmedi.

---

## 17 Kasım 2026 — ASR bağlantısı ve devam kaydı

Kullanıcı önceliği: **önce görüntü/ses, Türkçe konuşma, OCR ve altyazı entegrasyonunu bitir, sonra YEDEKLER'deki 18.074 kanalı tara; ana İBO listesine dokunma.** Mevcut `v2/spoken_language_sample_review.py` faster-whisper ASR örnekleyicisi keşfedildi; sıfırdan ASR kurulumu gerekmiyor. Ancak örnekleyici bağımsızdı ve tahminleri otomatik kabul etmemelidir.

Yeni `v2/backup_speech_evidence.py`: mevcut ASR raporundaki hash temelli dil tahminlerini güvenli, ham URL/metin içermeyen **yalnızca inceleme ipucu** biçimine çevirir; kanıtlanmış Türkçe olarak işaretlemez. `v2/test_backup_speech_evidence.py` altı regresyon senaryosu eklendi, `v2/run_backup_archive_tests.py` içine bağlandı. Toplam **55 yazılı test**; bunların çalıştırıldığına ilişkin PASS kanıtı henüz yok. Gerçek örnek ses+video decode, OCR, altyazı ve ASR testleri ile operatör onayı hâlâ eksik. Bu değişiklikler PR #365 özellik dalında, merge edilmedi.

---

## 17 Kasım 2026 — Öncelik sırası düzeltmesi: önce AV/ses dili/OCR/altyazı

**Kullanıcı talimatı:** Mevcut playlistin 18.074 kanallık YEDEKLER bölümü henüz işlenmeyecek. Önce görüntü/ses decode, konuşulan Türkçe, OCR ekran yazısı ve altyazı örnekleme sistemi bitirilecek ve gerçek test kanıtlarıyla kabul edilecek. Ana İBO ve YEDEKLER'e dokunulmayacak. Google Drive bu aşamanın kaynağı değil.

**Kontrol:** PR #365 HEAD `ced9c55b551fffb2104433a9d967da671de3eaec` security gate run **44100472265 SUCCESS**; job `Verify suspended publishers, no cron and immutable IBO` SUCCESS, `live-discovery-diagnostic` SKIPPED. Bu, 48 offline Python testinin ve gerçek AV/OCR/ASR örneklerinin PASS kanıtı değildir.

**Düzeltme:** `v2/backup_text_sampler.py` URL denetimi kontrol karakterlerini ve `.local` / `.internal` özel DNS son eklerini de reddeder (commit `3381eaa1296ccb9ac1d58aec49edf019613bf0c2`). Yeni negatif test (commit `9f23388339673ef463749ed0d7610d4021787149`). **49 yazılmış offline test**; son HEAD için gerçek çalıştırma PASS kanıtı yok. DNS rebinding ve redirect koruması ayrıca gereklidir. Bir sonraki zorunlu iş: sekiz offline test modülünü çalıştırıp raporlamak; örnek yayınlarda video+audio decode, ASR konuşma, OCR ve altyazı için bağımsız kanıt toplayıp kabul etmek; sonra 18.074 YEDEKLER taramasına geçmek. PR henüz merge edilmedi.

---

## 17 Kasım 2026 — Akıllı arşiv offline test çalıştırıcısı

**Yapıldı:** `v2/run_backup_archive_tests.py` eklendi (commit `76693c776a4a84d60cc6a06496779fb5c821b1c0`). Depo kökünden `python v2/run_backup_archive_tests.py --verbose` komutu sekiz akıllı arşiv test modülünü tek seferde `unittest` ile çalıştırır ve hata kodunu korur. Yeni `.github/workflows` eklenmedi, production güvenlik kilidi değiştirilmedi. Bu komutun CI'da çalıştırıldığına dair kanıt henüz yoktur; 48 test **yazılmıştır, geçmiş sayılmamıştır**. Önceki HEAD `95b43252d87bbe5539f52020b28e5ab51fa743b6` için run `44100276639` kontrol anında `in_progress` idi; mevcut güvenlik job'ı kendi regresyon adımlarını çalıştırır, yeni sekiz modülü çalıştırdığını göstermiyor. 18.074 kanal taraması ve PR merge yapılmadı; İBO/YEDEKLER korunuyor.

---

## 17 Kasım 2026 — Playback aktarımındaki doğrulama alanı düzeltmesi

**Doğrulandı:** PR #365 önceki HEAD `962d055aa29bf70ac40e6ac06dc234c4b2627c68` için GitHub `V2 Main Production Security Gate` run **44099552093 SUCCESS**. Bu güvenlik gate'i tüm Python testlerini çalıştırmaz.

**Yapıldı:** `v2/backup_playback_import.py` gerçek `stream_probe` kayıtlarının `status=AV_VERIFIED` ve `decode_status=DECODED_AV` alanlarını da aktarır; böylece `backup_evidence_adapter.join_evidence` kanıtı kaybetmeden doğrulanmış AV'yi değerlendirebilir. Bozuk playback hash'leri reddedilir. Kod commit `8be2b0dc9b15d24b315667ac3071480af375697a`, iki test commit `6b83fa2fe9bc10b29d52f24b7418eb7a3c971a3b`, iki modüller arası uçtan uca sınıflandırma testi commit `0a9790e69cf49aeeef53749f72b98f21f5b8b801`. Toplam **48 yazılmış offline test senaryosu**. Yeni HEAD için test ve CI PASS henüz doğrulanmadı. 18.074 gerçek kanalın tam taraması ve PR merge yapılmadı. Ana İBO/YEDEKLER korunuyor.

---

## 17 Kasım 2026 — OCR/altyazı akış URL güvenlik kontrolü

**Doğrulandı:** PR #365 önceki HEAD `363e90e547fe326fe875e97fef2906200c43368a` için security gate run **44098139164 SUCCESS**. Güvenlik gate'i 42 Python testinin tamamının çalıştırıldığı anlamına gelmez.

**Yapıldı:** `v2/backup_text_sampler.py` yerel/özel/metadata IP literal adreslerini ve `localhost` alan adlarını reddediyor; bozuk URL ayrıştırma istisnalarını da güvenli biçimde reddediyor (commit `3cfb146e440bfb82c9119f7d06c5d091cc5f4ece`). `v2/test_backup_text_sampler.py` içine iki test eklendi (commit `521b94d57c3ebe9097e2e9d34a8408488d888917`). Toplam yazılmış offline test senaryosu **44**. **Sınır:** DNS üzerinden özel IP'ye çözümlenen alan adları ve yönlendirmeler için ağ çıkışında ayrıca koruma gerekir; kodun mevcut URL kontrolü tam SSRF önlemi değildir. Son HEAD için CI ve 44 Python testinin geçişi henüz doğrulanmadı. 18.074 gerçek kanal taraması yapılmadı; ana İBO ve YEDEKLER korunuyor, merge yok.

---

## 17 Kasım 2026 — Mevcut playback aggregate veri köprüsü

**Yapıldı:** `v2/backup_playback_import.py` mevcut `all-source-playback-aggregate.json` formatındaki `channel_results` verilerini akıllı arşivin `by_url_sha256` formatına salt okunur dönüştürür. Envanter kimlikleri tam eşleşmeli, tekrarlar ve eksik `coverage_complete` reddedilir. Kaynak aggregate yalnız `VIDEO_DECODED`/`AUDIO_DECODED` yazıyorsa gerçek decode kanıtı otomatik uydurulmaz; `decoded_av_verified` sadece açıkça `True` ise taşınır. Kaynak dosyalar ve mevcut çıktı üzerine yazılmaz. Kod commit `28585215dde3b2895e87b5607f99f8946e05bdc4`, kimlik sertleştirmesi `defe894301c35c313614c7e3d3308d53a1a3f76e`. Dört yeni offline test commit `6491757e40cba5caad0deaca61d4fe772b966614`. Toplam yazılmış offline senaryo **42**. Önceki HEAD `7f89c65a166ed5acf40a6c05db89e278ee1f105f` security run `44097911777` kontrol anında `in_progress` idi. Son commit için CI PASS henüz doğrulanmadı. Gerçek 18.074 kanalın envanter ve aggregate dosyaları bu işlemde okunup çalıştırılmadı. Ana İBO/YEDEKLER korunuyor, PR merge edilmedi.

---

## 17 Kasım 2026 — Test envanteri denetimi ve güvenlik kontrolü

**Doğrulama:** Önceki HEAD `34f9b38b56340214b2a92ad7dd139178cc917f6b` için GitHub security gate run **44097374984 SUCCESS**. Sonraki HEAD `56ed4a671e028180243e26fd63a5a7d1e27f4c05` için run **44097756792** kontrol anında `in_progress` idi. `v2/test_backup_*.py` altı modülün test metotları tek tek sayıldı: smart archive **9**, adapter **11**, text evidence **6**, offline CLI **3**, text sampler **4**, batch **5** = **38 test senaryosu** (önceki notlarda 37 yazılmıştı; sayı düzeltilmiştir). Yazılmış olmak PASS anlamına gelmez. Batch testinde overwrite koruması ağ izni reddi ile karışmasın diye `run(src,out,1,2,True)` olarak düzeltildi (commit `95f75d68e45e332bad0fc080e3e7cac94692a8a1`). Bu testlerin tamamı GitHub Actions'ta henüz kanıtlı olarak koşturulmadı. Gerçek 18.074 yayın taraması ve PR merge eksik; ana İBO/YEDEKLER korunuyor.

---

## 17 Kasım 2026 — Toplu OCR/altyazı hata yalıtımı ve çıktı gizliliği

**Doğrulandı:** Önceki HEAD `34f9b38b56340214b2a92ad7dd139178cc917f6b` için `V2 Main Production Security Gate` run **44097374984 SUCCESS**. Bu sonuç yeni değişikliklerin unit test kabulü değildir.

**Yapıldı:** `v2/backup_text_batch.py` tek kanalın OCR/altyazı örnekleme hatasında tüm batch'i düşürmeden `SAMPLE_ERROR` olarak devam eder; çıktı yalnız açıkça izinli alanları içerir, örnekleyicinin beklenmedik ham metin/URL alanları dışarı sızamaz; örnekleyiciden gelen doğrulama bayrağı `True` olsa dahi otomatik dil onayı `False` kalır (commit `31f305886cbec3de6c394761511a881753211785`). Yeni regresyon testi hata izolasyonu, ham metin reddi ve otomatik dil onayı reddini kontrol eder (commit `f8b8932c09fcbfba9453637132618c6f6739da58`). Toplam yazılmış offline test senaryosu **37**. Son HEAD'in CI sonucu henüz doğrulanmadı. Gerçek 18.074 tarama, canlı OCR/ASR ve merge yapılmadı. Ana İBO ve YEDEKLER değiştirilmedi.

---

## 17 Kasım 2026 — Toplu OCR/altyazı ağ erişimi için açık izin

**Yapıldı:** `v2/backup_text_batch.py` artık ağ üzerinden akış örneklemesi başlatmak için açık `--allow-network` bayrağı gerektiriyor; varsayılan çalıştırma ağ erişimini reddediyor (commit `d34a88b8ac53a2ab70b54ec83cd9ab3ff7e96a3e`). Üç mevcut test bu açık izne uyarlandı; yeni test varsayılan ağ reddini doğrular (commit `3bc041be942c683e3893ae1ef8fdd88ef232fe3b`). Hazırlanan toplam offline senaryo **36**. Önceki HEAD `35399ce...` security gate run **44097151792** kontrol anında in_progress idi. Bu yeni HEAD için PASS doğrulanmadı. Gerçek 18.074 kanallık tarama veya merge yapılmadı; İBO ve YEDEKLER korunuyor.

---

## 17 Kasım 2026 — Sınırlı OCR/altyazı toplu örnekleme bağlantısı

**Doğrulandı:** PR #365 önceki HEAD `585a55bb4d1a5823a9068e499fce013019513d67` için GitHub `V2 Main Production Security Gate` run **44096050377 SUCCESS**. Bu güvenlik kontrolüdür; tüm Python unit testlerinin koştuğunu kanıtlamaz.

**Yapıldı:** `v2/backup_text_batch.py` yerel JSON snapshot `candidates` kayıtlarından URL hash'ine göre tekilleştirerek manuel tetiklenen, 1–16 kanal ve kanal başına 2–15 saniye limitli OCR/altyazı örneklemesi yapar. `backup_text_sampler.sample` kullanır; ham URL, altyazı, OCR metni rapora yazılmaz; sadece inceleme ipuçları. Var olan çıktı dosyasını ve kaynak dosyasını üzerine yazmayı reddeder. Kod commit `9aff105f1b8d6364fb62a1fa19c740b10eef24b1`, 3 yeni offline test commit `2aa8dae601a531df367286c942f0b63753c6508c`. Yazılmış toplam test senaryosu **35**.

**Eksik ve sınır:** 18.074 kanalın tam taraması yapılmadı; bu yalnız küçük partili manuel opt-in örnekleme. Son commit CI sonucu, gerçek yayın doğrulaması, OCR/altyazı dil paketleri, tam ASR+AV+OCR/altyazı orkestrasyonu ve kabul testleri bekliyor. İBO ve YEDEKLER değişmedi; PR merge edilmedi.

---

## 17 Kasım 2026 — Offline CLI import hatası giderildi

**Doğrulandı:** OCR/altyazı örnekleyicisi ve 32 yazılmış testin bulunduğu commit `585a55bb4d1a5823a9068e499fce013019513d67` için GitHub `V2 Main Production Security Gate` run **44096050377** = **success**. Bu güvenlik kapısı 32 offline testin çalıştığını **kanıtlamaz**.

**Düzeltildi:** `v2/backup_archive_offline.py` doğrudan CLI olarak çalıştırıldığında `backup_evidence_adapter.py` içindeki yalnız göreli `from .backup_smart_archive` importu paket bağlamı olmadığı için hata veriyordu. Adaptör artık hem `python -m v2.backup_archive_offline` hem `python v2/backup_archive_offline.py` çağrılarına uyumlu (commit `60d96a50d06621ec3085b3923c7d1ff3bdc370f4`). Doğrudan CLI `--help` smoke test eklendi (commit `72d342ec46d4f4d0ff18b15c45bf5787fa9d2059`). Toplam yazılmış offline test **33**; son değişikliklerin CI sonucu henüz doğrulanmadı.

**Eksikler:** 18.074 gerçek envanter girdisinin erişimi, kanıt şeması eşleştirmesi, OCR/altyazı ve konuşma örnekleyicilerinin kontrollü toplu yürütümü, 33 offline testin gerçekten koşulması ve kabul, PR merge. İBO ve YEDEKLER değiştirilmedi.

---

## 17 Kasım 2026 — İstenen gerçek OCR ve altyazı örnekleyicisi

**Yapıldı:** `v2/backup_text_sampler.py` tek bir açıkça seçilmiş HTTP(S) akışından en çok 2–15 saniyelik sınırlı FFmpeg işlemiyle tek video karesi çıkarıp yerel Tesseract OCR (`tur+eng`) denemesi ve ilk altyazı akışını SRT olarak örnekleme denemesi yapar. Her iki kaynak `backup_text_evidence.inspect_text_observations` içine girer; raporda ham OCR/altyazı metni veya URL bulunmaz, yalnız inceleme ipucu bulunur; `language_evidence_verified=False`, `review_approved=False` sabittir. Eksik FFmpeg, eksik OCR modeli, altyazısız akış veya başarısız örnekleme hiçbir zaman Türkçe doğrulaması sayılmaz. Kod commit `fe4dfbab5da3de7fbdba21f10da98e8cd61d9138`; dört offline test commit `c29922611d9d1379131843bf5a77d6557dd6fada`. Yazılmış toplam test senaryosu **32**.

**Önemli eksik:** Bu tek-akış örnekleyicisi henüz 18.074 kanal batch sistemine bağlanmadı, gerçek kanal üzerinde çalıştırılmadı, CI PASS doğrulanmadı. OCR için Tesseract tur+eng dil verileri, FFmpeg ve ses için mevcut `spoken_language_sample_review.py` faster-whisper gerekir; bunların runner'da kurulu olduğu doğrulanmadı. Altyazı türüne göre SRT çıkarma başarısız olabilir; başarısızlık belirsiz kalır. Ana İBO/YEDEKLER değişmedi. Sonraki adım test sonuçlarını kontrol etmek ve kontrollü/manuel tetiklenen, limitli batch entegrasyonu geliştirmek. PR #365 henüz merge edilmedi.

---

## 17 Kasım 2026 — Kanıt tipleri güvenlik düzeltmesi

**Yapıldı:** `backup_smart_archive.py` doğrulanmış dil, gerçek AV decode ve tükenmiş tekrarlar için truthy değer yerine yalnız Python `True` kabul edecek şekilde düzeltildi (commit `036b7cb2fd07eaf2ec3ef1b09ed977efab05e5c1`). JSON'daki `"true"` metni yanlışlıkla doğrulama sayılmayacak. Üç regresyon testi eklendi (commit `d9f64e93a75560340f7b893a0e7b40d019aecaf9`). Yazılmış toplam offline test **28**. Önceki güvenlik run `44094943848` kontrol anında in_progress idi; son commitler için PASS kanıtı yok. Gerçek 18.074 kanal taraması, OCR/ASR canlı entegrasyonu, batch, PR merge eksik; İBO ve YEDEKLER değişmedi.
---
## 17 Kasım 2026 — Akıllı arşiv: kimlik doğrulama sertleştirmesi

**Yapıldı:** `backup_evidence_adapter.py` envanter kimliklerinin küme işleminden ÖNCE 64 karakter küçük harf SHA-256 metni olmasını zorunlu kılıyor. Böylece bozuk liste/nesne kimlikleri beklenmeyen `TypeError` üretmek yerine açık `ValueError` ile reddediliyor. Commit `987e7ae401b7e1fae137204598ea9db739229db6`. İki regresyon testi eklendi: liste kimlik ve geçersiz hash reddi (commit `565aab1e3aeec74989b937db6f0753d65d4af725`). Toplam yazılmış offline test **25**. Önceki commit `9146ece...` güvenlik run `44094763759` kontrol anında devam ediyordu; son commitlerin CI sonucu henüz doğrulanmadı. Gerçek 18.074 kanal taraması ve PR merge hâlâ yapılmadı; ana arşiv/İBO değişmedi.

---

## 17 Kasım 2026 — Gerçek stream_probe şeması bağlantısı

**Yapıldı:** Mevcut `v2/stream_probe.py` gerçek çıktı şeması incelendi: başarılı FFmpeg decode sonucu `status=AV_VERIFIED`, `audio=true`, `decoded_av_verified=true`, `decode_status=DECODED_AV`; salt ffprobe meta sonucu `AV_STREAMS_PRESENT` ve `decoded_av_verified=false`. `backup_evidence_adapter.py` bu gerçek şemayı destekleyecek biçimde güncellendi (commit `f561ff5f753a38cb38caf846963424d9cd2351cb`). İki regresyon testi eklendi: gerçek decode kabul, metadata-only ret (commit `69abf55886f834adef1bf07e220cb15ea551b628`). Toplam yazılmış offline senaryo **23**. Önceki güvenlik run `44094555802` kontrol anında devam ediyordu. **Yeni commitlerin CI PASS kanıtı henüz yoktur.** Gerçek 18.074 tarama, dil OCR/ASR gerçek entegrasyonu, batch ve PR merge eksik. İBO ve YEDEKLER değiştirilmedi.

---

## 17 Kasım 2026 — PR #365 güvenlik doğrulaması ve bozuk envanter koruması

**Gözlem:** Güvenlik workflow'u önceki düzeltme commit'i `7bf43fa9baea6cd5f0909d6964edaca2a290c22b` için run **44094366504** olarak `in_progress` görüldü; başarı sonucu henüz yoktu. Sonraki kod değişiklikleri için CI yeniden kontrol edilmeli. `backup_evidence_adapter.py` bozuk/null envanter satırını açık `ValueError` ile reddedecek biçimde sertleştirildi (commit `6b6296b1d368a6e825bbaf031322938d206722b5`). İki yeni offline regresyon senaryosu eklendi (commit `8039bbe2e643b8459dec83e1033243e9c486f3f0`): bozuk envanter ve eksik playback. Toplam yazılmış offline senaryo **21**. Başarı koşusu henüz kanıtlanmadı.

**Sırada:** Son PR commit'inin security gate sonucunu ve test kapsamını doğrula; CI yeşil olmadan merge yapma. Gerçek rapor şema adaptörleri, güvenli batch tarama, gerçek OCR/altyazı çıkarımı ve 18.074 kapsama kabulü henüz yapılmadı. Ana İBO ve YEDEKLER değiştirilmedi.

---

## 17 Kasım 2026 — PR #365 kırmızı güvenlik testinin kök nedeni ve düzeltme

**Doğrulanan CI:** Commit `f47defdd54a3927e0956699beab5c843e77c011b` için GitHub Actions `V2 Smart Backup Archive Offline Tests` run **44094082917 SUCCESS**; `V2 Main Production Security Gate` run **44094082828 FAILURE**. Güvenlik işinin logunda `MAIN_WORKFLOW_FILE_LOCK_FAIL` / `WORKFLOW_INVENTORY unexpected: v2-smart-backup-archive.yml` görüldü; ana İBO playlist değişikliği `false`, güvenlik testindeki 10 unittest geçti. Sorun yeni ve henüz onaylanmamış workflow dosyasıdır; sınıflandırıcı test başarısızlığı değildir.

**Düzeltme:** Güvenlik envanterini gevşetmek yerine yeni `.github/workflows/v2-smart-backup-archive.yml` dosyası PR dalından kaldırıldı (commit `e858a9436fabea5c3d923ef7698c57e5ccf9bdd8`). Önceki 19 offline testin Python dosyaları korundu. **Düzeltmeden sonraki güvenlik CI sonucu henüz yeniden doğrulanmadı.** Yeni workflow ancak ayrı güvenlik onay süreciyle eklenebilir; şimdilik mevcut izinli test mekanizması kullanılmalı. PR #365 birleşmedi, 18.074 canlı tarama yapılmadı. Devam: son commit CI güvenlik sonucunu kontrol et, 19 offline testin güncel kodla yürütülmesini doğrula; sonra gerçek rapor dönüştürücü ve kontrollü tarama işçisi geliştir.

---

## 17 Kasım 2026 — Akıllı arşiv: salt-okunur rapor çalıştırıcısı

**Gerçekleşen:** `v2/backup_archive_offline.py` üç ayrı JSON kanıt girdisi (envanter, AV, incelenmiş dil) üzerinden `backup_evidence_adapter.join_evidence` kullanarak tek salt-okunur arşiv raporu üretir; varsayılan tam kapsam beklentisi 18.074, girdi dosyalarının üzerine yazma reddedilir, raporda kaynak URL/kanal adı bulunmaz. `v2/test_backup_archive_offline.py` iki yeni test senaryosu ve ayrı CI workflow'unda yeni testlerin çağrılması eklendi. Toplam yazılmış offline senaryo sayısı **19**. Commitler `fac4bb78d36400d28f3f1e323c4f4ca39ef0c57b`, `12d783baaf96dbe227aae8fadc0ca41d0ad6337a`, `4a382c7b588827642eea8fd6ba4b543e71b974f9`.

**Henüz tamamlanmadı:** Bu JSON girdi sözleşmesi gerçek tarama/ASR/OCR raporlarından otomatik üretilmiyor; gerçek OCR/altyazı çıkarma, 18.074 kanal AV kuyruğu, canlı kapsama kabulü, CI PASS doğrulaması ve PR birleştirmesi eksik. CI workflow dosyası yazılmış olsa da başarılı koştuğu iddia edilmez. Bir sonraki sohbet PR #365 ve bu notla başlamalı; önce CI hatalarını kontrol et, sonra gerçek kaynak şeması adaptörlerini ve bounded batch pipeline'ı ekle. Ana İBO/YEDEKLER korunmuştur.

---

## 17 Kasım 2026 — Akıllı arşiv: OCR/altyazı kanıt ipuçları ve bağımsız CI

**Bu oturumda eklendi:** `v2/backup_text_evidence.py` OCR ve altyazıdan gelen haricî gözlemleri sınırlı ve güvenli biçimde alır, Türkçe karakter/dil etiketi üzerinden yalnız inceleme ipucu üretir. OCR motoru veya altyazı indirme/çözme bu adımda YOKTUR. Ham yazı çıktı raporuna konmaz; dil doğrulandı veya kullanıcı onayladı şeklinde sahte kabul üretilmez. `v2/test_backup_text_evidence.py` altı yeni regresyon senaryosu; `.github/workflows/v2-smart-backup-archive.yml` üç yeni modülün compile + toplam 17 offline testini PR değişiminde koşturacak ayrı CI workflow'u. Commitler: `cb32a7c8d94e881c6e15d08086917c3f03a982a1`, `b656ce682c2e716b7383860327dfcb6a136d980f`, `5e1ace810bdfab594e4de7381dd7a8ea976f149a`.

**Kritik sınır:** Bunlar geliştirme dalında; test dosyalarının eklenmesi PASS demek değildir. CI koşusu ve başarısı ayrıca kontrol edilmeli. OCR gerçek video kareleri üzerinden, altyazı gerçek akış üzerinden henüz entegre edilmedi; toplu AV/ASR tarama işçisi, veri sözleşmesi ve gerçek 18.074 kapsama doğrulaması da eksik. Sıradaki adım PR #365 CI sonucunu denetlemek, varsa test sorunlarını düzeltmek, gerçek OCR/altyazı ve kuyruk entegrasyonunu tamamlamak. `DEVAM_NOTU.md` ve PR #365 başka sohbetten ilk okunacak yerlerdir. Ana İBO, YEDEKLER ve state.json değişmedi.

---

## 17 Kasım 2026 — Akıllı arşiv devamı: kanıt birleştirme adaptörü

**Yapıldı (yalnız PR #365 geliştirme dalı):** `v2/backup_evidence_adapter.py` ve `v2/test_backup_evidence_adapter.py` eklendi. Ayrı envanter, AV ve dil kanıtlarını URL hash kimliği üzerinden eşleştiren salt-okunur katman; mükerrer kimliği, eksik kapsamı ve bilinmeyen kanıt kimliklerini reddeder. Gerçek decode video+ses birlikte doğrulanmadıkça çalışan saymaz; yalnız kontrollü tekrar ve doğrulanmış terminal hata ile çalışmayan der. Türkçe/yabancı sınıfı için bağımsız dil kanıtı ve inceleme onayı birlikte gerekir; salt ASR ipucu/isim/metadata yetmez. Beş adaptör regresyon senaryosu yazıldı. Commitler: `d6276e35c0624dc462df8443d14a3b7b3fe51d1a`, `544bcdf4cf8ceb721d81f2711e8b4aa164171e1e`.

**Henüz yapılmadı:** Testler CI'da koşturulup PASS kanıtı alınmadı; mevcut canlı rapor formatlarına gerçek dönüştürücü, OCR, altyazı, batch tarama/yeniden deneme ve 18.074 kanallık kapsama kabulü eksik. Bu modül henüz mevcut workflow'a bağlı değildir; PR merge edilmedi. Bir sonraki oturum önce PR #365 ve DEVAM_NOTU'yu kontrol etsin, gerçek rapor şemalarıyla adaptörü bağlasın, offline test/CI koştursun; sonra OCR/altyazı eklesin. Ana İBO/YEDEKLER/ana arşiv ve kanonik görev durumları değişmedi.

---

## 17 Kasım 2026 — 18.074 akıllı arşiv geliştirmesi: ilk kod adımı (PR #365)

**Gerçekleşen:** `v2/backup_smart_archive.py` salt-okunur kanıt tabanlı sınıflandırma ve JSON raporlayıcı eklendi; `v2/test_backup_smart_archive.py` altı offline regresyon senaryosu eklendi. Kanallar TR/FOREIGN/UNKNOWN dil ve WORKING/NOT_WORKING/UNKNOWN durumlarından Türk çalışan, Türk çalışmayan, yabancı çalışan, yabancı çalışmayan, belirsiz kategorilerine ayrılır. Eksik dil kanıtı Türk/yabancı diye atanmaz; gerçek AV decode olmadan çalışan denmez; tekrarsız başarısızlıkta çalışmayan denmez. Tam envanter sayımı ve mükerrer kimlik kontrolü var. Sınıflandırıcı oynatma listesi yazmaz ve ağ taraması yapmaz.

**Kanıt/commit:** kod `85d98ccadf486588bf722c4c52c822748939c447`, test `d1b18e16abe905a66078bddba1c92320d54bf760`; PR https://github.com/Madsc55/MADSC55-TV-V2/pull/365. Test dosyası yazıldı, ancak Actions veya gerçek test koşusu başarı kanıtı henüz alınmadı. Kod yalnız geliştirme dalında, main'e birleşmedi.

**Sıradaki adım:** mevcut `stream_probe.py`, `spoken_language_sample_review.py` ve `turkish_language_evidence.py` sonuçlarını doğrulanmış ve şeması kontrol edilen tek kanıt sözleşmesine bağlamak; OCR ve altyazı tespitini ayrıca geliştirmek; URL ve özel veriyi rapora sızdırmadan güvenlik testleri; küçük offline fikstür testleri; ardından CI/PR denetimi. 18.074 canlı tarama ve otomatik yayın başlatılmayacak. Başka sohbet devamı için önce bu notu ve PR #365'in son durumunu oku, başka paralel PR'lerle çakışma kontrolü yap. Ana İBO/YEDEKLER ve state.json değişmedi; tamamlandı diye işaretleme.

---

## 17 Kasım 2026 — YAPILACAK: YEDEKLER 18.074 kanal toplu AV, Türkçe tanıma ve akıllı arşiv

**Durum: PLANLANDI / UYGULANMADI.** Kullanıcı isteği: YEDEKLER kategorisindeki 18.074 kanalı kayıpsız toplu denetlemek; Türk kanallarını isim/ülke/TR etiketi yanında gerçek Türkçe konuşma, ekrandaki Türkçe yazı ve Türkçe altyazı kanıtlarıyla mümkün olduğunca eksiksiz bulmak; çalışan/çalışmayan ve Türk/yabancı/belirsiz sınıflarına ayırmak. Sayı işlem başlangıcında gerçek envanterden yeniden doğrulanacak.

**Uygulama planı:**
1. Ana arşiv ve YEDEKLER'in değişmez snapshot, kanal kimliği, kaynak URL referansı, sıra ve sayımını al; tekrar eden kayıtları ayrı raporla, kayıt silme veya kayıp yok.
2. 18.074 kaydı kuyruk/batch ve sınırlı paralellikle test et: erişim, gerçek FFmpeg video decode, ses akışı ve duyulabilir ses; HTTP/timeout/DRM/geo-block gibi engelleri ayrı kodla. Tek başarısız ölçüm kalıcı ölü hükmü değildir; kontrollü tekrar dene.
3. Türkçe tespitini birleştir: ad/metadata (TR/TUR/Türkiye ve bilinen yayıncılar), ses üzerinden konuşma/dil tanıma, video karelerinden OCR ile Türkçe ekran yazısı, mevcut altyazı parçalarından dil tanıma. Türkçe kanıtı bulunmaması yabancı olduğunun kanıtı değildir. Sessiz, kısa örnekli, erişim engelli veya karışık dilli yayınlar belirsiz/inceleme kuyruğuna alınır; kanıt ve güven seviyesi kaydedilir.
4. Ana arşiv üzerinde silmeden mantıksal depolar oluştur: Türk çalışan, Türk çalışmayan, yabancı çalışan, yabancı çalışmayan, belirsiz; geçici arızalar için yeniden test kuyruğu. Dil sınıfı ile çalışma durumu ayrı alanlar olsun; sınıflar kanıta göre güncellensin. Kullanıcının istemediği kanallar aktif görünümden ayrılabilsin, ana arşivde kalsın.
5. Sonuç raporu: toplam/tekil/test edilen, AV doğrulanan, görüntü-ses eksik, erişilemeyen, TR konuşma/OCR/altyazı kanıtı, her depo sayısı, belirsizler, tekrar denemeler ve örnek kanıt referansları. Yanlış pozitif/negatif örnekleriyle kabul testi yap.

**Güvenlik ve kabul:** Ana İBO listesine, YEDEKLER'in özgün kayıtlarına/sırasına, YENİLER/FAVORİLER/EPG'ye ve eski MADSC-TV'ye izinsiz yazma yok. Sınıflandırma ayrı metadata/indeks katmanında; istenirse onaylı işlemle kategoriye taşıma/kopyalama. Mevcut #18/#31 AV kanıt altyapısı tekrar kullanılsın ama ses dili/OCR/altyazı gerçekten uygulanıp test edilmeden var sayılmasın. Tam 18.074 kapsamı ve rapor doğrulanmadan 'tamamlandı' işaretlenmesin. Mevcut #34 en son yapılacak kuralı ve kanonik görev durumları değiştirilmesin; bu not yeni plan kaydıdır, görev numarası atamaz.

---

## 15 Kasım 2026 — ÖNCELİKLİ: kullanıcı onaylı İBO düzenleme kapısı

Kullanıcının kurduğu esas iş akışı: kanal keşfi → ayrı adaylar → açık onayla YEDEKLER → cihazda gerçek görüntü/ses testi → çalışan kanalları kullanıcının talimatıyla ULUSAL-HEPSİ/HABER/SPOR/BELGESEL/SİNEMA vb. kategorilere kopyalama/taşıma → istenirse kanal ve kategori sırasını değiştirme. YEDEKLER'de kaynak kullanıcı aksini istemedikçe kalır. Ana listeye izinsiz otomatik yazma kesinlikle yasak. Kullanıcının açık talimatıyla yapılan kategori düzenlemeleri ise teknik olarak mümkün olmalıdır.

AÇIK TEKNİK ENGEL: `v2/main_actions_security_gate.py` yalnız YEDEKLER içi reorder kabul ediyor. PR üzerinden somut işlem onayı + değişiklik öncesi/sonrası kayıt denetimi + tam snapshot/rollback + regresyon testleri hazırlanmalı; güvenlik kapısı bu doğrulanmış onayları kabul etmeli, yetkisiz otomasyonları reddetmeli. Bu tamamlanmadan 'çözüldü' yazma. Eski MADSC-TV deposuna ve ana listeye bu notla hiçbir değişiklik yapılmaz.

---

## 15 Kasım 2026 — Kanonik bitirme akışı (kapanış kanıtı zorunlu)

**Kanonik durum:** `v2/tasks/state.json`: 21 completed / 13 in_progress. Açıklar: #15, #17, #18, #19, #20, #21, #28, #29, #30, #31, #32, #33, #34. Bu kayıt hiçbir görevi tamamlandı yapmaz.

1. **Aşama A — önce:** #15 tarihî kimlik ve 6 eksik hash / bağımsız yayıncı kanıtı; #17 kurtarma kuyruğu; #18 güncel gerçek ses+görüntü; #19 kesin EPG-ID ve 303 boşluk; #20 kurtarma kanıt zinciri; #21 TR/AZ/dünya/YouTube canlı kaynak devam testleri. Son canlı koşu #43608247496: 103/103 uygun M3U, 28.845 aday, 8.573 AV (8.540 eski + 33 yeni), 20.272 kanıtsız, 300 gerçek tekrar deneme. Altı görev açık.
2. **Aşama B:** #28 gerçek kanıtlı 1000 İBO, #29 gerçek kanıtlı 2000 İBO, #30 EXTINF/URL, ZIP, manifest, SHA-256. Sentetik paket nihai teslim değildir.
3. **Aşama C:** #31 gerçek cihaz görüntü/ses; #32 bağımsız haricî şifreli restore; #33 üretim kabulü. Önceki #13 Drive restore #32 kabulü yerine geçmez.
4. **Aşama D — en son:** #34 Türkiye/Azerbaycan/dünya, GitHub/Gist/GitLab/Codeberg/YouTube/resmî yayıncı M3U/M3U8 kapsamlı tarama.

**Her görev kapanışı:** kanonik state ve son commit/PR/Actions/artifact incele → eksikliği gider → offline ve gerekli gerçek canlı testleri yap → kanıt/başarı ölçütünü doğrula → yalnız o zaman `state.json` completed, tarih ve kanıt URL'leriyle güncelle → `DEVAM_NOTU.md` içine sonuç/engel/run/commit kaydet → sıradakine geç. Kanıtsız kapanış yok.

**Koruma:** Ana İBO, YEDEKLER, YENİLER, FAVORİLER, EPG ve eski MADSC-TV ayrı tutulur. Eşzamanlı PR körlemesine merge edilmez. Manuel canlı tarama ve üretim yayımlaması kendiliğinden başlatılmaz.


---

## 17 Kasım 2026 — PR #365 denetimi ve özel offline test CI kapısı

- PR #365 açık ve merge edilmemiş durumda. Geliştirme dalı: `plan/18074-kanal-akilli-test-arsiv-20261117`; bu denetimde önceki HEAD `6a3908e941cc028f2f478669999bc4bfee5a8cba` idi. PR #365'in 23 dosyalık değişiklikleri incelendi; ana dal Production Security Gate run `44120387105` SUCCESS, ancak bu koşudaki işler mevcut güvenlik/playlist koruma gruplarıdır; yeni akıllı arşiv test runner'ını çalıştırdığına dair kanıt değildir.
- `v2/run_backup_archive_tests.py` 11 unittest modülünü çağırıyor. Test dosyalarındaki `test_*` yöntemleri sayıldığında **71 test senaryosu** bulunuyor; bu, testlerin çalıştırıldığı veya geçtiği anlamına gelmez. Eski DEVAM_NOTU içindeki 68/70/71 sayıları yazılı test sayımıdır, PASS sonucu değildir.
- PR dalına `.github/workflows/v2-backup-archive-offline-tests.yml` eklendi (commit `f1b7b7fdd0903f2b2e087cf79bf47d13677e0028`). Workflow yalnızca PR değişikliklerinde veya manuel dispatch ile 11 modülü `python v2/run_backup_archive_tests.py --verbose` komutuyla çalıştırmayı hedefler; canlı yayın taraması ve playlist yazımı yapmaz. Bu commit için henüz Actions run görünmedi; dolayısıyla 71 testin PASS/FAIL sonucu **bilinmiyor**.
- Yerel clone/test girişimi GitHub DNS çözümlemesi nedeniyle başarısız oldu: `Could not resolve host: github.com`. Bu nedenle yerel PASS kanıtı da yok.
- Güvenlik incelemesi: ASR ve OCR/altyazı örnekleyicileri `MADSC55_SECURE_EGRESS_CONFIRMED=1` kontrolü yapıyor; bu değişken tek başına DNS rebinding, HTTP redirect veya özel IP'ye ağ erişimini engellemez. `backup_text_sampler.valid_url` sözdizimi ve ilk IP kontrolleri gerçek DNS çözümleme/yönlendirme sonrası egress izolasyonunun yerine geçmez. Gerçek ağ katmanı güvenli proxy/egress doğrulanmadan değişken açılmayacak ve güvenilmeyen gerçek yayınlar ffmpeg'e verilmeyecek.
- OCR ve altyazı örnekleyici kodu mevcut; fakat gerçek yayın karelerinden OCR, gerçek HLS altyazı çıkarımı, ASR ile birlikte sınırlı izinli gerçek yayınlarda uçtan uca kabul henüz yapılmadı. ASR dil modeli çıktısı, OCR ve altyazı sonuçları inceleme ipucudur; otomatik Türkçe onayı değildir.
- **Sıradaki adım:** özel workflow'un gerçek Actions koşusunu elde edip 71 testin her birinin sonucunu incelemek; başarısızları düzeltmek. Sonra DNS/redirect/SSRF engelleyen gerçek egress katmanını kurup ayrı güvenlik testleriyle kanıtlamak; ardından sınırlı izinli gerçek yayınlarda AV+ASR+OCR+altyazı uçtan uca örnek kabulü yapmak.
- Ana İBO playlisti, YEDEKLER, YENİLER, FAVORİLER, EPG ve görev durumları değiştirilmedi. 18.074 kanal taraması başlatılmadı. PR #365 birleştirilmedi.

---

## 17 Kasım 2026 — OCR/altyazı FFmpeg protokol whitelist düzeltmesi

- Kod incelemesinde OCR kare çıkarma çağrısında `-protocol_whitelist file,http,https,tcp,tls,crypto` bulunduğu, fakat aynı örnekleyicideki ayrı altyazı çıkarma FFmpeg çağrısında eksik olduğu tespit edildi. Altyazı çağrısına da aynı açık whitelist eklendi.
- Yeni regresyon testi `test_subtitle_extraction_uses_protocol_whitelist`, gerçek altyazı komutunun whitelist bayrağını ve tam protokol listesini taşıdığını doğrulayacak şekilde eklendi. Kod commit: `6ea7214fa4eb7c21c50aa6b0077be0c73474bf58`; test commit: `06462990f58b095e0e38b16da3cfb5f4a9dd2960`.
- Test henüz çalıştırılmadı; test sayısı **72 yazılı senaryo** (önceki 71 + bu regresyon) olarak güncellendi, PASS iddiası yok. Özel offline Actions workflow'unun bu son commitlerde gerçekten tetiklenip tetiklenmediği ayrıca doğrulanmalı.
- Bu whitelist yalnız FFmpeg protokol yüzeyini sınırlar; DNS rebinding/HTTP redirect sonrası özel IP erişimini önleyen ağ katmanı egress koruması değildir. Güvenli egress doğrulanmadan gerçek yayın örneklemesi başlatılmayacak.
- Ana İBO playlisti, YEDEKLER ve diğer korunan listeler değişmedi; 18.074 kanal taraması başlatılmadı.
