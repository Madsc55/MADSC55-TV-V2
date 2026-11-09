## 9 Kasım — V2 DEVAM: #13 AWS CLI kurulum ve eski offline artifact kontrolü

- `353bf909`: bağımsız S3 restore workflow'u sabitlenmemiş `awscli` pip kurulumunu kaldırdı; GitHub-hosted runner'daki `aws` ikilisini `command -v aws` / `aws --version` ile doğrular. Şifreleme kütüphanesi sabit `cryptography==44.0.2` kalır. Gerçek AWS erişimi ve versioned restore henüz doğrulanmadı.
- Daha eski, mevcut `github-actions-artifact-13677940957.zip` offline artefaktı yerel olarak incelendi: `unittest.log` **829 test OK (skipped=3)**, `playlist.log` **840 kanal, 2 yedek, 13 kategori, 47 keşif kaynağı PASS** bildiriyor. Bu eski artefaktın en son geliştirme commit'i ile aynı SHA'ya ait olduğu doğrulanmadı; 3 skipped test bulunduğundan son toplu kabul veya #13/#26 için yeşil kanıt sayılmaz.
- Bu oturumda son commit'e ait Actions run/job ID ve gerçek S3 restore sonucu alınamadı. Görevler açık; 8/33. main, PR #9, korunan ana İBO, kategoriler ve tarihî 4.955 baseline değişmedi.

## 9 Kasım — V2 DEVAM: gerçek S3 workflow bağımlılık kontrolü

- `fe894d70`: S3 restore workflow'unda varlığı bu ortamda doğrulanmamış sabit `awscli==1.42.68` sürümü yerine `awscli` kurulumu ve `aws --version` kontrolü eklendi; `cryptography==44.0.2` sabit kalır. Bu değişiklik gerçek restore kanıtı değildir.
- GitHub commit-workflow-run sorgusu `fe894d70` ve `589b0f72` için `workflow_runs: []` döndürdü. Bu uç nokta push çalışmaları için eksik sonuç verebildiğinden, **run başlamadı / başarılı / başarısız** sonucu çıkarılmadı. Gerçek Actions run ID, log ve versioned S3 kabulü halen doğrulanamadı.
- #13 açık; 8/33. Ana İBO, main, PR #9, tarihî 4.955 kayıt değişmedi. Saatlik otomasyonla eşzamanlı yazmayı önlemek için dosya blob SHA'sı taze okundu.

## 9 Kasım — V2 DEVAM: #13 gerçek S3 restore kabul workflow'u

- `589b0f72`: `.github/workflows/v2-s3-restore-acceptance.yml` eklendi. Geliştirme dalındaki ilgili dosya push'larında ve manuel dispatch ile bağımsız versioned S3 `get-object` + SHA256 + AES-GCM + 4.955 tarihî kimlik kabulünü `v2/independent_s3_restore.py` üzerinden yürütür. `concurrency.cancel-in-progress: false`, read-only repository yetkisi, 65 dakikalık job timeout, eksik secret için fail-closed kapısı ve Actions run/commit özeti bulunur.
- Dış erişim gereksinimleri: `V2_S3_RESTORE_AWS_ACCESS_KEY_ID`, `V2_S3_RESTORE_AWS_SECRET_ACCESS_KEY`, `V2_S3_RESTORE_AWS_REGION`, `V2_S3_RESTORE_BUCKET`, `V2_S3_RESTORE_OBJECT_KEY`, `V2_S3_RESTORE_VERSION_ID`, `V2_S3_RESTORE_PINNED_SHA256`, `V2_ARCHIVE_KEY_HEX` (isteğe bağlı AWS session token). Bağımsız pinlenmiş SHA ve gerçek sürüm olmadan #13 kapanmaz.
- Workflow commit'i yapıldı fakat **gerçek S3 çalışması ve Actions run sonucu bu oturumda doğrulanmadı**; #13 açık, 8/33. Ana İBO/main/PR #9/tarihî baseline korunuyor. Devam: gerçek workflow job logunu al, gerekirse secrets/izin engelini kaydet, bağımsız işlere geç.

## 9 Kasım — V2 DEVAM: Task Engine CI hata logları

- `7a091fe2`: `v2-master-engine.yml` içinde 33 görev Task Engine testleri `task-engine.log` dosyasına yazılır; test hatası sonraki grouped/compile/offline testleri ve artifact yüklemesini engellemez. `steps.task_engine_tests.outcome` son fail-closed kapısına eklendi: skipped/failure hiçbir durumda başarı sayılmaz.
- GitHub Actions için yeni run ID veya doğrulanmış test sonucu bu oturumda elde edilmedi. Görev #26 henüz kapatılmadı; 8/33. Saatlik otomasyonla yazma çakışması önlemek için güncel blob SHA kontrol edildi. main, PR #9, ana İBO ve 4.955 tarihî baseline değiştirilmedi.

## 9 Kasım — V2 DEVAM: #26 derleme ve offline regresyon logları

- `688bbd61`: Master Engine offline-tests işinde derleme ve tüm offline regresyon adımları artık kendi sonuçlarını `steps.compile_modules.outcome` / `steps.offline_regressions.outcome` olarak saklıyor. `continue-on-error` yalnızca log toplamak için; derleme, toplu arşiv/AV kabulü veya genel regresyon başarısız/atlanan ise son fail-closed kapısı job'u başarısız bitiriyor. `compile.log`, `unittest.log`, `playlist.log` ve `acceptance-11-13-14-16.log` artifact kapsamındadır.
- Değişiklik geliştirme dalına commit edildi. Bu commit için gerçek GitHub Actions run ID / test sonucu henüz doğrulanamadı. #26 kapanmadı; 8/33. Saatlik otomasyonla çakışmamak için GitHub dosya SHA'sı her yazmadan önce okundu. main, PR #9, ana İBO ve 4.955 tarihî kayıt değişmedi.

## 9 Kasım — Actions hata loglarının tam toplanması (#26)

- `c575c179`: Master Engine offline işinde #11/#13/#14/#16 toplu kabul adımı hata verdiğinde sonraki genel offline regresyonların ve log artifact yüklemesinin atlanmaması için adım `continue-on-error` ile izlenir; **son fail-closed kapısı** `steps.grouped_acceptance.outcome != success` ise job'u kırmızı bitirir. Bu, testleri yeşile çevirmez; hata inceleme kapsamını genişletir.
- Geliştirme dalındaki push tetikleyicisi mevcut, workflow `concurrency.cancel-in-progress: false` ile aynı workflow koşularını sıraya alır; bu kilit GitHub dosya yazıcıları arasında atomik kilit değildir.
- Yeni push için gerçek Actions run/job/log sonucu bu oturumda henüz elde edilmedi. #26 ve diğer görevler açık, 8/33. Gerçek S3 versioned restore ve kullanıcı cihaz testi dış bağımlılıkları sürüyor.

## KALICI TALİMAT — MADSC55 TV V2 TÜM KALAN İŞLERİ BİTİR (9 Kasım 2026)

**Devam komutu: `V2 DEVAM`.** Her oturumda yalnızca `Madsc55/MADSC55-TV-V2` reposunun `madsc/v2-discovery-bulk-20261031` geliştirme dalında `[V2 SIRA]` GitHub kayıtlarını, `v2/tasks/master_tasks.json`, `v2/tasks/state.json` ve bu dosyayı yeniden oku. 33 görevin zaten kabul edilmiş 8 tanesini tekrarlama; kalan 25'i öncelik/bağımlılık sırasıyla **gerçek uygulama, test, Actions doğrulaması, commit ve görev durumu güncellemesi** ile ilerlet. Sadece durum raporu döngüsüne girme. Her küçük adımda yeniden onay isteme.

1. Önce Actions push/dispatch tetikleme, job logları, artifact, test bağımlılıkları ve güvenli yeniden denemeyi düzelt; geçerli son SHA için başarı kanıtını al. Başarısız, atlanan veya logu alınamayan job'u yeşil sayma.
2. #13 gerçek bağımsız, sürümlü S3 şifreli arşiv geri yüklemesini (bağımsız pinlenmiş SHA256, AES-GCM, 4.955 değişmez kimlik) kabul et; S3 yetkisi/sırları yoksa gerçek dış bağımlılık olarak işaretle, sentetik testle tamamlandı yazma.
3. #9, #11, #14, #16, #23, #25, #26 kabul şartlarını doğrula; sonra bağımsız/bağımlı kalan görevleri bitir. Gerçek FFmpeg görüntü+ses olmadan kanala AV kanıtı verme; tarihî 45/4.955 ve 2.643 kayıp adres için uydurma URL/kurtarma yazma.
4. Resmî kaynak, dünya/TR/AZ/YouTube canlı yayınları, GitHub/Gist/GitLab/Codeberg/Scribd/SlideShare/Internet Archive, `turkiye.m3u`, `tr.m3u8`, `turkish-iptv`, `canli-tv`, `yerel-tv`, `iptv-turkiye`, M3U/M3U8, XMLTV/EPG, kalite ve kaynak geçmişi keşiflerini görev sırasıyla kapsa; yalnızca gerçek AV ile doğrulanmışları paketle.
5. Yeni IBO 1000/2000 paketlerini oluştur ve test et; **main, PR #9, ana İBO listesi, YEDEKLER/YENİLER/FAVORİLER, kategoriler, 4.955 tarihî kimlik ve cihaz favorileri değiştirilemez.** Kullanıcı IBO Player cihaz testi #32 dış bağımlılıktır; kullanıcı yapmadan tamamlandı yazma.
6. Her aşamada `DEVAM_NOTU.md` ve görev durum dosyasına test sonucu, commit, gerçek Actions URL'si, kapananlar, kalanlar ve gerçek engelleri kaydet. İşler engellenirse gerekçesini yazıp bağımsız göreve geç. Saatlik otomasyonla çakışmamak için mevcut kilitleri koru; aynı dosyada eşzamanlı yazma yapma, SHA kontrolü ve güvenli tekrar deneme uygula. Hedef 33/33 **kanıtlı** kabul; dış bağımlılıkları açıkça belirt.

**Başlangıç durumu:** 8/33 tamam; 10 devam, 1 engelli, 14 bekleyen. Son değişikliklerin Actions kanıtı yok. Bu kalıcı talimatın eklenmesi görev kabulü veya test başarısı değildir.

## 9 Kasım — tarihî SHA üyelik hesaplaması

- `5737ad74`: #14 şifreli arşiv kabulünde tarihî SHA üyelik kümesi kayıt başına tek kimlik hesaplamasıyla kuruluyor; kabul şartı ve korunmuş baseline değişmedi.
- Yeni GitHub Actions run ID, yeşil test kanıtı veya gerçek uzak S3 restore kanıtı elde edilmedi. Bu turda hiçbir görev kapanmadı; 8/33. main, PR #9, ana İBO ve tarihî envanter korunuyor.

## 9 Kasım — Master Engine toplu kabul çıktısı

- `093475c4`: #11/#13/#14/#16 toplu offline kabul adımının `GITHUB_STEP_SUMMARY` çıkış kodu satırında tek ters bölü newline kaçışı kullanıldı; push tetikleyicisi geliştirme dalında mevcut.
- GitHub commit workflow-run sorguları boş ve son başarısız run #42672120731 yeniden çalıştırma isteği GitHub 403 ile reddedildi. Bu yüzden yeni Actions başarısı doğrulanmış değil. Test geçişi veya görev kapanışı iddia edilmiyor; 8/33.
- Uzak S3 versioned restore kanıtı ve gerçek AV kabul şartları tamamlanmadı; main, PR #9, ana İBO, tarihî envanter değişmedi.

## 9 Kasım — #14 tarihî kimlik işareti güvenliği

- `26866de0`: şifreli aday görünümünün `historical_not_reverified` değeri değişmez tarihî baseline SHA kimlik kümesiyle birebir karşılaştırılıyor; adayın kendini sahte biçimde tarihî olarak işaretlemesi veya gerçek tarihî işaretini gizlemesi reddedilir.
- `cb92cc65`: 4.955 gerçek tarihî kayıt + yeni geçerli URL içeren AES-GCM arşivde sahte tarihî üyelik bayrağının reddini sınayan regresyon eklendi.
- GitHub Actions yeni commit'ler için doğrulanmış sonuç vermedi; bu nedenle #14 kapatılmadı. Bağımlı #13 uzak S3 geri yükleme kanıtı ve diğer kabul koşulları açık. Genel durum 8/33. main, PR #9, ana İBO ve tarihî baseline değişmedi.

## 9 Kasım — #11 tam URL aday kümesi kayıp koruması

- `8ca5e9d1` ve `a609c3eb`: `archive_acceptance_gate.check` yalnızca adayların ham URL'lerden türediğini değil, **her geçerli ham URL kimliğinin** aday görünümünde tam bir kez bulunduğunu doğrular. Eski regresyonların hata metni sözleşmesi korundu.
- `b8d8d6f5`: 4.955 değişmez tarihî baseline + iki ayrı geçerli URL ile AES-GCM arşiv kurup, bir URL'nin aday görünümünden silinmesini reddeden test eklendi.
- Yeni commit'ler için GitHub Actions sonucu henüz doğrulanmadı; #11/#13/#14/#16 kapanmadı, 8/33. Gerçek S3 ve AV kabul kanıtı gerekliliği sürüyor. Main, PR #9, ana İBO, tarihî envanter değiştirilmedi.

## 9 Kasım — #11/#14 eski kaynak alanları provenans denetimi

- `95abdf31`: şifreli deduplikasyon adayındaki `source_ids` kümesinin ham SHA kaynak geçmişine eşit olması yanında eski `source`/`source_id` alanları da `source_ids(candidate)` üzerinden aynı kümeye bağlandı. Doğru `source_ids` yanında sahte eski kaynak etiketi artık reddedilir.
- `7cb641b4`: hem `source` hem `source_id` sahteciliği için ayrı AES-GCM arşiv regresyonu eklendi; gerçek 4.955 hash-only tarihî baseline dosyası değiştirilmedi.
- Master Engine push offline kabul adımı bu regresyonu kapsar; bu commit'lerin yeni Actions run ID/sonuçları API ile doğrulanmadı. #11/#13/#14/#16 açık, kapanan 0, 8/33. Gerçek uzak S3 ve AV kanıtı olmadan tamamlandı yazılmadı. Main, PR #9 ve ana İBO korunuyor.

## 9 Kasım — #11 hash-only kaynak geçmişi regresyonu

- `b2022f98`: 4.955 tarihî baseline korunarak aynı URL SHA'sına bağlı yeni hash-only kaynak satırı ve gerçek URL satırı birlikte arşivlenir. Deduplike adaydan hash-only kaynak etiketi çıkarıldığında `archive_acceptance_gate.check` reddetmeli; test eklendi.
- V2 Master Engine geliştirme dalı push tetikleyicisi ve #11/#13/#14/#16 toplu offline kabul adımı mevcut. GitHub connector'ün commit-run sorgusu push çalışmaları için sonuç sağlamıyor; yeni run ID veya başarılı test sonucu henüz doğrulanmadı.
- Görev kapanışı yok (8/33); #13 gerçek versioned S3 geri yükleme kanıtı, #14 bağımlılığı ve #16 gerçek geçici hata uçtan uca kanıtı açık. main/PR #9/ana İBO/tarihî baseline korunuyor.

## 9 Kasım — V2 BİTİR: toplu kabul iş akışı tetikleme düzeltmesi

- `89b46d90`: `.github/workflows/v2-master-engine.yml` geliştirme dalındaki her push'ta `test_archive_acceptance_gate`, `test_historical_inventory_guard`, `test_independent_s3_restore`, `test_traz_transient_av_recovery` modüllerini ayrı fail-closed adımda çalıştırır. `v2/reports/master-ci/acceptance-11-13-14-16.log` başarısızlıkta bile artifact'a dahil edilir.
- Eski başarısız run #42672120731 jobs/artifacts API ile boş dönüyor; ona takılmadan yeni push tetiklemesi uygulandı. Yeni run ID, job sonucu ve log henüz GitHub API ile doğrulanamadı. Testleri geçmeden #11/#13/#14/#16 kapatılmayacak. Özellikle gerçek bağımsız S3 restore ve uçtan uca transient AV kabulü, sentetik regresyondan ayrı kanıt gerektirir.
- Kapatılan görev 0, mevcut 8/33. Main, PR #9, ana İBO listesi, tarihî envanter değiştirilmedi.

## 9 Kasım — V2 BİTİR: #11/#14 eksik kaynak geçmişi kaybını engelleme

- GitHub Actions #42672120731 için jobs ve artifacts API sorguları boş döndü; test hata loguna erişilemedi. Bu çalışmanın başarı veya kök hata nedeni doğrulanmadı. Link: https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42672120731
- `1ed59a14`: şifreli aday görünümünde kaynak etiketlerinin yalnızca ham URL geçmişinin alt kümesi olması artık yeterli değil; aynı SHA kimliğine ait tüm kaynak geçmişinin eksiksiz korunması zorunlu. Sahte etiketler kadar eksik etiketler de reddedilir.
- `1b5acb42`: kaynak etiketi tamamen silinmiş aday için regresyon eklendi; mevcut uydurma/tekrarlı kaynak durumları da korunuyor.
- Yeni commit'ler için gerçek CI sonucu doğrulanmadı. #11/#13/#14/#16 kapatılmadı; bağımsız S3 geri yükleme ve uçtan uca geçici hata kabulü bekliyor. 8/33; main, PR #9, korumalı İBO ve tarihî baseline değiştirilmedi.

## 9 Kasım — #11/#14 şifreli aday kaynak etiketlerini ham URL kimliğine bağlama

- `32bad600`: `archive_acceptance_gate.check` her deduplikasyon adayının `source_ids` etiketlerini tam URL SHA kimliğine ait ham arşiv kayıtlarının `source_ids/source_id/source` birleşimiyle doğrular. Aynı hash'e ait hash-only tarihî kaynaklar da hesaba katılır. Uydurma, tekrarlı veya geçersiz kaynak etiketi reddedilir.
- `a8b9ec78`, `61fdfee7`: gerçek 4.955 tarihî referans ve AES-GCM arşiv ile uydurma/karışık/tekrarlı kaynak etiketlerinin reddini doğrulayan regresyon; her alt durum için benzersiz geçici arşiv yolu düzeltmesi.
- Bu yeni commit'ler için GitHub Actions test sonucu henüz doğrulanmadı; görev kapatma yok, 8/33. #13 bağımsız uzak S3 geri yükleme ve #14 tam kabul açık. main/PR #9/korumalı İBO değiştirilmedi.

## 9 Kasım — #14 sahte cihaz/İBO kabulü reddi

- `264a6fc1`: `archive_acceptance_gate.check`, şifreli deduplikasyon aday görünümündeki `device_verified` ve `ibo_device_verified` alanlarının da açıkça `False` olmasını zorunlu kılar. Geçerli AES-GCM manifesti ve ham URL provenansı, cihaz/İBO AV kabulü yerine geçmez.
- `c09bd39c`: her iki bayrağı ayrı ayrı `True` yaparak 4.955 gerçek tarihî referansla oluşturulan şifreli arşivin reddi regresyonu eklendi.
- GitHub Actions'ın bu iki yeni commit'e ait offline test sonucu doğrulanmadı; classic commit status boşluğu Actions başarı/başarısızlık kanıtı değildir. #13 uzak S3 geri yükleme ve #14 kabulü açık; 8/33. main, PR #9 ve korumalı İBO değişmedi.

## 9 Kasım — #14 hash-only adayın gerçek URL sayılmasını önleme

- `7f6dad5b`: `archive_acceptance_gate.check` şifreli aday görünümündeki her kayıtta `validate_url(row.get("url"))` şartını zorunlu kılar. Ham arşivde aynı SHA'ya ait URL olsa bile adayın kendisi URL'sizse kabul edilmez.
- `f20847b4`: 4.955 gerçek baseline, gerçek yeni ham URL, eşleşen `url_sha256`, fakat URL'si kaldırılmış şifreli aday görünümünün reddi için regresyon eklendi.
- `v2-master-engine.yml` geliştirme dalındaki her push için `offline-tests` job'unu tanımlar; bu turda yeni commit'in Actions run/job sonucu doğrulanamadı. Classic combined commit status sorguları boş; bu başarı veya başarısızlık kanıtı değildir. Gerçek uzak S3 restore #13 ve #14 kabulü açık, 8/33. main, PR #9 ve korumalı İBO değiştirilmedi.

## 9 Kasım — #14 şifreli aday görünümünde sahte yeni AV reddi

- `0d28d3f9`: `archive_acceptance_gate.check` aday görünümündeki `status=NOT_REVERIFIED`, `av_verified/decoded/video/audio/spoken_language_verified=False` koşullarını zorunlu kılar. Geçerli AES-GCM manifesti ve gerçek ham URL provenansı olsa bile sahte yeni AV bayrakları reddedilir; tarihî kanıt silinmez.
- `be7b8c54`: gerçek 4.955 hash-only referansla, geçerli ham URL ve şifreli manifest üzerinden `av_verified=True` sahteciliğinin reddini test eden regresyon eklendi.
- Yeni kod/test commit'leri henüz Actions ile doğrulanmadı. #13 gerçek bağımsız S3 restore, #14 bütün kabul ve #16 uçtan uca geçici hata kabulü açık; 8/33. main, PR #9 ve korumalı İBO listesi değiştirilmedi.

## 9 Kasım — #14 şifreli aday görünümü için ham URL provenans zorunluluğu

- `3bf50997`: `archive_acceptance_gate.check`, AES-GCM manifesti ve 4.955 baseline doğrulandıktan sonra her adayın exact URL SHA kimliğinin `historical + newer` ham kayıtlardaki gerçek, geçerli URL kimliğinden gelmesini zorunlu kılar; adayda kimlik yoksa, tekrar varsa veya ham URL'de karşılığı yoksa reddeder.
- `6ded27c0`: gerçek 4.955 referans kaydı ve geçerli şifreli manifestle üretilmiş ancak ham kayıtlarda olmayan sentetik aday URL'sini içeren arşivin reddini doğrulayan regresyon eklendi.
- Geliştirme dalına commit edildi. Yeni commit'lerin CI sonucu henüz doğrulanmadı; #13 bağımsız S3 restore kabulü ve #14 kapanmadı. **8/33**; main, PR #9, korumalı İBO değiştirilmedi.

## 9 Kasım — #13/#14 immutable 4.955 tarihî referans dosyasının tam içerik sabitlemesi

- `48476187`: `archive_acceptance_gate.py` artık `v2/history/stage3-4955-hash-only.jsonl` dosyasının tam Git blob SHA1'ini (`c91c94a3f19097dec2855105da26d8b9a8329f8b`) doğruluyor; yalnızca 4.955 URL SHA kimliği toplamı yeterli değil. Referans dosyasındaki kaynak/metadata değiştirilirse şifreli geri yükleme kabulü fail-closed.
- `dd66114d`: URL SHA kimlikleri korunurken ilk tarihî referans kaydının metadata'sı değiştirildiğinde kabulün reddini doğrulayan regresyon eklendi.
- Source Integration Batch `42606783037` 12/12 job success ve güncel AV kanıtları önceki notta; bu yeni commit'lerin CI sonucu henüz doğrulanmadı. Gerçek bağımsız S3 restore kabulü için özel yetki ve sırlar gerekiyor; #13/#14 açık, 8/33. main/PR #9/ana IBO değiştirilmedi.

## 9 Kasım — Source Integration Batch #42606783037 tamamlandı; güncel gerçek AV artefaktı okundu

- GitHub Actions `42606783037`: **12/12 job completed/success** (kaynak adapter regresyonu, FFmpeg HLS, geçici hata yeniden denemesi, TR/AZ kaynak ve EPG araması dahil). `42609830543` için job listesi boş döndü; bu run'ın başarısı doğrulanmış sayılmaz.
- `v2-grouped-av-evidence-42606783037` (artifact `13677038022`) ZIP indirildi; `final-worldwide-acceptance.json` ve `historical-worldwide-av-crosswalk.json` doğrudan okundu.
- 35.934 aday, 35.934 probed, 0 unprobed, 14.495 toplam decoded AV. Bunların `evidence_origin` ile tek tek sayımında **86 CURRENT_RUN_FFPROBE_FFMPEG decoded**, **14.409 PRIOR_RUN_HASH_ONLY_NOT_FRESH decoded**; 14.495'i yeni canlı yayın olarak sayma.
- Tarihî 4.955 kimlik korunmuş; 4.890 exact SHA eşleşmesi; **3.046** eşleşmede AV; **1.844** eşleşmede AV yok; **65** dünya raporunda yok. `historical_broadcaster_identity_verified=false`, `ibo_device_verified=false`, `readiness=REVIEW_REQUIRED`. Önceki #42539900333 raporuna göre 62→86 current-run decoded ve 3.042→3.046 tarihî matched AV; farklı run'lar arasında yeni tekil kanal farkı doğrulanmadı.
- #9/#11/#13/#14/#16 bağımlılıkları açık; #13 gerçek sürümlü uzak S3 restore + gizli anahtar gerektiriyor. **8/33** değişmedi. main, PR #9 ve ana İBO listesine dokunulmadı.

## 9 Kasım — #14 şifreli arşivde ham tarihî kanıt zorunluluğu

- `454859d`: `_verify_archive_envelope` artık geçerli blok sayısı ve payload SHA256 manifesti bulunsa bile **ham tarihî kayıt bulunmayan** view-only arşivi reddeder; eski tarihî veriyi geri yükleme kabulü olmadan kaybolmuş saymaz.
- `0898eb1`: tam tutarlı manifest ve SHA256 ile oluşturulmuş ama `raw_record_count=0` olan sentetik view-only arşivin reddini doğrulayan regresyon eklendi.
- Değişiklikler geliştirme dalındadır; Actions sonucu henüz doğrulanmadı. #14 ve bağımlı #13 gerçek şifreli uzak restore kabulü açık; 8/33. main, PR #9 ve ana IBO listesi değiştirilmedi.

## 9 Kasım — #11/#14 hash-only tarihî TR kanıtı ile yeni AZ URL çelişkisi

- `b6a52099`: aynı gerçek URL'nin tarihî TR ve yeni AZ kaynaklarında çelişmesi halinde kaynak kimlikleri korunurken `UNKNOWN/CONFLICTING_TR_AZ_EVIDENCE` ve `NOT_REVERIFIED` bekleyen regresyon eklendi.
- `abc05b67`: tarihî **yalnız SHA256** TR kimliğiyle eşleşen yeni AZ URL'si için ayrı regresyon eklendi. Ham tarihî kayıt korunur, SHA eşleşmesi ve iki kaynak provenansı tutulur; yeni aday AV/decoded/video/audio bayrakları false kalır.
- Bunlar yeni kod testleridir; GitHub Actions'ın bu commit'lerde başarılı çalıştığı henüz kanıtlanmadı. #11/#14/#16 açık, 8/33. Ana IBO, main ve PR #9 değiştirilmedi.

## 9 Kasım — AV kanıtı tazeliği: 14.417 toplam, yalnızca 62 bu koşuda yeni

- `42539900333` / `v2-grouped-av-evidence` artefaktındaki `final-worldwide-acceptance.json` içindeki **35.542 adayın tamamının** `evidence_origin` ve `decoded/video/audio` alanları tek tek sayıldı: `CURRENT_RUN_FFPROBE_FFMPEG` 21.187 kayıt, `PRIOR_RUN_HASH_ONLY_NOT_FRESH` 14.355 kayıt.
- 14.417 `VIDEO_AUDIO_DECODED` kaydının **62'si bu koşudaki FFprobe/FFmpeg**, **14.355'i eski koşudan hash-only korunmuş kanıt**. Önceki notta geçen 14.417, yeni canlı doğrulama sayısı olarak yorumlanmamalıdır; toplam birleştirilmiş AV sayısıdır.
- Bu ayrım #14/#16 için kritik: tarihî AV kanıtı saklanır fakat yeni AV kabulüne terfi ettirilmez. 4.890 tarihî SHA eşleşmesi / 3.042 tarihî decoded AV, otomatik olarak 3.042 yeni prob veya İBO oynatma kabulü değildir. #11/#14/#16 açık, 8/33 değişmedi.

## 9 Kasım — Gerçek Actions artefaktı ile tarihî SHA/AV çapraz kontrolü

- GitHub Actions run `42539900333` içindeki `v2-grouped-av-evidence-42539900333` ZIP artefaktı indirildi; `final-worldwide-acceptance.json` ve `historical-worldwide-av-crosswalk.json` açılıp okundu. Artefakt SHA256: `6981e10e090417ec83dfeff0d0d3da3a7dbcd95fe4437f2aa56c13742fe85e39`; run head: `15da708c003e49dde49bfce7b68310ad77cf2302`.
- Gerçek tarama raporu: 35.542 adayın 35.542'si probe edildi, 14.417'sinde görüntü+ses çözümlendi; 0 unprobed; `readiness=REVIEW_REQUIRED`, `ibo_player_verified=false`, `spoken_language_verified=0`. İBO kabulü değildir.
- Tarihî hash-only çapraz kontrol: 4.955 kimlik korunmuş; 4.890 exact URL SHA eşleşmiş; 3.042 eşleşmede decoded AV; 1.848 eşleşmede AV kanıtı yok; 65 tarihî kimlik dünya raporunda yok. `historical_broadcaster_identity_verified=false`, `ibo_device_verified=false`. Rapor gerçek tarihî veriyi kapsar, ancak #14 uzak arşiv restore/metadata multiset kabulünü **tek başına kanıtlamaz**.
- #11/#14/#16 açık kalır; #13 gerçek şifreli uzak yedek restore ve #9 resmî kaynak provenans kabulü eksiktir. Yeni AV kanıtı icat edilmedi, ana IBO/main/PR #9 değiştirilmedi. Son commit CI'si ayrıca doğrulanmalı.

## 9 Kasım — #11/#14 tarihî AV durum metnini yeni kanıt gibi taşımama

- `d2ed4223` 5 offline workflow **completed/success**; `dfb42523` Master Engine, Eight-Stage ve Actions Monitor **completed/success**. Bunlar gerçek canlı AV veya IBO cihaz kabulü değildir.
- `8f92147c`: ham tarihî `status=VIDEO_AUDIO_DECODED` değeri şifreli arşivde değiştirilmeden korunur, ancak yeni tekilleştirilmiş adayın `status` değeri `NOT_REVERIFIED` yapılır; önceki decoded/video/audio/AV/IBO bayrakları false kalır. `84951b41`: hem tarihî durumun korunmasını hem aday durumunun güvenliğini doğrulayan regresyon.
- Son test commit'i için CI **henüz doğrulanmadı**. #11/#14/#16 ve bağımlılıkları açık, 8/33. main, PR #9, ana IBO ve tarihî envanter değişmedi.

## 9 Kasım — #11/#14 aday görünümünde eski AV kanıtının taşınması engellendi

- `a7989ba5`: tarihî ham kayıtların `decoded/video/audio/av_verified/device_verified/ibo_device_verified` bayrakları arşivde aynen korunur; **yeni tarama yapılmadan** tekilleştirilmiş URL aday görünümünde bu bayrakların tamamı `False` yapılır. Kaynak geçmişi kaybolmaz.
- `d2ed4223`: hem tarihî hem yeni kaynakta eski AV/IBO bayrakları `True` olsa bile ham kayıtların tam korunması ve aday görünümde sahte AV oluşmaması regresyonu. Push sonrası Actions **pending/queued**, başarı ilan edilmedi.
- #11/#14/#16 in_progress, #9 ve #13 kabul bağımlılıkları açık. Toplam 8/33. main, PR #9, IBO ve tarihî envanter değiştirilmedi.

## 9 Kasım — #16 FFmpeg başarısız probunda çelişkili AV bayrakları reddi

- `baf6f5a3` ve `1d4dc57f` Master Engine offline ve Eight-Stage **success**; önceki explicit-null proof CI hatası çözüldü.
- `3fb6dd47`: FFmpeg sonucu `decoded=False` iken `video=True` veya `audio=True` içerirse `aggregate` artık `ValueError` verir; kaynak başarısızlığı AV kanıtına dönüşmez. `b24c9414`: üç çelişkili bayrak kombinasyonu için regresyon. Son test commit'inin Actions sonucu henüz doğrulanmadı.
- Source Integration Batch koşuları `pending/cancelled` görüldü; bu **başarı değildir**. #9 resmî kaynak kanıtı, #13 gerçek özel S3 geri yükleme, #14 gerçek 4.955 arşiv kabulü ve #16 gerçek kesinti kabulü hâlâ açık. #11/#14/#16 tamamlanmadı, toplam 8/33.

## 9 Kasım — #16 FFmpeg null proof CI hatası düzeltildi

- `25f45bff` Master Engine ve Eight-Stage **failure**: `test_malformed_live_probe_is_rejected_before_claiming_av` explicit `{sha: None}` verildiğinde ValueError bekliyordu; `aggregate` yanlışlıkla `p is None` üzerinden bunu bulunamayan kaynak gibi sayıyordu.
- `baf6f5a3` ile `if h not in proofs` kontrolü eklendi; gerçek eksik kaynak ile mevcut ama bozuk FFmpeg kanıtı ayrıldı. Sahte başarı üretilmedi. **Yeni commit için Actions henüz doğrulanmadı**; önceki kırmızı koşular yeşil kabul edilmedi.
- #11/#14/#16 in_progress; #13 gerçek özel S3 restore ve #9 resmî kaynak kanıtı hâlâ engel. Sonraki adım `baf6f5a3` grouped Actions sonucunu alıp #15/#18/#19 bağımlılıklarına ilerlemek.

## 9 Kasım — #16 gerçek kesinti sırasında önceki AV kimlikleri korunuyor

- `22f7fab7`: `aggregate` raporuna `original_av_channel_ids_preserved` eklendi; geçici DNS/HTTP/timeout nedeniyle **hiçbir yeni kaynak bulunmasa bile** önceki gerçek AV kanıtlı kanal kimlikleri açıkça raporda tutulur. Malformed FFmpeg proof (`None`) kabul edilmez. `9c136f72` regresyonları hem tam kaynak kesintisini hem malformed probe reddini test eder.
- Önceki `a8b379af` 4.955 satırlık AES roundtrip regresyonu Master Engine, Eight-Stage, Sıralı Hazırlık, Scanner Offline ve Actions Monitor workflow'larında başarılı. `9c136f72` son commit Actions kabulü henüz görülmedi. **#16 in_progress**; canlı/gerçek tarihî kabul yok. #11/#14 de açık; #15/#18/#19 bağımlılıkları devam ediyor.

## 9 Kasım — #14 tam 4.955 satırlık şifreli roundtrip kabul testi

- `a8b379af`: `v2/test_historical_inventory_guard.py` artık **4.955 sentetik tarihî kayıt + yeni kaynak** için AES arşiv yazma/geri okuma, aynı SHA'lı üç farklı kaynak ve farklı önceki AV/hata durumu, tam ham metadata korunması, aday görünümde tekilleştirme, AV/IBO doğrulaması uydurulmaması ve tam baseline çoklu-küme eşitliğini birlikte test ediyor. Bu gerçek tarihî dosyanın yerini tutmaz.
- Push ile beş offline Actions tetiklendi (ilk gözlem queued). Sonuçlar görülmeden #14 veya bağımlı #16 completed sayılmayacak. #11/#14/#16 in_progress; #15/#18/#19 bekliyor. Kaynak envanteri, ana IBO, main ve PR #9 değişmedi.

## 9 Kasım — Son yeşil CI ve #11/#14/#16 görev durumu

- `81f53be7` commit'inde **beş** temel workflow `completed/success`: Master Engine **offline-tests** (live master skipped), Eight-Stage, Sıralı Hazırlık, Current Scanner Offline, Actions Monitor. Kaynak entegrasyonu uzun işi `27335019` için son gözlemde `in_progress` idi; başarılı kabul edilmedi.
- `v2/tasks/state.json` #11/#14/#16 artık **in_progress** ve ilgili kanıt bağlantıları, bağımlılıklar, gerçek engeller kayıtlı (commit `d5fee039`). **Hiçbiri completed değil.** #11: #9 resmî kaynak keşfi; #14: #13 bağımsız şifreli arşiv geri yükleme ve gerçek 4.955 kayıt kanıtı; #16: #14 ve gerçek geçici yayın hatası kabulü. Sonraki sıralama #15→#18→#19.
- Daha önceki `14fbb8c0` test hatası `94acf4bb` ve `81f53be7` ile düzeltildi; son başarılı iş akışları bu düzeltmeyi doğruladı. **Yeşil offline test gerçek canlı AV veya IBO cihaz kanıtı değildir.**

## 9 Kasım — V2 DEVAM #14 gerçek çoklu tarihî kimlik regresyonu

- #14 `verify_historical_baseline` artık aynı URL SHA'ya ait birden fazla tarihî kaydı tek sözlük girdisine indirgemez; **tam kayıt çoklu kümesini** ve bütün kaynak/durum metadatasını doğrular. Aynı hash'e sahip farklı geçmiş satırları kabul edilir; satır silinmesi, değiştirilmesi veya yeni sahte AV durumu reddedilir. Kod commit `1fe5c6b6`, 4.955 satırlık tekrar/metadata regresyonu `ddfb14eb`.
- Önceki `27335019` commit'inde Master Engine offline, Eight-Stage, Ordered Preflight, Scanner Offline ve Actions Monitor completed/success; Master Engine **live master skipped**. Source Integration Batch son gözlemde in_progress; bu başarı diye sayılmadı.
- `ddfb14eb` için toplu Actions henüz queued/pending. **#11/#14/#16 kapatılmadı**; #14 gerçek arşiv/baseline kabulü ve #11'in #9 bağımlılığı hâlâ açık. #15/#18/#19 sıralı bağımlılıkları bekliyor.

## 9 Kasım — Toplu #11/#14/#16 çalışma devri (kabul bekliyor)

- Kullanıcı emri: #11, #14, #16 topluca; kabulden sonra #15/#18/#19. Bu turda **hiçbiri completed yapılmadı**; bağımlılıklar ve gerçek 4.955 baseline/remote S3 kabul kanıtı ayrı doğrulanmalı.
- #11: `v2/historical_inventory_guard.py` deduplicated view içindeki kaynaklardan taşınan `av_verified` bayrağını zorunlu false yapar; ham tarihî ve yeni kayıtlar şifreli arşiv için aynen korunur. Test: aynı URL'nin iki yeni kaynağı ve tarihî SHA-only kaynak geçmişi kaybolmaz, AV/cihaz kanıtı uydurulmaz. Commit'ler `cd231eb8`, `c7847d09`, `807f608e`.
- #16: `v2/traz_transient_av_recovery.py` yeniden deneme çıktısında tam URL SHA256 eşleşmesini, kaynak hedef kümesini ve kanal kimliğini kontrol eder; başka kanala ait AV kanıtını kabul etmez. Regresyon `3cffeb32`; kod `a5ff82a5`. Önceki başarı kimlikleri geçici bağlantı hatasında korunur.
- #14: Tarihî kimliklerin şifreli arşiv roundtrip ve başarısızlık yolu testleri mevcut; **gerçek 4.955 kayıtla güncel kabul kanıtı olmadan kapatılmayacak**. #11, #14 ve #16'nın son commit CI iş/job sonuçları doğrulanmalı. Ana IBO, main, PR #9 ve tarihî envanter değiştirilmedi.

## 9 Kasım — Tarihî kurtarma zorunluluğu kaldırıldı; beşli CI doğrulandı

- Kullanıcı kararı uygulandı: `v2/tasks/master_tasks.json` görev #3/#4/#6 için `deferred_optional` kapsamını tanımlar; bu görevlerin kanıtları ve 4.955 tarihî kimlik korunur, **completed** sahte biçimde verilmez. Diğer görevlerin bu üç kayda olan bağımlılıkları çıkarıldı. `v2/tasks/task_engine.py` zorunlu seçimde bunları atlar; #34 kapısında ertelenenleri zorunlu tamamlanma olarak saymaz. Kod/test commit'leri `4997184917073de17ec3332779d592b5e4afe837`, `9b908eea3a44c0f006cfdd637ce2345697b232da`, `4dc213d1aa244f074feb707e17cdb4db57418f06`.
- Aynı son commit `4dc213d1` için beş GitHub Actions workflow'u **completed/success**: Master Engine #42610015411, Eight-Stage #42610015533, Ordered Preflight #42610015392, Actions Monitor #42610015523, Actions Trigger & Protected Playlist Gate #42610015394. Bunlar CI kod/güvenlik doğrulamasıdır; canlı AV veya IBO cihaz testi değildir.
- `5cce6da32dc6c2b3bdebf92d11824bbe5a5a355f` ile Source Integration Batch push.paths'den `v2/tasks/**` kaldırıldı. Workflow dosyasının kendisinin değişmesi nedeniyle eski başlatılmış ağır tarama ve bir kuyruk işi hâlâ ayrıca kontrol edilmeli; sırf görev dosyası değişikliği yeni ağır tarama tetiklemez.
- **Yeni aktif odak:** #9 resmî yayıncı/canlı TV kaynağında gerçek provenance ve AV ayrımı; #11 URL hash tekrarları ve kaynak geçmişi. #11, #9 kabul edilene kadar tamamlandı denmez. #5'in üç özgün bozuk satır engeli ayrıca açık kalır. #13 S3 gerçek restore ve #23 gerçek live master kanıtı olmadan kapatılmaz. Ana IBO, main, PR #9 korunur.
- 33 numaralı kayıt şimdilik denetim/izlenebilirlik için saklanır; üçü kullanıcı kararıyla isteğe bağlıdır. **Zorunlu kapsam 30 görevdir.** #34 için zorunlu 30'un kabulü ve #32 kullanıcı cihaz testi gerekir; mevcut geçmiş notlardaki '33/33 zorunlu' ifadeleri bu karar ışığında güncel değildir.

---

## 9 Kasım — KULLANICI KARARI: tarihî kurtarma taramalarını zorunlu bitiş kapsamından çıkar (UYGULAMA BEKLİYOR)

Kullanıcı, tarihî kanal/kaynakların tek tek yeniden bulunmasını ana V2 tamamlanmasının ön şartı olmaktan çıkarmayı açıkça istedi. Bu karar #3 (45/50 özel kimlik), #4 (4.955 tarihî kimliğin eksik AV araştırması) ve #6 (2.643 kayıp adresin yeniden AV taraması) için geçerlidir. Tarihî envanter, şifreli adaylar ve mevcut AV kanıtları **silinmez**; kanıtsız yayınlar çalışıyor sayılmaz. Genel kanal keşfi, yeni kaynakların gerçek AV doğrulaması, güvenlik, IBO koruması ve kullanıcı cihaz testi devam eder.

**ÖNEMLİ:** Henüz kanonik 33 görev manifesti/ledger'ı değiştirilmedi; #3/#4/#6 otomatik olarak completed sayılmadı. Bu üç görevi çıkarma/defer etme uygulaması, bağımlılıkları (#17 ve ardılları), 33→34 kapısını ve testleri birlikte güvenli biçimde yeniden düzenlemeyi gerektiriyor. Mevcut uzun Source Integration Batch #42606783037 sürerken ağır AV tetikleyen `v2/tasks/**` dosyalarına yeni yazma yapılmamalı. Önce bu workflow'un görev defteri değişikliklerinde gereksiz tarama başlatması önlenmeli; sonra tek toplu commit ve regresyon testleriyle karar uygulanmalı. #34 geniş TR/dünya kanal keşfi unutulmayacak; erken başlatma kapısı da yeni kapsamla uyumlu biçimde güncellenmeli.

---

## 9 Kasım — #13 bağımsız S3 geri yükleme güvenliği, kanıt sınırı

- Dev commit `4f5d2685a6685dc429e59a1ca7c69068b73b3c6f`: `v2/independent_s3_restore.py` artık S3 nesne sürüm kimliğindeki DEL (ASCII 127) kontrol karakterini ağ isteğinden önce reddeder.
- Dev commit `897de2a34fccdbe744fe787fa74c3eb7f13b531d`: `v2/test_independent_s3_restore.py` için S3'ü hiç çağırmama regresyonu eklendi.
- Aynı ikinci SHA üzerinde gerçek Actions: Eight-Stage #42539429702 (2/2 success), Current Scanner #42539429699 (2/2 success), Actions Monitor #42539429671 (success), Master Engine #42539429747 (offline-tests success; live master skipped), Ordered Preflight #42539429620 (compile/protect/discovery-tests/safety success; read-only live audit skipped). Bu sonuçlar **offline güvenlik kabulüdür**, gerçek AWS S3 sürüm geri yükleme kanıtı değildir; #13 açık kalır.
- Paralel uzun Source Integration Batch #42530626269 son gözlemde 11/12 success, bir canlı AV rapor job'u in_progress. Onunla yarışan ikinci ağır tarama başlatılmadı. Main, PR #9, IBO listesi ve 4.955 tarihî kayıt değiştirilmedi.

---

## Görev yürütücüsü için üç doğrulama/düzeltme (33 görev kapsamında, AÇIK)

Bu üç madde **34. görev değildir**; mevcut 33 görevin görev yönetimi/otomasyon güvenilirliği kapsamındaki açık teknik eksikleridir. Kodda ve gerçek GitHub Actions çalışma kanıtlarında doğrulanmadan tamamlandı denmez:

1. **Her çalışma başında okuma:** Otomasyonun gerçekten `DEVAM_NOTU.md`, `v2/tasks/master_tasks.json` ve `v2/tasks/state.json` dosyalarını dev dalındaki güncel commit'ten okuduğunu, başlangıç logları ve testlerle doğrula; eksikse uygulayıp topluca test et.
2. **Kanıtlı durum güncellemesi:** İş sonunda gerçek run/job sonuçları, commit SHA, AV/cihaz kanıtı ayrımı, hata ve engel gerekçesiyle kanonik `state.json` güncellenmeli; devam notu büyük değişikliklerde senkronize edilmeli. `completed` kanıtsız verilmemeli; tamamlanan işler yeniden açılmamalı. Çakışan saatlik çalışmalara karşı tek-yazıcı/eşzamanlılık koruması olmalı.
3. **33→34 kapısı:** Yalnızca kanonik 33 görevin hepsi kabul kanıtıyla `completed` olduktan sonra https://github.com/Madsc55/MADSC55-TV-V2/issues/10 için açık onaylı/uygun sıraya alma ve otomatik başlatma koşulu uygulanmalı; erken başlamama, tekrarlı başlamama ve cihaz testi kullanıcıya ait olma kuralları doğrulanmalı.

**Durum:** Bu maddeler yapılacak/doğrulanacak işlerdir; uygulanmış veya test edilmiş sayılmaz. Yalnız V2 dev dalı; main, PR #9 ve korunan IBO listesi değişmez.

---

## 33 görevden sonra — #34 Türkiye M3U/M3U8 geniş kapsamlı keşif (BEKLEMEDE)

**Kalıcı iş kaydı:** https://github.com/Madsc55/MADSC55-TV-V2/issues/10
**Başlatma şartı:** Kanonik 33 görev tamamlanmadan bu iş başlatılmaz; mevcut 33 görev ledger'ına eklenmez veya sıra değiştirilmez. Şu an yalnızca yapılacak iş olarak kaydedilmiştir.

- Arama adları: `turkiye.m3u`, `tr.m3u8`, `tr.m3u`, `turkish-iptv`, `canli-tv`, `yerel-tv`, `iptv-turkiye`, `m3u tr`, `m3u8 tr`, `Türkiye IPTV`, `Turkish TV playlist` ve ilgili Türkçe/İngilizce varyasyonlar.
- Kaynak türleri: GitHub/Gist, GitLab, Codeberg, bağımsız açık IPTV/M3U dizinleri, Internet Archive, resmî yayıncılar, canlı TV web sayfaları; YouTube Live yalnız aday/kimlik araştırmasıdır, sayfa bağlantısı oynatılabilir M3U kabul edilmez.
- Özellikle araştırılacak örnekler: https://github.com/omerdenizhan/IPTV-M3U ; https://github.com/iptv-turk-tr/iptv/blob/main/list.m3u ; https://github.com/iptv-org/iptv/blob/master/streams/tr.m3u ; https://github.com/Free-TV/IPTV . Bunlar şu an **aday kaynaklardır**, doğrulanmış yeni V2 kaynakları veya çalışan kanallar değildir.
- Kaynak güvenliği, URL/kimlik tekrar ayıklama, tarihî provenance, gerçek FFmpeg video+audio kanıtı, TR/AZ sınıflandırma ve ayrı IBO test çıktısı şarttır. Tek tek değil toplu test; cihaz kabulü kullanıcıya aittir.
- **Koruma:** Yalnız V2 dev dalı; eski `madsc-tv`, `main`, PR #9, `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, cihaz favorileri ve sabit TRT 1/DHA sırası değiştirilmez.

---

## 7 Kasım — Gerçek Master Engine kabul koşusu talebi

#23 için yalnız offline yeşil workflow yeterli değildir. Bu dev commit mesajındaki `[run-live-master]` işareti, mevcut `V2 Master Engine` workflow'unun canlı `master` job'unu tetiklemek içindir. Job gerçek 500-aday keşif/doğrulama çalıştırır; kalıcı şifreleme anahtarı eksikse fail-closed durur. Run ID, job adımları ve çıktı kanıtı doğrulanmadan #23 kapatılmaz. Korunan IBO, main, PR #9 değiştirilmeyecektir.

## 7 Kasım — S3 regresyon hatası kapandı

`a00fac0b` commit'inde üç workflow'u kıran yanlış DEL test girdisi `d2bfb9299421cf8a690a7189b0ecd95f679913c2` ile düzeltildi. Aynı SHA üzerinde gerçek Actions job sonuçları: Eight-Stage `42395053358` (2/2 success), Master Engine `42395053334` (offline-tests success, koşullu master skipped), Ordered Preflight `42395053346` (compile/protect/discovery-tests/safety success, koşullu live audit skipped), Current Scanner `42395053399` (2/2 success), Actions Monitor `42395053377` (success). Gerçek S3 remote restore kanıtı yok; #13 açık. Canlı Master Engine kabulü yok; #23 açık. İlerleme 8/33. Korunan IBO, main ve PR #9 değiştirilmedi.

# MADSC55 TV V2 — TEK GİRİŞLİ KALICI DEVİR / CANLI GÖREV DEFTERİ

> **Yeni sohbet başlangıcı:** Yalnızca `Madsc55/MADSC55-TV-V2` deposunun `madsc/v2-discovery-bulk-20261031` dalındaki bu dosyayı, `v2/tasks/master_tasks.json`, `v2/tasks/state.json` ve GitHub'daki mevcut **[V2 SIRA]** issue kayıtlarını oku. Bu üst bölüm en güncel iş akışı özetidir; alttaki uzun kronoloji tarihîdir, güncel durum sayılmaz. Görevleri sıfırlama veya yeni görev seti oluşturma. Dosyayı büyük değişikliklerde tek güncellemede yenile.

## Yetki, güvenlik ve tekrar etmeme kuralları (7 Kasım 2026)

- **Yalnız dev dalına yaz:** Eski `madsc-tv`, `main`, PR #9, `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, cihaz favorileri, tarihî envanter ve saatlik otomasyon dokunulmaz. TRT 1 1440P QHD ve DHA CANLI 720P HD sabit ilk iki YEDEKLER girdisidir. PR #9 birleştirilmez.
- Gerçek FFmpeg video+audio kanıtı olmadan kanal çalışıyor sayılmaz; HTTP/manifest/EPG eşleşmesi AV değildir. IBO cihaz testini kullanıcı yapar. Prototip, mock yayın, sahte başarı ve yalnız yeşil test için kabul gevşetme yasak.
- **GitHub Actions gerçek kabul yolu (7 Kasım doğrulandı):** `mcp__GitHub__fetch` ile `https://api.github.com/repos/Madsc55/MADSC55-TV-V2/actions/runs` doğrudan okunabiliyor; `fetch_workflow_run_jobs` ve `fetch_workflow_job_logs` ile run/job kanıtları alınabiliyor. `fetch_commit_workflow_runs` PR odaklıdır; birleşik commit status yerine gerçek push run SHA/job/log kullan. Canlı master job yalnız `[run-live-master]` içeren push commit mesajında çalışır, sıradan push'ta `skipped` olması workflow tasarımıdır; gerekli canlı master kabulüyle karıştırma. Yeni workflow_dispatch başlatma aracı mevcut değil. Yetkili başka çalışma ortamı gerekirse bunu bir defa engel olarak kaydet; bağımsız geliştirmeye geç.
- **CI:** `v2-master-engine.yml` ve `v2-actions-monitor.yml` dev push için filtresiz; `v2-ordered-preflight.yml` dev push `v2/**` filtresiyle; `v2-source-integration-batch.yml` seçilmiş kaynak yolları ve artık `v2/master_engine.py`, `v2/test_master_engine.py`, `v2/tasks/**` için. `workflow_dispatch` bu dört workflow'da tanımlı. Güvenlik gereği canlı medya kurtarma bazı workflow'larda manuel-only kalır. GitHub Actions depo ayarlarının etkinliği / yeni run kesinliği kanıtlanmadı; kanıt olmadan tetikleyici değiştirme.

## Kanonik 33 görev (canlı ledger okuması)

- **7 completed, 4 in_progress, 1 blocked, 21 pending = 33.** Durum otoritesi `v2/tasks/state.json`; aşağıdaki tablo 7 Kasım okuma anının anlık görüntüsüdür, ileride değişirse ledger esas alınır. Evidence sayısı başarı kanıtının içeriğini otomatik doğrulamaz.

| # | Görev | Ledger durumu | Evidence URL adedi |
|---:|---|---|---:|
| 1 | Kaynak entegrasyonu AV taramasını sonuçlandır | completed | 2 |
| 2 | Son kod değişikliklerinin toplu testlerini doğrula | completed | 4 |
| 3 | Kurtarılamayan 45 kanal kimliğini araştır | in_progress | 2 |
| 4 | 4.955 tarihî kimlikte 1.886 AV kanıtsız ve 7 eşleşmeyen kaydı incele | in_progress | 2 |
| 5 | 3 bozuk kaynak satırını ve 17 dinamik kaynak boşluğunu onar | blocked | 2 |
| 6 | 2.643 kayıp yayın adresini toplu FFmpeg AV testinden geçir | pending | 0 |
| 7 | GitHub/Gist, GitLab ve Codeberg entegrasyonları | completed | 2 |
| 8 | Scribd, SlideShare ve Internet Archive kaynakları | completed | 1 |
| 9 | Resmî yayıncı ve canlı TV kaynakları | in_progress | 1 |
| 10 | IPTV-org TR/AZ eşleştirmeleri | completed | 1 |
| 11 | URL tekrarlarını ayıkla ve kaynak geçmişini koru | pending | 0 |
| 12 | Yayın hatalarını sınıflandır | completed | 1 |
| 13 | RSA arşiv bütünlüğü ve geri yükleme | pending | 0 |
| 14 | 4.955 tarihî kimliği koru | pending | 0 |
| 15 | SHA, URL ve yayıncı kimliği eşleştirmesi | pending | 0 |
| 16 | Geçici hatalarda geçmiş kanıtları koru | pending | 0 |
| 17 | Kurtarma kuyruklarını ve arşiv sonuçlarını tamamla | pending | 0 |
| 18 | TR/AZ kanal kimliklerini doğrula | pending | 0 |
| 19 | XMLTV/EPG eşleştirmelerini düzelt | pending | 0 |
| 20 | Gerçek yayın kalitesi etiketlerini doğrula | pending | 0 |
| 21 | Kategorileri düzenle | pending | 0 |
| 22 | TRT 1 ve DHA sabit sırasını koru | completed | 2 |
| 23 | Master Engine, Eight-Stage Runner ve Ordered Preflight entegrasyonu | pending | 0 |
| 24 | Otomatik keşif, kurtarma ve kanıt saklama kabulü | pending | 0 |
| 25 | Süre aşımı, tekrar deneme ve takılma kontrolleri | pending | 0 |
| 26 | Actions hata raporları ve güvenli yeniden deneme | pending | 0 |
| 27 | Merkezî state.json ile GitHub sonuçlarının tutarlılığı | in_progress | 2 |
| 28 | Doğrulanmış ibo_1000.m3u paketi | pending | 0 |
| 29 | Doğrulanmış ibo_2000.m3u paketi | pending | 0 |
| 30 | M3U, kategori ve tekrar kontrolleri | pending | 0 |
| 31 | Son toplu kabul testleri | pending | 0 |
| 32 | IBO Player cihaz testi — yalnızca kullanıcı | pending | 0 |
| 33 | Son arşiv ve tamamlanma raporu | pending | 0 |

- **#27 ek güvenlik:** `f4bc66db3ec1e1bb4e6e1f61ec896bf40413340e` Actions izleyicisine gerçek head_branch/event uygunluğu ve `acceptance_candidate` gözlem alanı ekledi; `ab9c5dee8619c0f05127b0499168714b5c17bee9` yanlış branch ve PR yeşil koşularının kabul sayılmamasını regresyonla güvenceye aldı. Bunlar yalnız kod/test eklemeleridir; yeni Actions toplu kabulü hâlâ bekliyor.

- **7 Kasım, Master Engine #816 offline-tests gerçek hata düzeltmesi:** Kullanıcının bildirdiği 18 testten 1 failure: `test_device_confirmation_cannot_attach_to_other_tasks` tamamlanmış görevde `Completed task cannot be silently reopened or downgraded` aldı, beklenen `only applies to task 32` idi. `v2/tasks/task_engine.py` içindeki `safe_transition` doğrulama sırası düzeltildi; tamamlanmış görev downgrade koruması aynen kaldı. Kod `be01ebae4aebc6e61c64b3d32a8d0a285eb6795a`, test `1b1a18f65b827804dd7981a5ed89bb263b477fab`. Yeni toplu Actions #816 sonrası run/job sonucu **henüz doğrulanmadı**; #27 açık. Workflow tetikleyicisi çalıştığı kullanıcı tarafından bildirildi; tekrar yetki/tetikleme araştırması yapma. Bağımsız geliştirmeye devam et.

- **7 Kasım, yeni Master Engine test düzeltmesi:** `v2/test_master_engine.py` içindeki iki AV fail-closed testinin M3U fixture'ında Python kaynak metnine çift kaçışlı `\\n` yazıldığı doğrulandı; M3U satırları ayrışmıyordu. `11181ef3c32e17288b03a95ee3abb888f6c2dbcb` ile kaynak literalinde doğru `\n` kullanıldı. Bu bir gerçek test-fixture hatası düzeltmesidir; güncel Actions run/job sonucuna erişilmediğinden #23/#27 kabulü **açık**. Kullanıcının bildirdiği #816 eski başarısız run yeni kodun kabulü değildir. Yeni sohbet, run ID olmadan başarı iddia etmesin; başka bağımsız göreve geçsin.

- **7 Kasım bağımsız CI regresyon onarımı:** `v2/test_actions_monitor.py` dosyasında testin kaynak kodunda gerçek Python sözdizimini bozan metinsel `\\n` bulundu; ayrıca başarısız job adımlarını denetleyen fixture yanlış workflow'a veri döndürüyordu. `e897fe89b6a73771df0f01d9c340efe307ada621` ile sözdizimi ve fixture routing düzeltildi. Bu kod GitHub'a yazıldı; **güncel run/job sonucu henüz doğrulanmadı**, #27 ve #23 açık. Eski #816 yeni kod kabulü değildir.

- **7 Kasım #13 S3 restore regresyon onarımı:** `v2/independent_s3_restore.py` boş anahtar ile hatalı biçimli anahtarı aynı hata mesajıyla reddediyordu; mevcut `test_missing_private_key_prevents_remote_request` ve `test_invalid_archive_key_is_rejected_before_remote_request` farklı hata mesajlarını beklediğinden offline test başarısız olabilirdi. `bab86a67e0bb73229077c2f120fafbe883757c79` ile boş anahtar `Missing private archive key`, biçimi bozuk anahtar `Invalid private archive key` mesajını üretir; her ikisi de S3 bağlantısından **önce** reddedilir. Gerçek S3 geri yükleme ve yeni toplu Actions kabulü hâlâ doğrulanmadı, #13 açık.

- **7 Kasım #27 güncel SHA kanıt sınırı:** `463fea97e4da580093d187c8d68144fcbe707285` Actions monitor'da `same_monitor_sha` şartı ekledi; geçmişte başarılı olmuş başka SHA'nın `acceptance_candidate` sayılması engellendi. `6bdff16123dcb125657d84ea06e65265c5978aa6` eski SHA reddi ve doğru SHA senaryolarını test ediyor. Gerçek güncel GitHub Actions run/job sonucu **bu turda doğrulanmadı**; bu iki commit için kabul yok. #27 açık, 7/33 değişmedi. Eski #816 sonucu yeni kod kanıtı değildir.

- **7 Kasım #27 workflow/job kabul sıkılaştırması:** `855dccb18107c3494af853aa853ff51b6cb0000b` ile `v2/actions_monitor.py` tamamlanan workflow'ların tüm job kayıtlarını `total_count` ile birlikte okur, boş/eksik/atlanan/başarısız job bulunan yeşil workflow'u kabul adayı saymaz. `18dd2916206ce88ac2192e139b1562049cfb75a9` regresyon fixture'larını ve eksik/skipped job testlerini günceller. Bu kod/test değişikliği **GitHub'a yazıldı**, ancak yeni push run ID ve gerçek job logu doğrulanmadığından #27 hâlâ açıktır; eski #816 kanıt değildir. `main`, PR #9, korunan IBO listesi, saatlik otomasyon değişmedi.

- **7 Kasım #27 mevcut testin gerçek kırılması düzeltildi (izleme özelliği eklenmedi):** `v2/test_actions_monitor.py` içindeki `test_all_grouped_workflows_are_queried` fixture'ı `observed.append(path)` ile hem dört workflow sorgusunu hem de sonradan eklenen job sorgularını sayıyordu. Bu nedenle `len(observed)==len(WORKFLOWS)` assertion'ı hatalıydı. `4f4f84c4f97df15cea2e1a238b49cfd93143828d` ile yalnız workflow sorguları sayılıyor; job sorguları testin kapsamına karıştırılmıyor. Güncel push Actions run ID/log erişimi olmadığından testin yeşile döndüğü **iddia edilmez**; #27 açık. Önceki #816 sonucu yeni kod kabulü değildir.

- **7 Kasım gerçek Actions loguyla S3 regresyon onarımı:** `42391180919` Master Engine offline-tests, `42391180885` Eight-Stage offline regressions, `42391155483` sıralı hazırlık discovery-tests job logları okundu. Üçünde de `test_invalid_archive_key_is_rejected_before_remote_request` alt testlerinde `"invalid private archive key"` / `"Invalid private archive key"` büyük harf uyuşmazlığı kaynaklı **4 failure** doğrulandı. `a9970a62476dc3a205af56c3b64e8ad03f40caae` ile gerçek hata mesajı test sözleşmesine uyarlandı. Aynı SHA'nın otomatik yeni Master Engine run'ı **42391495237** `completed/success`, `offline-tests` job **128459851205** `success`; `master` job **128459910987** `skipped` olduğundan bu run tüm işlerin çalıştığı anlamına gelmez. Eight-Stage **42391495647**, sıralı hazırlık **42391495267** en son kontrol anında tamamlanmamıştı. #27 ancak gereken tüm job'lar ve aynı SHA kabul şartları doğrulanınca kapatılacak; 7/33 korunur. GitHub API doğrudan `mcp__GitHub__fetch` ile `/repos/Madsc55/MADSC55-TV-V2/actions/runs` erişimi çalışıyor, eski 'run listesine erişim yok' notu artık geçersizdir. Yeni izleme özelliği ekleme; gerçek log ve kod hatalarını düzelt.

- **7 Kasım toplu Actions kanıtı (SHA `504fbb2b22e6fd79013a3c5d244f4ab034afbf3b`):** Eight-Stage `42391548121` **success**, iki job da success (FFmpeg guard `128460006214`, offline/protected `128460006345`); Master Engine `42391548120` **success**, offline-tests `128460006511` success, `master` `128460053518` **skipped** (workflow YAML'de `[run-live-master]` push mesajı şartı); Actions Monitor `42391548094` **success**, read-master-runs `128460006176` success. Önceki SHA `a9970a62` sıralı hazırlık `42391495267` **success**, compile/protect/discovery-tests/safety success, public-source audit skipped. Bunlar gerçek GitHub run/job sonuçlarıdır, ancak #27'nin **root `state.json` ile sonuç uzlaştırması + optimistic SHA concurrency + fail-closed** kabul kriterini tek başına tamamlamaz; #27 açık. `main`, PR #9, korunan listeye dokunma. 

- **7 Kasım #27 KAPANDI (8/33):** Aynı commit `90f195b010df2e1992b2d39bbdc43beb06ba9d98` için Master Engine `42391685418` offline-tests job success, Eight-Stage `42391685379` iki job success, Monitor `42391685458` job success. Master Engine'in `master` job'u yalnız `[run-live-master]` push'unda çalıştığından skipped; canlı tarama yapılmış sayılmıyor. `v2/tasks/test_task_engine.py` kapsamındaki canonical root/ledger bağları, same-SHA gerçek run sözleşmesi, stale root fail-closed, optimistic SHA conflict ve korunan yazma reddi offline regresyonları Master Engine toplu job'unda geçti. Bu kriterlere dayanarak `v2/tasks/state.json` #27 completed kaydı `75b5c2e933f2c71237f62431f314f8c3bff4a956` commit'iyle yazıldı. Bu state-only commit'in yeni Actions sonuçları ayrıca doğrulanmalı. Sıradaki bağımsız iş #13 gerçek RSA/AES arşiv offsite restore kabulü; gerçek S3 kanıtı olmadan kapatma. Korunan dosyalar değişmedi.

## En son değişiklikler ve bekleyen gerçek kabul

- **#9 kaynak entegrasyonu:** `727bf0c239fa7155c6ef4413fdaad88d6a7a9a55` kaynak workflow push path kapsamını genişletti; `7ff7f1e82d99f6f50abaade9eb9d6418ee0eba01` Master Engine regresyonlarını toplu kaynak testine ekledi. Kaynak uçtan uca canlı kabulü tamamlanmış sayılmaz.
- **#23 Master Engine:** `ece56e3b80d5e859ec45587e2d35371c713e32e2` decoder'ın truthy hata payload'ını AV saymasını engelledi; `902a7b7185839dcdd51282111bb8eddd2619aeaa` test ekledi. `600518d072165b39011baa02dac70802ed2f021b` HTTP kontrolünü explicit True yaptı; `4922f583ca5bcbdb2d5f447e5fbf787e90946b3f` regresyonu ekledi. Yeni commitler için toplu kabul henüz doğrulanmadı.
- **#13 bağımsız S3 restore:** `ba03465048f3a72fbdf70fa34a9c7ca206ca40d6` workflow preflight fail-closed; `f827bd404e1da3f61a0b805071e77286d25af8bd` gerçek indirmeden önce 64-hex key doğruluyor; `d7a57200ad5a652d3765c6113d578a3a91b623fe` regresyon. Gerçek versioned S3 download + AES-GCM + 4.955 tarihî kimlik roundtrip kanıtı bekliyor; **tamamlanmadı**.
- **#27 Actions kabulü:** `9b786eb81863bd7414871ce1ccfd6d0a91a70e42` izleyiciyi dört workflow'a genişletti; `7437256ab02a5fec5fc994f6acc8c1ff8e588049` regresyon. Gerçek güncel run/job logları ve kök state tutarlılık kabulü bekliyor. Önceki 4 workflow'luk düzeltme için yeni Actions sonucu iddia edilmez.
- **Doğrulanmış tarihî kanıt (yalnız ilgili eski SHA):** Actions [#42228674931](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42228674931) dünya AV: 34.209/34.209 tarama, 12.968 video+ses, 9 mühürlü paket; 4.955 tarihî kimlik, 4.948 exact SHA, 3.062 AV, 7 eksik SHA. Actions [#42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753) 17 modül / 190 offline test başarılı, canlı AV skipped. **Bunlar yeni commitlerin kabulü değildir.** 45 kurtarılmamış kanalın gerçek AV işi kullanıcı önceliğiyle en sona bırakıldı; hiçbir sahte kurtarma yok.
- **Sonraki bağımsız işler:** #13 gerçek restore önkoşulları ve hatalı kanıt kabulü; #23 güvenli Master/Eight-Stage/Preflight; #27 run kayıtlarının doğru kimlik ve kapsam denetimi; #9 canlı kaynak handoff/provenance. Ardından uygun diğer bağımsız görevler. Her önemli kod değişikliğinde ilgili offline regresyonu ekle, topluca çalıştırılabilen yetkili ortamda çalıştır, gerçek sonuçları kanıtla. Test çalıştırılamazsa açık bırak.

---

## TARİHÎ KAYITLAR (eski tarihler ve SHA'lar; canlı ledger yerine geçmez)

## 7 Kasım 2026 — #27 SHA gözlem kilitlenmesi düzeltildi

- Önceki [739373bf](https://github.com/Madsc55/MADSC55-TV-V2/commit/739373bf3290927b5ee0cf97ef8d38e95b724664) değişikliğindeki `root.last_verified_run_observation.development_commit == expected_sha` koşulu, kök dosyanın commit anında güncellenememesi nedeniyle yeni push kabulünü kilitleyebilirdi.
- [13fe5917](https://github.com/Madsc55/MADSC55-TV-V2/commit/13fe59177827770bcddb20ba95a2cc65212462f2) bu zorunluluğu kaldırdı. Kök gözlemi tarihîdir; `verify_grouped_actions` hâlâ beklenen commit SHA'sına ait bütün gerekli başarılı gerçek Actions run kayıtlarını şart koşar.
- [d522acb4](https://github.com/Madsc55/MADSC55-TV-V2/commit/d522acb436685ab89a16cf312cc5f12ccdaca376) regresyonu güncelledi. Kod commitleri gerçek; yeni toplu Actions sonucu henüz doğrulanmadı. #27 tamamlandı sayılmaz.

---

## 7 Kasım 2026 — #27 ve #13/#V2 SIRA 06 gerçek değişikliklerin devri

- #27 SHA eşleştirme güvenlik kontrolü: `v2/tasks/task_engine.py` kök `last_verified_run_observation.development_commit` ile beklenen Actions commit SHA'sını karşılaştırır; uyumsuzlukta fail-closed. Commit [739373bf](https://github.com/Madsc55/MADSC55-TV-V2/commit/739373bf3290927b5ee0cf97ef8d38e95b724664).
- #27 regresyonları: [e98f01ba](https://github.com/Madsc55/MADSC55-TV-V2/commit/e98f01ba024916aeb714e246184617721bf3c489), testte yanlış kök fixture kullanımının düzeltmesi [9cc38334](https://github.com/Madsc55/MADSC55-TV-V2/commit/9cc38334117a2ddd1df8d2b6e541197a6decea35).
- #13/#V2 SIRA 06: gerçek arşiv modülleri `v2/encrypted_archive.py`, `v2/archive_acceptance_gate.py`, `v2/independent_s3_restore.py`. `v2/secure_archive.py` bu dalda yoktur; eski dosya adıyla arama tekrarlanmasın.
- S3 offline regresyonlarına doğru sürüm + yanlış checksum ve eksik anahtar durumları eklendi: [6db0e61f](https://github.com/Madsc55/MADSC55-TV-V2/commit/6db0e61f5a2cb483b3c4a32a1e21dcf971099857). Toplu `v2-ordered-preflight.yml` discovery-tests aşamasına `python v2/test_independent_s3_restore.py` eklendi: [18e54905](https://github.com/Madsc55/MADSC55-TV-V2/commit/18e5490531c9b373649c2c871e381b4844736f71).
- **Kabul kanıtı bekleniyor:** Bu yeni commitlerde push Actions run ID/job/log henüz doğrulanmadı; commit varlığı test başarısı değildir. GitHub'ın commit-run bağlayıcısı yalnız PR koşularını döndürebilir. Gerçek S3 versioned get-object + AES-GCM + 4.955 kimlik restore kanıtı yok; #13/#14 ve #27 tamamlandı olarak işaretlenmeyecek.
- Önceki gerçek koşu #42303308753'te yalnız offline 17-modül işinin sonucu success, canlı AV işi skipped; bu yeni commitlerin testi değildir. Korunan main/PR #9/ana İBO playlist değişmedi.

---

## 7 Kasım 2026 — Görev #27 gerçek CI tetikleme ve toplu test entegrasyonu

- `.github/workflows/v2-actions-trigger-protection.yml` geliştirici dalında güncellendi: `v2/tasks/task_engine.py` ve `v2/tasks/test_task_engine.py` değişiklikleri artık `push` path filtrelerinde; `tasks.test_task_engine` mevcut toplu güvenlik regresyon komutuna eklendi. `PYTHONPATH=v2:v2/tasks` ile test modülünün gerçek import yolu tanımlandı.
- Commitler: [34a93be0](https://github.com/Madsc55/MADSC55-TV-V2/commit/34a93be05e5f74f9353a47b45f24508c800b71a6), [83dbe788](https://github.com/Madsc55/MADSC55-TV-V2/commit/83dbe788bdcb9023db03514d1b319c5556a376d6).
- Bu workflow değişikliği bir push koşusunu tetikleyebilir; ancak bu oturumda yeni run ID/job sonucu elde edilmedi. **Başarılı CI veya görev #27 tamamlandı iddiası yok.** Gerçek koşu sonucunu kontrol etmeden kapatma.
- Canlı AV workflowu manuel-only kalır; ana IBO, main, PR #9, tarihî envanter değişmedi.

---

## 7 Kasım 2026 — Görev #27 güvenli GitHub yazma yolu sertleştirmesi

- Gerçek geliştirme dalı kodu `v2/tasks/task_engine.py` içindeki `assert_safe_write` artık mutlak yolları, iç içe `..` kaçışlarını, `.`/boş bileşenleri, ters bölü işaretlerini, boş veya string olmayan yolları ve korunan IBO dosyasını fail-closed reddediyor.
- `v2/tasks/test_task_engine.py` bu geçiş/koruma bypass örneklerini regresyon testlerine ekledi.
- Kod: https://github.com/Madsc55/MADSC55-TV-V2/commit/6f12eb5f232b513715e975f8021b1a8aa43d00a4 ; test: https://github.com/Madsc55/MADSC55-TV-V2/commit/bd1ab1d818b798ebe20c0477cc2c9432919ab50e
- Bu oturumda yeni GitHub Actions run/job sonucu doğrulanmadı ve yerel test çalıştırılmadı; görev #27 **açık**. Eski yeşil runları yeni commitin kabulü olarak kullanma.
- Ana IBO listesi, main, PR #9 ve tarihî envanter değiştirilmedi.

---

## 7 Kasım 2026 — Görev #27: Actions kanıt kimliği doğrulaması güçlendirildi

- `v2/tasks/task_engine.py` `verify_grouped_actions`: başarılı Actions run kaydı artık yalnız URL önekiyle kabul edilmiyor; URL'deki run ID, gerçek pozitif tamsayı `id` alanıyla birebir aynı olmalı. Python `bool` kimliği ve `0` da reddediliyor. Böylece başka başarılı run'ın bağlantısını taşıyan sahte/yanlış kayıt kabul edilmiyor.
- `v2/tasks/test_task_engine.py`: yanlış run URL/ID ve geçersiz ID regresyonları eklendi. Görev #5'in gerçek ledgerda `blocked` olması test fixture'ına açıkça ayrıldı; canlı durumun sentetik zamanlama testini bozması önlendi.
- Commitler: [3cb9e22a](https://github.com/Madsc55/MADSC55-TV-V2/commit/3cb9e22ad1e7a62a3b9bc73948c48c39e7e1386e), [3f0ec950](https://github.com/Madsc55/MADSC55-TV-V2/commit/3f0ec9507c054a70be11b293157186ecc6a49ee1).
- Görev #27 **in_progress**, tamamlanmadı: yeni commit için gerçek toplu Actions kabulü ve kök `state.json` ile uçtan uca tutarlılık kanıtı bekleniyor. Yeni FFmpeg taraması yapılmadı, kanalların AV durumu yükseltilmedi.
- `main`, PR #9, ana IBO ve tarihî envanter değişmedi.

---

## 7 Kasım 2026 — Görev #12 gerçek dünya FFmpeg kanıtıyla tamamlandı

- Gerçek Actions [#42228674931](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42228674931), job `127928618610` logu: `FINAL_WORLDWIDE_REPORT_GATE` = `COMPLETE_AV_COVERAGE_EVIDENCE`, **34.209/34.209** gerçek aday taranmış, **12.968** video+ses decode, **0** taranmamış, **9** SHA bütünlüğü denetlenen mühürlü paket; **23** regresyon testi `OK`.
- `v2/final_worldwide_report_gate.py` bütün adayların tanımlı probe/arıza durumlarına, tutarlı `video/audio/decoded` bayraklarına ve eksiksiz sayım/şifreli manifest koşullarına uymasını zorunlu kılıyor; bilinmeyen durum fail-closed. Bu kanıtla mevcut görev ledgerındaki **#12 yayın hatalarını sınıflandır** tamamlandı.
- Bu kabul yalnız doğrulanmış dünya raporunun sınıflandırılması içindir; **45 kanal**, **2.643 eksik adresin yeni canlı AV testi**, **1.886 tarihî AV açığı**, **7 eksik SHA**, **IBO cihaz testi** tamamlandı sayılmaz. Sonraki iş #13 RSA restore ve #14 tarihî koruma kabulü için gerçek artifact/roundtrip kanıtı.
- Üretim verisi uydurulmadı. `main`, PR #9, ana IBO ve tarihî envanter değişmedi.

---

## 7 Kasım 2026 — Üretim kanıtı: tarihî 4.955 SHA/AV koşusu yeniden doğrulandı

- GitHub Actions [#42228674931](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42228674931), gerçek job `127928618610`: **success**. Logdaki `HISTORICAL_EXACT_SHA_AV`: 4.955 tarihî kimlik korundu, 4.948 kesin SHA eşleşti, 3.062 video+ses decode kanıtlı, 7 dünya raporunda yok.
- Gerçek artifact `13507480461`, `v2-historical-av-crosswalk-42228674931`, 289.976 byte, süresi dolmamış, SHA256 `78f4b2188696e159662a29bf6cab3530992bd39490367d7342c0fef9958c23fb`. Artifact varlığı ve job başarısı doğrulandı; bu oturumda ZIP restore veya yeniden canlı FFmpeg taraması yapılmadı.
- Görev #4 mevcut ledgerında gerçek kanıt ve açık engel güncellendi: eşleşen ama AV decode kanıtı olmayan 1.886 kayıt ve dünya raporunda olmayan 7 SHA. **Tamamlanmadı.** 45 kayıp kanal, 2.643 adres ve IBO paketleri için yeni AV kanıtı yok; sonuçlar yükseltilmedi.
- Prototip, mock yayın, sahte URL veya gösterim amaçlı IBO çıktısı üretilmedi. `main`, PR #9, ana IBO listesi ve tarihî envanter değiştirilmedi.

---

## 7 Kasım 2026 — Hızlandırılmış tamamlama: özgün kaynak engeli kaydedildi, gerçek Actions jobları okundu

- Mevcut 33 görev manifesti, kök state ve görev ledgerı okundu; yeni görev veya Issue oluşturulmadı.
- Gerçek GitHub Actions API jobları doğrulandı: [#42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753) offline 17-modül job **success**, canlı AV job **skipped**; [#42302404218](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42302404218) eski offline job **failure**; [#42216075104](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42216075104) 12/12 job **success**. Başarılı eski koşular güncel commit'in toplu kabulü değildir.
- Görev #5 **blocked** olarak mevcut `v2/tasks/state.json` kaydına işlendi: 17 özgün dinamik kaynak kimliği ve 8.449 tarihî old_only kaydı korunuyor; üç özgün bozuk satırın kimlikleri eldeki kanıtta tespit edilemiyor. Üç örnek bozuk kayıt testi, özgün üç satırın onarıldığı anlamına gelmez. Aynı metin aramasını tekrarlama; bağımsız işlere geç.
- Son CI filtre commit'i [eaac39fb](https://github.com/Madsc55/MADSC55-TV-V2/commit/eaac39fb4afc4036e2db17f5c2e671b45274d820) için yeni gerçek run ID doğrulanmadı; commit-status boşluğu koşu yokluğu sayılmadı.
- Görev #3/#4 ve 2.643 adres için yeni FFmpeg AV kanıtı bulunmadı; kanal kurtarma veya IBO ihracı kabul edilmedi. Yalnız geliştirme dalında görev ledgerı ve bu not değiştirildi; main, PR #9, korunan IBO ve envanter değiştirilmedi.

---

## 6 Kasım 2026 — V2 DEVAM: yeni Actions regresyonu satır sonu hatası düzeltildi

- [1ea909d8](https://github.com/Madsc55/MADSC55-TV-V2/commit/1ea909d8183004d4f92d19cca04a0a2440f307b7): `test_ordered_preflight_installs_crypto_before_discovery_tests` içindeki `source.split` ayraçları Python'da gerçek satır sonunu eşleştirecek biçime getirildi. Güvenlik denetimleri gevşetilmedi.
- [Issue #1](https://github.com/Madsc55/MADSC55-TV-V2/issues/1) güncellendi; **açık**. Dört sistem workflow'unun yeni gerçek Actions kabul logları alınamadı.
- [#42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753) 190 testlik önceki başarı tekrar çalıştırılmadı; canlı AV kurtarma kanıtı hâlâ yok. `main`, PR #9, korunan IBO ve tarihî envanter değiştirilmedi.

---

## 6 Kasım 2026 — V2 DEVAM: Ordered Preflight sırası için güvenlik regresyonu

- [bb3e6f06](https://github.com/Madsc55/MADSC55-TV-V2/commit/bb3e6f06ce64005d9862f7b935b4df5da10e9e9a): `v2/test_actions_trigger_protection_audit.py` içine, `v2-ordered-preflight.yml` `discovery-tests` içinde `cryptography==44.0.2` kurulumunun ilk testten önce olması ve geniş sürüm aralığı bulunmaması şartı eklendi.
- [Issue #1](https://github.com/Madsc55/MADSC55-TV-V2/issues/1) güncellendi; açık.
- `b16661aa` için GitHub combined commit statuses boş döndü; Actions run sonucunu göstermez. Yeni toplu sistem testinin başarı logu alınamadı. Önceki başarılı [#42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753) tekrar çalıştırılmadı.
- Gerçek AV kanıtı olmadan 45 kanal kurtarılmış sayılmaz. `main`, PR #9, IBO ve tarihî envanter değişmedi.

---

## 6 Kasım 2026 — V2 DEVAM: Ordered Preflight şifreleme bağımlılığı sırası

- Önceki geliştirme HEAD `4b024105cb5ffb435f835441dbcae31f56d75d86` kontrol edildi.
- [4ce71b05](https://github.com/Madsc55/MADSC55-TV-V2/commit/4ce71b0511f912e8792ed42d57afa98a7e2167c1): `.github/workflows/v2-ordered-preflight.yml` `discovery-tests` içinde `cryptography==44.0.2` artık ilk testten **önce** yükleniyor; geç kurulum kaldırıldı. Import kaynaklı hata olasılığı giderildi; log kanıtı olmadan asıl CI hatası olduğu iddia edilmiyor.
- [Issue #1](https://github.com/Madsc55/MADSC55-TV-V2/issues/1) güncellendi, **AÇIK** kaldı.
- Başarılı [17 modül / 190 test Actions #42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753) gereksiz tekrarlanmadı.
- **Kabul engeli:** Dört sistem workflow'unun güncel run ID/job loglarına mevcut bağlantıdan ulaşılamıyor. Yeni toplu test sonucu doğrulanmadı. 45 AV kimlik kurtarma da tamamlanmış değil.
- Yalnız dev workflow ve görev notu değişti; `main`, PR #9, IBO, kategoriler ve tarihî envanter korunuyor.

---

## 6 Kasım 2026 — V2 DEVAM: görev #1 güvenlik regresyonu eklendi, kabul AÇIK

- Geliştirme dalı kontrolünde önceki HEAD `403c1729dac3efc901afa4b09ff44e07e7ce478d` idi. GitHub'da mevcut `[V2 SIRA]` #1–#8 kayıtları bulundu; yeni proje/Issue açılmadı.
- [eb34b7ba](https://github.com/Madsc55/MADSC55-TV-V2/commit/eb34b7ba4acb2a1eab7a9beb5d1fa920b464d3c0): `v2/test_actions_trigger_protection_audit.py` içinde canlı orphan kurtarma workflow'unun manuel-only olması, şifreleme bağımlılığı, ilgili offline regresyon ve değişmez IBO hash denetimi için yeni fail-closed test eklendi.
- [Issue #1](https://github.com/Madsc55/MADSC55-TV-V2/issues/1) güncellendi ve **açık** bırakıldı.
- Başarılı önceki 17 modül / 190 test kanıtı [#42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753) tekrar çalıştırılmadı.
- **Engel:** Bu oturumda GitHub Actions'ın son push run listesine erişim sağlayan connector işlemi bulunmadığından, yeni kodun Master/Eight-Stage/Preflight/Trigger Gate kabulü doğrulanamadı. Yeni Actions run ID veya yeşil sonucu iddia edilmiyor.
- **Koruma:** `main`, PR #9, ana IBO, sabit TRT/DHA sırası, kategoriler, cihaz favorileri, tarihî arşiv ve eski repo değiştirilmedi. Canlı 45 kanal kurtarma hâlâ açık.

---

## 6 Kasım 2026 — Ortak sistem CI tetikleyici çakışması giderildi, Actions doğrulaması açık

- **Korunan ve tekrar çalıştırılmayan başarılı koşu:** [#42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753), commit `4672f994`, 17 modül / 190 test `OK`; canlı AV job `skipped`.
- **Doğrudan doğrulanan kök neden:** `v2/actions_trigger_protection_audit.py` içindeki `MANUAL_NETWORK_OR_MEDIA` kümesi `v2-orphan-m3u-recovery` workflow'unu yalnız `workflow_dispatch` ile sınırlar. Önceki offline regresyonu başlatmak için bu dosyaya eklenen `push`, `UNAPPROVED_AUTOMATIC_PUSH` ve `NETWORK_OR_MEDIA_NOT_MANUAL_ONLY` ihlallerine neden olur. Bu güvenlik kapısı gevşetilmedi.
- **Düzeltme:** [db2b52aa](https://github.com/Madsc55/MADSC55-TV-V2/commit/db2b52aaf116144a579199353aeb0def4dcd8078): mevcut `v2-orphan-m3u-recovery.yml` tam olarak önceki manuel-only blob `c4e291dbe726709db3b6beba07d491d0db6de25b` içeriğine geri döndürüldü. Read-only 190-test başarısı tarihsel kanıt olarak korunuyor.
- **Bekleyen doğrulama:** Master Engine, Eight-Stage Runner, Ordered Preflight ve Actions Trigger & Protected Playlist Gate için bu commit sonrası gerçek run/job logları henüz alınamadı; dört işin hepsi geçti denemez. Geliştirme dalındaki yeni push'un mevcut güvenli CI tetikleyicilerini başlatması beklenir, fakat run ID doğrulanmadan başlatıldı iddiası yapılmaz.
- **Sonraki aşama:** Dört sistem CI koşusunun sonuçlarını ve olası ek hataları doğrula; yalnız hepsi başarılıysa gerçek 45 kimlik AV kurtarmaya geç. `main`, ana IBO, PR #9, eski repo ve tarihî arşiv değişmedi.

---

## 6 Kasım 2026 — 4672f994 kurtarma kabulü BAŞARILI; diğer sistem kapıları AÇIK

- **Doğrulanan Actions:** [#42303308753](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42303308753), commit [4672f994](https://github.com/Madsc55/MADSC55-TV-V2/commit/4672f994b47d933a9232c2cc887f143dea3d7b3b), job `128186296451`: **190 test, OK** (17 modüllük read-only kurtarma regresyonu). Şifreleme kurulumu ve korunan IBO/tarihî metadata kontrolleri geçti. Canlı AV job `128186298557` **skipped**.
- **Diğer kapılar:** Kullanıcı aynı commit için Master Engine, Eight-Stage Runner, Ordered Preflight ve Actions Trigger & Protected Playlist Gate başarısızlığını bildirdi. Bu dört koşunun run/job ID ve logları henüz erişilebilir araçlarla tespit edilemedi; ortak kök neden **doğrulanmadı**, rastgele düzeltme yapılmadı. Commit bazlı PR-run sorgusu 0 sonuç verdi; bu sorgu push/dispatch koşularını kapsamıyor.
- **Karar:** Başarılı 17 modüllük regresyon tekrar çalıştırılmayacak. Dört sistem kapısının gerçek logları alınmadan yeşil kabul edilmeyecek; canlı 45 kimlik AV kurtarma da tamamlandı sayılmayacak.
- **Koruma:** Yalnız geliştirme dalındaki bu görev notu değiştirildi; `main`, ana IBO, PR #9, arşiv ve eski depo değişmedi.

---

## 6 Kasım 2026 — Actions #42302404218 kök neden ve düzeltme kaydı

- **Gerçek koşu:** [#42302404218](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42302404218), job 128183217444, 139 test / 3 failure / 20 error. Korunan IBO ve tarihî metadata hash kontrolü **başarılı**; 17-modül toplu test job'u **başarısız**; canlı AV tarama job'u **skipped**.
- **Kök neden:** Salt okunur offline job'da `cryptography` kurulmamış; 20 import hatasının ortak nedeni `ModuleNotFoundError: No module named 'cryptography'`. Üç failure: iki baseline senaryosu fixture içinde aynı kaynak/hash çiftini yineliyor; aday sayısı testi şifreli aday sayısı için yeni doğru üst sınır davranışı yerine eski eşitlik varsayımını kullanıyor.
- [e07de418](https://github.com/Madsc55/MADSC55-TV-V2/commit/e07de418edabba4c7d8ccabcbf17f1854a95871f): mevcut salt okunur job'a sabit `cryptography==44.0.2` kurulumu eklendi.
- [4672f994](https://github.com/Madsc55/MADSC55-TV-V2/commit/4672f994b47d933a9232c2cc887f143dea3d7b3b): 55 benzersiz kaynak/hash çifti / 50 kimlik sağlayan baseline fixture; eksik özgün kimlik, yeni upstream kayıt ve açık URL testleri; 38 adayın 37'lik mühürlü arşive sığmadığını reddeden güvenlik regresyonu. Bu test dosyası değişikliği, yalnız dev dalındaki read-only 17 modüllük push tetikleyicisinin kapsamındadır.
- **Doğrulama bekliyor:** Son commit için yeni Actions run ID/log/başarı henüz alınamadı. Başarılı denmeden bu aşama kapanmayacak. Korunan `main`, IBO, PR #9 ve geçmiş envanter değiştirilmedi.

---

## 6 Kasım 2026 — Salt okunur toplu regresyon tetikleyicisi eklendi; Actions sonucu BEKLİYOR

- Mevcut `.github/workflows/v2-orphan-m3u-recovery.yml` önceden yalnız `workflow_dispatch` içerdiği için push ile çalışmıyordu.
- [1f53039c](https://github.com/Madsc55/MADSC55-TV-V2/commit/1f53039c0725e654860652103c89ddd01597693f): mevcut workflow'a yalnız `madsc/v2-discovery-bulk-20261031` dalında `v2/test_orphan_resolution_gate.py` değişince çalışan **read-only 17 modüllük offline** job eklendi. Mevcut canlı dört kaynak kurtarma job'u yalnız `workflow_dispatch` ile çalışmaya devam eder; `contents: read` korunur.
- [c674f949](https://github.com/Madsc55/MADSC55-TV-V2/commit/c674f949fb113c014c0a0358b5510ae890b76896): test dosyasına açıklama commit'i gönderilerek push tetikleyicisi koşulu sağlandı.
- **Kanıt sınırı:** GitHub Actions run ID, job sonucu veya logu henüz alınamadı. Push tetikleyicisinin çalışması amaçlandı; başarılı/başlamış olduğu **iddia edilmiyor**. CI doğrulanmadan 17 modül veya 45 kanal tamamlandı sayılmayacak.
- Sonraki iş: gerçek run ID ve 17-modül logunu kontrol et; hata varsa düzelt, yeniden tetikle; kabulden sonra 45 kimliğin AV kurtarmasına geç.
- Ana IBO, `main`, PR #9, tarihî kimlikler ve özel URL arşivi değiştirilmedi.

---

## 6 Kasım 2026 — 468cd6cd sonrası doğrulanmış devam kaydı (kurtarma toplu kabulü AÇIK)

- **Geliştirme dalı:** `madsc/v2-discovery-bulk-20261031`. Son kontrol edilen kod commit'i `468cd6cde98eaa6952641fe0ca0caec44bbc394c`.
- **Mevcut takip:** GitHub Issues `[V2 SIRA]` kayıtları ve bu `DEVAM_NOTU.md` bulundu. Mevcut kayıtlar silinmedi veya yeniden başlatılmadı. Önceden kararlaştırılan 33 işin tam eşleştirmesi henüz doğrulanmadığından, 8 görünen Issue kaydı 33 işin tamamı olarak yorumlanmamalıdır.
- **Actions kontrolü:** `468cd6cd` için combined status sorgusunda 0 durum; yalnız PR tetiklemeli runları döndüren commit-run sorgusunda 0 sonuç. Bunlar manuel `workflow_dispatch` koşularının yokluğunu ispatlamaz. `.github/workflows/v2-orphan-m3u-recovery.yml` manuel tetiklemeli. **Bu kayıt tarihinde yeni toplu koşu başlatıldığı veya başarılı olduğu doğrulanmadı.**
- **İlk açık kabul:** `v2/test_orphan_resolution_gate.py` dahil 17 modüllük tek toplu offline regresyonu çalıştır; ardından mevcut 55 kaynak kaydı/50 kanal kimliği fail-closed kapısını gerçek şifreli kanıtlarla değerlendir. Başarılı CI olmadan tamamlandı sayma.
- **Önemli ayrım:** 5 AV kanıtlı / 32 adaylı AV kanıtsız / 13 adaysız, son tarihî raporun 50 kimliklik dağılımıdır; yeni test sonucu değildir. 45 eksik kanal kurtarılmış sayılmaz.
- **Koruma:** `main`, PR #9, `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, TRT 1/DHA sabit sırası, eski repo ve tarihî kanıtlar değiştirilmedi.
- **Sonraki işler:** 33 görev korunarak sıralı devam: kurtarma kabulü → 45 kimlik → 2.643 adres → doküman/forge adaptörleri → 3 bozuk satır/17 dinamik kaynak → 4.955 kimlik/1.886 AV açığı ve RSA/SHA restore → TR/AZ/XMLTV → Actions güvenliği → ayrı IBO 1000/2000 paketleri → toplu kabul ve kullanıcı cihaz testi.

---

## 5 Kasım 2026 — 15 MADDELİK PAKETİN GERÇEK TOPLU UYGULAMA VE KABUL KAYDI

**Uygulama:** Yalnız \`Madsc55/MADSC55-TV-V2\` geliştirme dalında. GitHub ana İBO listesi korunmuştur; YEDEKLER/YENİLER/FAVORİLER, sabit TRT 1/DHA kayıtları, eski depo ve açık PR #9 değiştirilmemiştir. Cihaz testi kullanıcıya aittir. Bu kayıt kaynak/AV/IBO kanıt türlerini birbirine karıştırmaz.

**Doğrulanmış kod ve test kanıtı:**
- [9c9a544a](https://github.com/Madsc55/MADSC55-TV-V2/commit/9c9a544a21fe3773be349e82e52bd1d61acfeb5e) IPTV API/EPG kimlik keşfi ve İBO test listesi için gerçek FFmpeg video+ses güvenlik kapısı.
- [571218a0](https://github.com/Madsc55/MADSC55-TV-V2/commit/571218a0e88def780d0013c0ec2b9405fb1d7bb7) büyük API koleksiyonları düzeltmesi, korunan ana listeye yazabilecek eski NewlistTR aktarıcısının pasifleştirilmesi. [API koşusu #42032119279](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42032119279) başarılı, 17/17 ilgili test geçti.
- [b10f52a1](https://github.com/Madsc55/MADSC55-TV-V2/commit/b10f52a16c62cc751f46f863985f981e786d2275) gerçek, toplu FFprobe+FFmpeg AV kabulü ve RSA/AES şifreli URL kanıtı. [Koşu #42033067184](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42033067184) BAŞARILI: 270 adresin 270'i test edildi, 171 adresde görüntü+ses decode edildi, 99 adres geçmedi, 0 adres taranmamış; 147 ayrı IPTV API kanal kimliğinde kanıtlı akış var, 24 kanıtlı alternatif URL var. Bu 147 kimliğin konuşma dili veya İBO cihazı kanıtlanmamıştır.
- [71c3230d](https://github.com/Madsc55/MADSC55-TV-V2/commit/71c3230d28dd1f015c029f1d611cb6dce8d82565) şifreli adres/kanal kimliği uyuşmazlığını reddeden dışa aktarma koruması. [IBO özel aktarım güvenlik koşusu #42033543589](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42033543589) başarılı.
- [e17f28d4](https://github.com/Madsc55/MADSC55-TV-V2/commit/e17f28d4467b5c1eb25cb0d0faeb32564b951a1b) API URL hash + TVG-ID kesin kimlik eşleştirmesini sıralı kaynağa bağladı. [Birleşik arama #42034880458](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42034880458) BAŞARILI iş akışı, ancak **kaynak kapsamı kısmi**: 47 yapılandırılmış kaynak; 13 kaynak ailesi; 9.163 benzersiz aday; 237 YouTube video sayfası, bunlardan yalnız 38'inde canlı metadata doğrulandı, 116'sı metadata açısından belirsiz. YouTube API anahtarı yapılandırılmamış. GitHub/Gist, GitLab/Codeberg ve resmî canlı sayfa kaynaklarında sınır/hatalar var. Sayfa referansları İBO M3U8 değildir.
- [db80008c](https://github.com/Madsc55/MADSC55-TV-V2/commit/db80008c3a3dd6f08d4b8313af221fabeb877580) gerçek API+AV kanıtını yeniden taramadan iş kuyruğuna dönüştüren modül. [Master #42035591970](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42035591970), [Eight-Stage #42035592124](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42035592124) BAŞARILI; 641/641 çevrimdışı regresyon geçti.
- [31dda5ef](https://github.com/Madsc55/MADSC55-TV-V2/commit/31dda5ef8e88c1d7f79571a7355486b759441a53) mevcut iki tamamlanmış Actions kanıtını tekrar yayın taramadan birleştirir; [koşu #42036109234](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42036109234) BAŞARILI, 25/25 ilgili test başarılı, şifreli kanıt SHA bütünlüğü sağlam. Anonim çıktı artifact: \`v2-traz-api-av-next-bulk-queue-42036109234\`, artifact ID \`13418921771\`.

**15 madde ilerleme ve açık işler (tamamlanmayanlara TAMAM denmez):**
1. Dünya çapında TR/AZ/Türkçe kaynak keşfi: 13 aile taraması ve API üzerinden **geliştirildi**; canlı kaynak kapsama hataları nedeniyle **kısmi**.
2. YouTube canlı keşif: 237 aday, 38 canlı metadata; API anahtarı eksik/116 metadata belirsiz. **Kısmi, İBO URL kanıtı değil.**
3. Resmî yayıncı siteleri: dizin/site eşleştirme mevcut; herkese açık doğrudan HLS kaynağı için kanal bazında AV kabulü **tamamlanmadı**.
4. M3U/M3U8 ve doküman/forge kaynakları: 9.163 aday ve adapter raporları; GitHub/Gist, GitLab/Codeberg, HTML indeksi kısıtları **kısmi**.
5. Tarihî kimlik kurtarma: 4.955 tarihî orijinal URL/hash eşleşmesi korunuyor; 50 özgün bozuk kimlikten en son doğrulanmış eski raporda 46'sı gerçek AV'siz. Yeni API AV adresleri bu kimliklere otomatik kurtarıldı sayılmadı. **Açık.**
6. Alternatif akışlar: 147 kimlikte 171 AV-doğrulanmış adres, 24 ek alternatif; kalıcı istikrar ve resmî yayıncı kesinliği henüz yok. **Kısmi.**
7. Gerçek toplu AV kabulü: API adaylarının 270/270 adresi topluca test edildi, 171 video+ses decode edildi; **bu kapsam için tamam**, tüm dünya/İBO cihaz testi değil.
8. Periyodik keşif/sağlık: kaynak takip kodu mevcut; uzun dönem ve cihaz doğrulaması **açık**.
9. Açık IPTV API: 529 hedef kanal kimliği, 270 adres adayı ve 71 Türkiye/Azerbaycan dışı Türkçe/Azerice feed-dili metadata kimliği; **API keşif ve birleştirme tamam**, AV ayrı.
10. EPG/XMLTV: API rehber eşleşmesi 185, **344 EPG referansı eksik kimlik** yeni iş kuyruğunda; XMLTV program doğruluğu ayrıca **açık**.
11. Konuşulan dil: API ülke/feed bilgileri gerçek ses dili kanıtı değildir. **Açık.**
12. İsveç erişimi: Actions runner sonucu İsveç ağında cihaz testi değildir; geo/DRM aşılmadı. **Açık.**
13. HLS/codec/çözünürlük: eski kalite modülleri mevcut; yeni 270 aday için tam master/variant kalite ve codec kabulü **açık**.
14. Aynı kanal alternatif isim eşleştirme: API kimliği + URL SHA ve kesin TVG-ID bağlantısı entegre; muğlak adları otomatik birleştirmiyor. **Kod tamam, canlı referans kapsamında eşleşme raporu.**
15. Kanal güvenilirlik puanı: sadece tek zamanlı AV kanıtı yüksek güvenilirlik üretmez; bu adaylarda puan bilinmiyor ve uzun dönem ölçüm **açık**.

**Bir sonraki işlemlerin korumalı sırası:** Kaynak kapsama sorunları ve 309 stream-adressiz kimlik → 344 EPG eksiği / kanal kimliği köprüsü → tarihî 46 AV eksik kimlik için kesin alternatif bulma → yeni konuşma dili/İsveç/HLS kalite/stabilite kanıtı → şifreli kanıtın kullanıcıya ait **özel RSA anahtarla yerel açılması** ve yalnız ayrı \`private-*.m3u8\` İBO cihaz-test listesi. Doğrudan plaintext URL'ler açık artifact'lara aktarılmaz; ana İBO değişmez, PR #9 birleştirilmez.

---


## 5 Kasım 2026 — İLAVE 7 TAVSİYE (9–15): TR/AZ canlı kanal keşfi ikinci genişletme paketi
- **Durum:** Kullanıcının sonraki proje çalışmaları için açıkça notlara eklenmesini istediği yedi yeni öneridir. İlk sekiz öneriyle birlikte **15 maddelik tek toplu geliştirme paketi** olarak değerlendirilecek. Bu satırlar tamamlanan özellik veya test kanıtı değildir.
- **9. Açık IPTV API keşfi:** Kamuya açık, izinli JSON/API kaynaklarını (özellikle IPTV-org ve uygun Dearbulut metadata'sını) kanal kimlikleri, ülke/dil, logo, alternatif isim, EPG ve yayın kaynağı eşleşmesi için kullan; API kaydı doğrudan çalışan stream kanıtı sayılmaz.
- **10. EPG/XMLTV tabanlı eksik kanal keşfi:** EPG'deki TR/AZ ve dünya çapındaki Türkçe kanal kimliklerini V2 envanteriyle karşılaştır; eksik kimlikleri gerçek yayın bağlantısı bulma kuyruğuna al. EPG bilgisi oynatılabilir URL değildir.
- **11. Yayın dili doğrulaması:** Ülke/isim bilgisinden yayın dili tahminini ayrı tut; izinli metadata ve gerektiğinde kısa ses örneklerinin analiziyle Türkçe/Azerbaycan Türkçesi konuşmayı kanıta dayalı sınıflandır. Yanlış pozitifleri ayrıca işaretle.
- **12. İsveç erişilebilirliği:** Türkiye/Azerbaycan kaynaklarından bağımsız olarak İsveç'teki gerçek erişilebilirliği kontrollü testlerle karşılaştır; bölge kısıtlamalarını raporla, DRM/geo kontrolünü aşma. Son İBO cihaz oynatım testi kullanıcının sorumluluğundadır.
- **13. HLS kalite/codec testi:** Varyant M3U8 master/variant ayrımı, çözünürlük (360p/720p/1080p vb.), bitrate, ses/video codec, süreklilik ve İBO uyumluluk adaylarını topluca ölç; en yüksek çözünürlüğü otomatik en iyi yayın sayma.
- **14. Aynı kanalın farklı isimlerini tek kimlikte eşleştirme:** Örneğin Sözcü TV/SZC TV/Sözcü Televizyonu. TVG-ID, resmî yayıncı, kaynak geçmişi, logo ve gerekirse gerçek video kanıtını birleştir; sadece isim benzerliğiyle farklı kanalları birleştirme.
- **15. Kanal güvenilirlik puanı:** Tek başarılı HTTP veya AV kontrolü yerine farklı zamanlarda video+ses başarısı, kopmalar, oynatma kararlılığı, URL ömrü, kaynak kalitesi ve gerçek İBO cihaz kanıtını ayrı ağırlıklarla puanla. Yetersiz kanıtı yüksek güvenilirlik olarak gösterme.
- **Birleştirilmiş uygulama yaklaşımı:** Önce mevcut kaynak kapsama eksikleri ve önceden kayıtlı 1–8 maddeleri; ardından 9–15 ek doğrulama ve zenginleştirme. İlgili adımlar sıralı ilerlesin, testler aşama bazında topluca çalıştırılsın. Kaynak keşfi → kimlik eşlemesi → gerçek oynatılabilir HTTP(S) URL → HTTP kontrolü → FFprobe/FFmpeg video+ses → ayrı deneme M3U listesi → kullanıcının İBO cihaz testi farklı kanıtlardır.
- **Değişmez koruma:** Yalnız `Madsc55/MADSC55-TV-V2`; eski depo kullanılmaz. Ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, ilk iki sabit YEDEKLER öğesi (TRT 1 1440P QHD; DHA CANLI 720P HD), protected main ve PR #9 korunacak; izinsiz merge veya üretim listesine otomatik ekleme yapılmaz.
- **Bu kayıt sırasında:** Yalnızca DEVAM_NOTU.md belgesi güncellendi; tarama, test, kaynak ekleme, çalışan kanal doğrulaması veya ana liste değişikliği yapılmadı.

## 5 Kasım 2026 — BEKLEYEN TOPLU İŞ PAKETİ: İnternette TR/AZ canlı TV keşfini genişletme
- **Durum:** Kullanıcının soru-cevap sohbetinde onayladığı gelecek çalışma notu. **Yalnızca plan/istek kaydıdır; kod, entegrasyon, kaynak, AV testi veya İBO aktarımı bu notla tamamlanmış sayılmaz.**
- **Hedef:** Türkiye, Azerbaycan ve dünya genelinde Türkçe/Azerbaycan Türkçesi yayın yapan, internet üzerinden canlı izlenebilen mümkün olduğunca çok **gerçek ve benzersiz televizyon kanalını** keşfetmek; İBO Player'a uygun, erişilebilir, görüntülü+sesli bağlantılarını doğrulamak. Yalnız M3U listeleriyle sınırlı kalmamak; YouTube'da yayın yapan Sözcü TV gibi kanalların resmî/alternatif yayın adreslerini de araştırmak.
- **8 iyileştirme (bir sonraki çalışmada tek sıralı iş paketi halinde):**
  1. **Dünya çapında Türkçe kanal avcısı:** TR/AZ yanında Avrupa, Kıbrıs, Balkanlar, ABD ve diğer bölgelerdeki Türkçe/dil temelli TV adaylarını ara; ülke ile kanıtlanmış yayın dilini ayır.
  2. **YouTube canlı yayın keşfi:** Türkiye/Azerbaycan haber, yerel, spor, kültür, müzik vb. canlı yayın kanal kimliklerini ve resmî canlılık metadata'sını bul; aynı kanalların bağımsız ve izinli HTTP(S) HLS/M3U8 kaynaklarını araştır. YouTube watch/kanal sayfası M3U8 değildir; geçici veya imzalı YouTube CDN URL'leri kalıcı İBO adresi sayılmaz; giriş/DRM/erişim engeli aşılmaz.
  3. **Resmî yayıncı sitelerindeki canlı akışlar:** canli-yayin/live/watch/izle sayfalarını ve herkese açık HLS kaynaklarını araştır, sağlayıcı/kanal kimliği ile eşleştir; izin veya DRM gerektirenleri atla.
  4. **Geniş M3U/M3U8 kaynak taraması:** IPTV-org ülke+dil listeleri, Free-TV, GitHub/Gist, GitLab/Codeberg, onaylı kamuya açık M3U arşivleri ve Scribd/SlideShare/Internet Archive gibi belge referanslarından gerçekten doğrulanmış liste kaynaklarını kullan; ham EXTINF/URL doğrula; aynı kaynağı ve URL'yi çoğaltma; kaynak/kapsam/hata raporları eksiksiz olsun.
  5. **Kayıp kimlikleri yeniden bulma:** Eski kanal TVG-ID, ad, resmî site, kaynak geçmişi ve şifreli URL arşivinden güvenilir alternatif arama; geçici başarısızlıkta kanal geçmişini/kimliklerini silmeme.
  6. **Aynı kanal için yedek akışlar:** Her kanalın kanıtlı 720p/1080p vb. alternatif URL, kalite, dil, kaynak ve güvenilirlik kayıtlarını sakla; en iyi bağımsız akışı seç, diğerlerini yedekle; muğlak isimleri yanlış birleştirme.
  7. **Toplu gerçek AV kabulü:** HTTP erişimini, FFprobe/FFmpeg gerçek video+ses decode testini ve kullanıcıda yapılacak İBO cihaz testini ayrı raporla; İsveç erişimi/geo sınırlamasını not et. Yalnız başarıyla doğrulanan akışlar ayrı İBO deneme listesine aday olur.
  8. **Periyodik keşif/sağlık/arşiv:** Yeni TR/AZ canlı kanalları izlemeye al, geçici hatalarda silme, güvenilir yeni akışları yeniden doğrula; EPG/logo/kimlik eşlemesi ve kaynak geçmişini koru; otomatik ana playlist yazma.
- **Uygulama sırası:** (A) Mevcut TR/AZ kaynak entegrasyonunun eksiklerini bitir → (B) YouTube+resmî TV sayfalarından yeni kanal kimlikleri ve doğrudan izinli akış adayları keşfet → (C) dünyadaki M3U/M3U8 kaynakları ve tarihsel eşleştirme ile havuzu zenginleştir → (D) tek toplu HTTP+AV kabul turu → (E) sadece kanıtlı adayları ayrı, manuel onaylı İBO test listesine hazırla → (F) güncel/bozuk/yedek durum takibini kur. İlgili testleri sırayla fakat aşama bazında toplu yap; tek tek gereksiz tekrarlar yapma.
- **Değişmez güvenlik kuralları:** Sadece `Madsc55/MADSC55-TV-V2`; eski `madsc-tv` deposuna dokunma. `main` korunmalı, PR #9 açıkça izin verilmeden merge edilmemeli. `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` ile YEDEKLER/YENİLER/FAVORİLER ve cihaz favorileri korunmalı; YEDEKLER ilk iki sıra TRT 1 1440P QHD ve DHA CANLI 720P HD. Kullanıcı İBO cihaz testini kendisi yapacak. Kaynak keşfi ≠ doğrudan M3U ≠ HTTP ≠ AV ≠ İBO cihaz doğrulaması.
- **Bu not kaydında uygulanmayanlar:** 8 özellik için yeni kod veya Actions test çalıştırması yapılmadı; kaynak entegrasyonlarının %100 tamamlandığı veya yeni kanalların oynadığı iddia edilmez.

## 3 Kasım 2026 — Worldwide Discovery kaynak bütünlüğü / #153 devam kaydı
- Canlı beş kaynak doğrulaması başarılı: Actions 41548331416, commit 5290db79. Beş grubun her biri için en az bir HTTP erişilebilir M3U doğrulandı; bu yayın decode kanıtı değildir.
- Worldwide Discovery önce 2, sonra 1 hata verdi. afff86b2 logları kalan hatayı görünür kıldı; d97ed1a sonrası canlı koşuda hata 'index-github-turkish-iptv-topics' (HTTPError) olarak belirlendi.
- de1a8c2b ve d97ed1a isteğe bağlı HTML indeksinden türetilen bozuk M3U bağlantılarını zorunlu kaynak hatalarından ayırdı. 4cffec72 ayrıca erişilemeyen isteğe bağlı HTML indeks sayfasını 'OPTIONAL_INDEX_FAILED' olarak denetim kaydında tutuyor; zorunlu M3U kaynağı hataları ve gerçek aday bütünlüğü testleri başarısız olmaya devam eder.
- Son kesin gözlenen Worldwide koşusu 41549287420 başarısızdı: 49 kaynak, 8077 aday, 1 hata (isteğe bağlı GitHub topic HTML indeksi). 4cffec72 sonrası toplu Actions sonucunu ayrıca doğrulamak gerekir; başarı doğrulanmadan tamamlandı denmez.
- Ana İBO playlisti, YEDEKLER/YENİLER/FAVORİLER, main, PR #9 ve eski depo değiştirilmedi.

## 2 Kasım 2026 — M3U metadata koruması (test bekliyor)
- `cffb38f5996acea625d58bc073bb95891cf689ea`: M3U export için EPG/logo/grup/URL korunumu regresyon testi eklendi. GitHub Actions sonucu henüz alınmadı; test başarı iddiası yok.
- `e26e0f884b29b6c2af037d70904ee03ad71f2ab0`: `v2/master_engine.py` M3U dışa aktarımında `tvg-id`, `tvg-logo`, `group-title` alanlarını EXTINF satırına taşıyacak şekilde değiştirildi.
- GitHub Contents API yazma işlemi başarılı; yerel test, GitHub Actions run ID, medya decode ve gerçek M3U artifact henüz doğrulanmadı. Bu aşama TAMAMLANDI değildir.
- Korunan ana İBO playlisti, YEDEKLER/YENİLER/FAVORİLER, main, PR #9 ve eski depo değiştirilmedi.

## 2 Kasım 2026 — gerçek M3U dışa aktarma satır sonu düzeltmesi
- `ad1d70ca2bacf123fd199440f68bc0daa9da8dea`: `6a96d044` ile eklenen standart 500/1000/2000 paketlerinde gerçek satır sonları yerine yazılan literal `\\n` hatası düzeltildi. Bu hata paketlerin geçerli M3U olarak ayrıştırılmasını engelliyordu.
- `02da2782dceb99f21a51346752f5c5e1bf655c0e`: standart paketlerle mevcut 500'lü batch'ler aynı `render_m3u()` fonksiyonunu kullanıyor; çıktı içeriği gerçek aday URL'lerinden türetiliyor.
- `441ab5100e9aa09620975123bd94be0c175d5be6`: çok satırlı M3U formatı, isim temizliği, URL korunumu için regresyon testi eklendi.
- Test durumu: kod ve test commit edildi; GitHub Actions run ID ve test sonucu doğrulanmadı. Yerel test koşusu yapılmadı. Fiziksel 500/1000/2000 gerçek paket üretimi ve kalıcı şifreli arşiv geri yüklemesi doğrulanmadı. Ana İBO playlisti, YEDEKLER/YENİLER/FAVORİLER, main, PR #9 ve eski depo değiştirilmedi.

## 2 Kasım 2026 — toplu CI ve gerçek paket dışa aktarma değişiklikleri
- Eski hata kanıtı: Verification #43 (`3bfc43c`) 154 testten 1 hata; Master #107 aynı eski committe 10 testten 1 hata (`test_duplicate_sources_decode_once_and_keep_all_provenance`, `0 != 1`). Kaynak: kullanıcının Actions ekran görüntüleri. Eski test M3U kaçışları `4953142` ile daha önce düzeltilmişti; tekrar değiştirilmedi.
- `d22967af76404813312e779793c1eea35fe28d09`: V2 Master Engine push job artık tüm unittest modüllerini toplu çalıştırır, logları hata halinde de artifact olarak saklar; manuel master job'u test edilen `github.sha` commitini checkout eder, gerçek run kimliğini artifact'e ekler.
- `6a96d044a5436407ff498b55170861c355fcd923`: Master Engine mevcut 500'lü çıktıya ek olarak **yalnızca yeterli sayıda gerçek medya-decode doğrulanmış aday olduğunda** 500, 1000, 2000 tam dolu fiziksel `.m3u` paketlerini üretir. Eksik paketleri sahte URL ile doldurmaz; kısmi kaynak hatasında paket yayımlamaz; rapora `standard_full_packages` sayıları eklenir. Bu kod değişikliği gerçek dosyaların üretildiği anlamına gelmez.
- GitHub Actions: geliştirme dalı push tetikleyicileri yapılandırılmıştır; yeni commitlerin sayısal run ID ve job sonucu bağlı API üzerinden elde edilmedi, başarılı sayılmadı. Gerçek canlı tarama yalnızca manuel workflow_dispatch ile, `V2_ARCHIVE_KEY_HEX` sırrı varsa çalışır. Doğrulanmış yayın adedi ve tarihî 4.955 adayın gerçek dosyası mevcut oturumda doğrulanamadı. Artifact 30 gün saklanır; kalıcı harici arşiv yerine geçmez.
- Ana İBO playlisti, YEDEKLER/YENİLER/FAVORİLER, `main`, PR #9 ve eski depo değiştirilmedi.

## 2 Kasım 2026 — tarihî URL koruması ve yeni regresyon
- `0528e2f6dc6bc0d1491ebef83c8d79116b344a68`: tarihî URL doğrulayıcısı `127.1`, `2130706433`, `0177.0.0.1`, `0x7f000001` gibi resolver tarafından yerel IP'ye çözümlenebilen alternatif sayısal hostları ve `.localhost` alt alanlarını reddediyor. Gerçek kaynak envanterine veya ana playlist'e dokunulmadı.
- `dab56afc23c2689bce50c05c7769484dc99d5ce3`: bu durumlar için çevrimdışı regresyon testi eklendi. GitHub'a commit kaydedilmesi Actions testinin başarılı olduğu anlamına gelmez.
- Sekiz aşama durumu: (1) Master Engine kodu mevcut, uçtan uca kanıt yok; (2) kaynak entegrasyonları kısmen mevcut, gerçek tarama doğrulanmadı; (3) FFmpeg yerel kontrolü önceki ekranda başarılı, canlı yayın decode kanıtı yok; (4) 4.955 tarihî adayın tam kurtarma kanıtı yok; (5) sınıflandırma/tekilleştirme kısmen testli; (6) şifreli arşiv kodu mevcut, kalıcı dış geri yükleme kanıtı yok; (7) gerçek 500/1000/2000 çıktı dosyaları doğrulanmadı; (8) Actions #43 ve Master #107 eski commitlerde başarısız, yeni commitler için run ID/job sonucu elde edilmedi.
- Koruma: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, `main`, PR #9 ve eski depo değiştirilmedi. Engeller: GitHub bağlantısında push Actions run listesi ve workflow_dispatch çağırma işlemi mevcut değil; bu nedenle yeni run ID veya başarı sonucu uydurulmadı.

## 2 Kasım 2026 — Master Engine immutable playlist CI koruması
- `cd0b5a44297b9bf7ada5b75ba745dd6a6b9b9b3e`: `.github/workflows/v2-master-engine.yml` offline-tests koruması yalnızca HEAD ile dosya karşılaştırmak yerine sabit doğrulanmış Git blob SHA `4b1c3cea4b5107a425abab60f62d41f9f81e05a7` değerini de kontrol ediyor. Böylece HEAD içinde yanlışlıkla değiştirilmiş ana playlist CI tarafından kabul edilmez.
- CI sonucunun yeşil olduğu henüz bağımsız doğrulanmadı; gerçek run ID alınamadı. Ana playlist dosyası değiştirilmedi. Sekiz aşama uçtan uca tamamlandı sayılmıyor.

## 2 Kasım 2026 — Master Engine çıktı artifact kapsamı
- `876e972299b359633fd75aecf191ce23277b5ac4`: manuel Master Engine işinin artifact kapsamı yalnızca `report.json` yerine `output/` içindeki gerçek rapor ve varsa M3U paketleri ile `inventory.enc` şifreli envanterini içeriyor. Bu yalnızca artifact toplama altyapısıdır; taramanın veya paket üretiminin başarılı olduğu iddiası değildir.
- GitHub Actions artifact saklama süresi 30 gün; kalıcı harici şifreli arşiv yerine geçmez. Yeni commit'in Actions run ID/job sonucu henüz doğrulanmadı. Ana İBO playlisti, main, PR #9, eski depo değişmedi.

## 2 Kasım 2026 — V2 Master Engine #107 hata kanıtı ve CI düzeltmesi
- Kullanıcı ekran görüntüsü: **V2 Master Engine #107**, commit `3bfc43c`, **FAILURE**, `offline-tests` 11 saniyede başarısız, `master` skipped. `test_duplicate_sources_decode_once_and_keep_all_provenance`: `AssertionError: 0 != 1`; 10 testten 1 başarısız. Bu **eski commit** için sonuçtur; güncel dalın yeni test sonucu değildir. Sayısal Actions run ID ekran görüntüsünde yok.
- `495314228800c43abc43b630fe4ec125abea9f3a` ile test M3U satır sonları düzeltilmişti; güncel dosyada doğru `\\n` kaçışları okundu.
- `2ebbde12ebea4772ee5d9d91cef4fdb51315bce3`: `.github/workflows/v2-master-engine.yml` içinde manuel gerçek master job'u `needs: offline-tests` ile başarı kapısına bağlandı; offline job özeti gerçek run ID, commit ve URL gösterecek. Kod commit edildi, yeni Actions sonucu henüz doğrulanmadı.
- Korunan ana playlist, `main`, PR #9 ve eski depo değiştirilmedi.

## 2 Kasım 2026 — yeni oturum, CI doğrulama ve açık engeller
- Koruma: yalnızca `madsc/v2-discovery-bulk-20261031` geliştirme dalı; ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, `main`, eski depo ve PR #9 değiştirilmedi.
- Son kullanıcı ekran görüntüsünde **Actions #43** (`3bfc43c0ea33ae9e1cb7897e425be8b7d76532c9`) **FAILURE**: offline regressions 154 testten 1 hata, FFmpeg başarılı. Bu koşu için sayısal API run ID henüz elde edilmedi; #43 yalnızca görünen çalışma numarasıdır.
- `495314228800c43abc43b630fe4ec125abea9f3a`: yeni M3U regresyon testindeki yanlış `\\n` kaçışları düzeltildi. Sonraki testlerin yeşil olduğu kullanıcı tarafından bildirildi; API üzerinden doğrulanmış run ID/job sonucu yok.
- `54c2b9bbea2b9cb4097cd12f1a525c7e7f67495f`: özel IP ve URL kimlik bilgileri için offline kaynak doğrulama testi eklendi; yeni koşu sonucu bağımsız doğrulanmadı.
- `dcdac238143cc110f78e158deccd6c42166e3042`: regresyon işinin GitHub Actions adım özetine gerçek `GITHUB_RUN_ID` bağlantısı ve `GITHUB_SHA` yazması sağlandı; yeni CI sonucu henüz doğrulanmadı.
- Gerçek açık işler: push Actions run ID ve loglarını API ile doğrulamak; tüm sekiz aşama için uçtan uca gerçek sonuç; geçmiş 4.955 adayın kanıtlı kurtarımı; canlı video decode; gerçek 500/1000/2000 paketler; GitHub dışı kalıcı şifreli arşiv geri yükleme; cihazda İBO testi. Hiçbiri yalnızca yeşil offline CI ile tamamlandı sayılmaz.

## 2 Kasım 2026 — GitHub Actions Verification #3 sonucu
- Workflow: V2 Eight-Stage Runner Verification; commit `c86e3c2242f403de793178b0159e4c364a6dde95`.
- Kullanıcının GitHub Actions ekran görüntüsünde `Verification 3` yeşil başarı simgesi ve 46 saniye süreyle görüntülendi. `Verification 1` ve `2` başarısızdı. Sayısal run ID, job detayları ve artifact içerikleri API üzerinden doğrulanamadı; burada uydurulmadı.
- Bu doğrulama çevrimdışı regresyon/yerel FFmpeg kontrolüdür; canlı IPTV yayın taraması, gerçek 500/1000/2000 paket üretimi ve cihazda IBO oynatma kanıtı değildir.
- Ana İBO playlisti, main ve PR #9 değiştirilmedi.

## 2 Kasım 2026 — kalıcı GitHub Actions runner doğrulaması
- `6bf73292d496d4afe5238bd4a31f1b96f8f31c12`: `.github/workflows/v2-eight-stage-verification.yml` eklendi. Geliştirme dalına push ve workflow_dispatch ile tetiklenir. Runner `ubuntu-24.04`, Python `3.12.7`, cryptography `44.0.2`; ayrı job'da FFmpeg paket sürümü sabitlenmiştir. checkout, korunan playlist SHA-256, Python compile, altı regresyon modülü, FFmpeg yerel gerçek kare ve audio-only negatif kontrolü bulunur. Loglar başarısızlıkta da artifact olarak yüklenir.
- GitHub bağlantısındaki commit-workflow sorgusu yalnızca pull_request tetikli koşuları getiriyor; bu commit için boş liste döndü. Dolayısıyla push-run ID, test sonucu ve job logu **doğrulanmadı**. Bu workflow canlı yayın doğrulaması yapmaz ve sekiz aşamanın tamamlandığı anlamına gelmez.
- Sonraki işlem: Actions UI/API ile push run ID bul, job loglarını ve artifacts incele; başarısız kod/runner sürümünü düzelt. Ana playlist, main ve PR #9 değiştirilmedi.

## 2 Kasım 2026 — sekiz aşamalı talimat, Aşama 1 ilerlemesi
- `e019759d9a7db1a6289450700069084bbeaff9b7`: Master Engine korunan playlist SHA-256 özetini kaynak indirme başlamadan önce alıyor; eksik kaynak taramasında yeni M3U paketi yayınlamıyor ve rapordaki batch_count sıfır kalıyor. Şifreli envanter ve rapor korunuyor.
- GitHub bağlı dosya okuma/yazma erişimi çalıştı; doğrudan git klonlama `Could not resolve host: github.com` nedeniyle başarısız. Bu oturumda repo Python testleri ve canlı medya taraması çalıştırılamadı; commit testten geçmiş veya Aşama 1 tamamlanmış sayılmıyor.
- Devam: çalışma dalında kodu bağımsız Python ortamında test et, özellikle `test_master_engine.py` ve `test_real_ibo_scan.py`; sonra Aşama 2 kaynak hata raporları. PR #9 ve main değişmedi, ana playlist değiştirilmedi.

## 2 Kasım 2026 — eksik kaynak durumu ve regresyon güvencesi
- `8fb8bf58bf0ab44b1bf7450ac1666ed7d5e747ef`: `v2/real_ibo_scan.py` rapor durumu, devam notuyla tutarlı olacak şekilde `PARTIAL_SOURCE_FETCH` yapıldı; erişilemeyen kaynakta mevcut çıktı dosyası üzerine yazılmadan hata çıkışı korunuyor. Erişilemeyen ikinci kontrol bloğu kaldırıldı.
- `85638a21970e9c1c30203a29ba7eb86581593f4e`: `v2/test_real_ibo_scan.py` eksik kaynak senaryosunda önceki paket baytlarının korunmasını, rapor durumunu ve ana listenin değiştirilmemesini sınayan regresyon testi eklendi.
- Bu oturumda test çalıştırma veya Actions başarı sonucu doğrulanmadı. Canlı tarama ve medya decode yapılmadı. PR #9 birleştirilmedi; ana playlist değiştirilmedi.

## 2 Kasım 2026 — main üzerindeki #3 scan hata görüntüsü ve paket koruması
- Kullanıcı ekran görüntüsü: `V2 Gerçek IPTV Tarama ve İBO Paketleri #3`, main `d9d80f2`, pull_request tetikleyicisi, scan job 53m18s, workflow 53m32s, `Incomplete source fetch or source count...`, exit 1. Bu, çalışma dalının Actions sonucu değildir; run ID ekran görüntüsünde görünmüyor.
- `836498371324c7aade8cecd877c1f0f1c2202144`: çalışma dalı `v2/real_ibo_scan.py` eksik kaynakta `PARTIAL_SOURCE_FETCH` ve `source_coverage_complete=false` raporlar, mevcut başarılı paketi değiştirmeden hata ile çıkar.
- Bu değişiklik henüz GitHub Actions veya Python testleriyle doğrulanmadı. Ana İBO playlist'e dokunulmadı, PR #9 birleştirilmedi.

## 2 Kasım 2026 — audio-only yanlış video doğrulaması düzeltmesi
- `faae859e70c94fb0a2a317022cae0e8457452279`: FFmpeg `framemd5` çıktı satırını video karesi saymak için `#media_type 0: video` şartı eklendi; audio-only yanlış pozitif engellendi.
- `1c95d7fd24d803d95d9d4c45a3d42b4e4f5e4791`: `v2/test_media_decode.py` içine audio-only regresyon testi eklendi ve geçerli video test verisi güncellendi.
- Yerel `python -m unittest -v test_media_decode`: 6 test başarılı (gerçek test komutu çalıştırıldı; mock subprocess birim testleri). Yerel FFmpeg lavfi testsrc video kare üretimi: exit 0, 1 framemd5 satırı. Canlı internet erişimi yok, canlı yayın test sonucu yok; Actions run ID doğrulanmadı.
- Ana playlist değiştirilmedi, PR #9 birleştirilmedi.

## 2 Kasım 2026 — FFmpeg gerçek kare doğrulaması entegrasyonu
- `586c9e1933609d58b0b17cd4fa8856ab34dfb9ea`: `v2/media_decode.py` URL doğrulaması, zaman aşımı ve FFmpeg framemd5 çıktı kontrolü ile gerçek çözümlenen video karesini şart koşar.
- `3a460f7ce793c8351212fcff0c0e9916aaca5874`: Master Engine manifest erişiminden sonra `media_checker` üzerinden kare doğrulamasını bağlar; cihaz doğrulaması ayrı kalır.
- `27345e294440737a51d9622884fae481ece8edbd`, `129aa8b1044bfff0099536e6047612ed872997b5`, `bcf6d844882479169fe4b4363f26e1e4fb49f4eb`: yeni decode testleri, iki CI job'ına test ekleme ve Master Engine geçiş testleri.
- Yerel test: `python -m unittest -v test_media_decode` — 5 test, 5 başarılı (subprocess sonuçları taklit edilmiştir; canlı medya testi değildir). GitHub Actions run ID bu oturumda doğrulanmadı; tüm depo testleri çalıştırılmadı. Ana playlist'e dokunulmadı, PR #9 birleştirilmedi.

## 2 Kasım 2026 — Master Engine SHA-256 tarama koruması
- `7d0e1414be8ac34c96111e4e2537e3a9f6c3ac65`: `v2/master_engine.py` korunan ana playlist'in tarama öncesi/sonrası SHA-256 değerlerini karşılaştırır, değişiklikte hata verir ve eşit özetleri rapora ekler. Playlist dosyası commit'te değiştirilmedi.
- Bu oturumda Actions run ID ve yürütülmüş Python test sonucu doğrulanmadı; gerçek tarama başlatılmadığından çalışma zamanı SHA-256 değeri yok. Aşama 1 henüz tamamlanmadı.

## 2 Kasım 2026 — boş aday raporunun korunması
- `a8efc12c07e92e9f965061f406623ee78a5e0019`: `v2/master_engine.py` sıfır adayda `NO_CANDIDATES` durumunu rapora kaydedip başarısız çıkıyor; sahte başarılı paket üretilmiyor.
- GitHub Actions run ID ve gerçek test sonucu bu oturumda doğrulanmadı. Korunan playlist'e yazılmadı; SHA-256 karşılaştırması henüz yapılmadı. Aşama 1 tamamlandı iddiası yok.

## 2 Kasım 2026 — sıfır medya doğrulaması başarı kapısı
- `57674c9d84c6b87dffacd6e706af43b2b0aea864`: `v2/master_engine.py` gerçek medya decode sayısı sıfır olduğunda `NO_MEDIA_DECODED` raporu üretir ve başarısız çıkar; şifreli arşiv ve rapor kalır, doğrulanmamış yayın paketi üretilmez.
- GitHub CLI bu yürütme ortamında kurulu değil (`gh: command not found`); git remote erişimi DNS nedeniyle engellendi (`Could not resolve host: github.com`). Push Actions run ID bu ortamda doğrulanamadı. Python regresyon testleri bu oturumda çalıştırılamadı; CI başarı iddiası yok.
- Korunan ana playlist'e yazılmadı; öncesi/sonrası SHA-256 ölçümü gerçekleştirilmedi. Aşama 1 tamamlanmış sayılmıyor.

## 2 Kasım 2026 — Actions test bağımlılığı ve SHA-256 koruması
- `0fea00650e8f12e9d94e22e6af2d510fcb53b562`: `.github/workflows/v2-master-engine.yml` offline-tests job'ına `cryptography>=42,<47` kurulumu ve korunan ana playlist'in HEAD/working-tree SHA-256 karşılaştırması eklendi. Playlist dosyası değiştirilmedi.
- Bu kontrol için Actions run ID ve job sonucu henüz alınamadı; commit bazlı PR-event filtreli run API'si ve combined status boş döndü. CI başarılı ilan edilmedi.

## 2 Kasım 2026 — Master Engine regresyon güvencesi
- `83df978abf42479e401903c2ada4f83a99e96407`: `v2/test_master_engine.py` manifest erişiminin medya decode kanıtı sayılmadığını test eden koşulla güncellendi.
- GitHub Actions koşusunun gerçek run ID/job sonucu henüz alınamadı; PR-event filtreli run sorgusu ve commit status sorgusu boş döndü. Testin çalıştığı/yeşil olduğu iddia edilmiyor.
- Ana playlist değiştirilmedi; SHA-256 öncesi/sonrası ölçümü henüz yapılmadı.

## 2 Kasım 2026 — Master Engine manifest/medya ayrımı
- `22f36818d694c92563ec187bc5aaec9d503800c4`: `v2/master_engine.py` medya çözümlemesi kanıtlanmayan manifest adaylarının doğrulanmış paketlere yazılmasını engeller; `media_decoded` alanı varsayılan false, raporda manifest ve medya sayıları ayrı.
- Bu commit gerçek ffprobe/ffmpeg decode entegrasyonu değildir. CI run ID, job sonucu ve regresyon test sonucu henüz doğrulanmadı. Gerçek paket üretilmedi; korunan ana playlist'e yazılmadı. SHA-256 karşılaştırması yapılmadı.

## 2 Kasım 2026 — tarayıcı salt-okunur güvenlik düzeltmesi
- Çalışma dalı `madsc/v2-discovery-bulk-20261031`: `a5044be1f8bad5e2e3bdf17747ed19b4e5647105` commit'i `v2/real_ibo_scan.py` içindeki `--append-live` seçeneğini ve korunan ana playlist'e yazan kodu kaldırdı.
- Ana İBO playlist dosyasına bu commit'te dokunulmadı. GitHub Actions push koşusu sonucu henüz doğrulanmadı; commit bazlı PR filtreli API boş döndü, bu başarı/başarısızlık kanıtı değildir.
- Gerçek medya decode, 500'lük paketlerin doğrulanması, kalıcı şifreli arşiv ve korunan dosyanın SHA-256 öncesi/sonrası karşılaştırması henüz doğrulanmadı.

## 2 Kasım 2026 — toplu V2 dal/CI/tarama denetimi
- GitHub karşılaştırması: `main` ile `madsc/v2-discovery-bulk-20261031` ayrışmış; karşılaştırma anında çalışma dalı 284 commit ileride ve 210 commit geride. Otomatik birleştirme yapılmadı.
- Çalışma dalındaki `.github/workflows/ibo-real-scan.yml` manuel tetiklenir ve `main` dalındaki güncel tarayıcı kodunu checkout eder. Böylece workflow dalı ile çalıştırılan kod dalı **farklıdır**; CI sonuçları buna göre yorumlanmalıdır.
- Workflow başarı kapıları, sıfır kanal, eksik kaynak, arşiv geri yükleme ve paket raporu kontrolleriyle güçlendirildi. Son düzeltme 858def4: doğrulama başarısızken paket yayınlanmaz, Actions çıktıları 30 gün saklanır. 30 günlük Actions artifact depolaması **kalıcı harici yedek değildir**.
- Bu çalışma sırasında gerçek internet taraması ve yeni Actions koşusu başlatılmadı; mevcut CI başarısı doğrulanmadı. Ana playlist/YEDEKLER/EPG/favoriler değiştirilmedi; PR #9 birleştirilmedi.
- Açık işler: güncel CI koşusunu doğrulamak; geçmiş #60 gerçek URL/4.955 aday kurtarmasını kanıtlamak; şifreli envanteri GitHub dışı kalıcı depoya kopyalayıp geri yüklemeyi doğrulamak; dalların kontrollü ve korunan dosyalara dokunmayan uyum planını uygulamak.

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


## 31 Ekim 2026 — GitHub keşif kapsamı dürüstlüğü
- Son doğrulanmış toplu CI #41212925415 SUCCESS.
- `github_source_discovery.py`: `MAX_REPOS`, `MAX_FILES`, GitHub API `tree.truncated` durumları artık `limits_hit` ve `coverage_status=PARTIAL_LIMITS` olarak raporlanıyor. Limitler nedeniyle eksik taramaya `COMPLETE_QUERIES` denmeyecek.
- `test_github_partial_discovery.py` içinde repo limiti ve kısaltılmış tree testleri eklendi; mevcut toplu CI içinde çalışır.
- Henüz gerçek tam ağ taraması, bağımsız şifreli yedek, oynatma testleri yapılmadı. Ana IBO, YEDEKLER, YENİLER, FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — Kaynak kaybı raporu eksikliği kontrolü
- `source_loss_audit.py` eski veya yeni `source_audit` boşken `NO_LARGE_REGRESSION` döndürmez; `MISSING_SOURCE_AUDIT` / `REVIEW_REQUIRED` üretir.
- Eski ve yeni sayıların tip ve negatif değer doğrulaması eksik audit koşulunda da çalışır.
- `test_source_loss_audit.py` iki yeni regresyon vakası ile güncellendi; tek toplu CI içinde çalışır.
- Gerçek kaynak ağ taraması ve bağımsız arşiv yedeklemesi tamamlanmış değildir. Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor, PR #9 merge edilmedi.


## 31 Ekim 2026 — Şifreli arşiv kabul kanıtı dosya izinleri
- `archive_acceptance_gate.py` bağımsız yedekleme/geri yükleme kanıtı JSON dosyasını da 0600 (owner-only) zorunlu kılar; herkesçe okunabilir dosyayı reddeder. `backup_location` tipi doğrulanır.
- `test_archive_acceptance_gate.py` mevcut başarılı kanıt testlerini özel dosya izniyle güncelledi ve 0644 reddi testini ekledi.
- Bu kod bağımsız yedeklemeyi oluşturmaz; bağımsız kalıcı depolama ve gerçek restore kanıtı hâlâ gerekir. Son CI sonucunu kontrol et. Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor, PR #9 merge edilmedi.


## 31 Ekim 2026 — CI #41213784417 düzeltmesi
- Gerçek hata: `test_restore_evidence_safety.py::test_reject_world_readable_restored_archive`, fixture restored dosyasını 0600 yaptıktan sonra evidence JSON dosyasını 0644 bıraktı. Yeni güvenlik kontrolü doğru şekilde reddetti.
- Test fixture her iki dosyayı da 0600 yapacak şekilde düzeltildi. Şifreli arşiv güvenlik şartı gevşetilmedi.
- Güncel toplu CI sonucu henüz doğrulanmadı. Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor, PR #9 merge edilmedi.


## 31 Ekim 2026 — Son CI kontrolü ve toplu tarama durum ayrımı
- CI #41214498144 SUCCESS (önceki kanıt dosya izinleri test hatası giderildi).
- `run_all_discovery.py` altı aşamanın bitmesinin tam kapsama veya oynatma doğrulaması olmadığını açıkça raporlar. Kısmi kapsam için her alt rapor incelenmelidir.
- Yeni resmî kaynakların ve gerçek kanal taramasının tamamlandığı iddia edilmez. Bağımsız kalıcı şifreli arşiv/restore kanıtı hâlâ gerçek taramanın önkoşuludur.
- Ana IBO, YEDEKLER, YENİLER, FAVORİLER korunuyor; PR #9 merge edilmedi.


## 31 Ekim 2026 — Forge sayfalama kaybı kontrolü
- CI #41215502742 SUCCESS.
- GitLab/Codeberg keşfi proje arama sayfa sınırına ve GitLab tree sayfa sınırına ulaşınca `limits_hit` ile `PARTIAL_LIMITS` raporlar; Codeberg truncated tree de aynı şekilde.
- `test_partial_source_coverage.py` GitLab limit senaryosuyla genişletildi; tek toplu CI altında çalışır.
- Sayfalama otomatik devam ettirilmedi: kısmi kapsam görünür kılındı, tam keşif iddiası yok. Gerçek tarama ve bağımsız şifreli arşiv doğrulaması bekliyor. Ana IBO/YEDEKLER/YENİLER/FAVORİLER değişmedi; PR #9 merge edilmedi.


## 31 Ekim 2026 — GitLab kaynak taraması sayfalama iyileştirmesi
- Son doğrulanmış CI #41215667614 SUCCESS.
- GitLab repository tree API ilk 100 dosyaya ulaştığında artık 2. ve gerekirse 3. sayfayı da okur. Üçüncü sayfa doluysa `GITLAB_TREE_PAGE_LIMIT` ile kısmi kapsam raporlanır.
- `test_partial_source_coverage.py` ikinci sayfadaki M3U kaynağının bulunduğunu doğrulayan çevrimdışı testle genişletildi.
- Ana IBO/YEDEKLER/YENİLER/FAVORİLER korunuyor; PR #9 merge edilmedi. Gerçek tam tarama ve bağımsız şifreli yedek hâlâ tamamlanmadı.


## 31 Ekim 2026 — Görev 1: bütünlük entegrasyonu ve ağ dayanıklılığı (kısmi)
- `v2/source_integrity.py` (9d3cf80) ve testleri (c593455) oluşturuldu. `discover.py` ana akışına `verify()` entegrasyonu commit 18f65813 ile eklendi; ek bağlantı testi 90f0fd90.
- Geçici ağ hatalarında sınırlı yeniden deneme, kalıcı HTTP 4xx ve geçersiz içerikte erken durma, kaynak başına güvenli hata türü/deneme sayısı raporu commit efd72262 ile eklendi. Timeout test fixture'ı commit 692ae0f6.
- CI: efd72262 için sıralı hazırlık #267 (run 41239473741) CANCELLED; 692ae0f6 için #268 (run 41239483328) SUCCESS: compile, protect, discovery-tests, safety dört iş de başarılı.
- Bu CI, gerçek IPTV-org/Free-TV/onaylı M3U uçtan uca ağ taramasını, bütün kaynakların erişimini, sıfır aday kaybını veya Worldwide Discovery #80 kök nedeninin giderildiğini kanıtlamaz. #80 hata logu henüz incelenmedi. Ayrıca #268 adım listesinde `test_source_integrity.py` adı görülmediğinden bu özel testin CI'da yürütüldüğü iddia edilmez.
- Görev 1 durumu: KISMEN TAMAMLANDI / GERÇEK TARAMA DOĞRULAMASI BEKLİYOR. Görev 2'ye kod değişikliğiyle geçilmedi; yalnızca mimari hazırlık yapılabilir.
- Koruma: ana IBO playlist'i, YEDEKLER'deki iki kanal, YENİLER, FAVORİLER, cihaz favorileri, logo/EPG/kategoriler değiştirilmedi; main ve PR #9 birleştirilmedi.


## 2 Kasım 2026 — Toplu çevrimdışı kurtarma entegrasyonu
- `v2/historical_url_recovery.py` ve `v2/test_historical_url_recovery.py` çalışma dalına eklendi (daedaba0, ea7d1fa).
- CI toplu test döngüsüne kurtarma testi ve değişiklik tetikleyicisi eklendi (75dd459). Çevrimdışı çalışır; gerçek ağ taraması başlatmaz.
- Kurtarma ancak eski raporlarda gerçek HTTP(S) URL mevcutsa aday üretir; anonim ID'lerden adres uydurmaz; mevcut URL'leri ve tekrarları çıkarır, kaynak/metadata korur. Eski #60 arşivinin gerçek URL kayıtları henüz temin edilmediği için 4.955 adayın kurtarıldığı iddia edilmez.
- CI'nın yeni commit sonrası yeşil sonucu henüz doğrulanmadı. Harici bağımsız şifreli yedek henüz doğrulanmadı.
- Ana IBO, YEDEKLER, YENİLER, FAVORİLER ve yabancı arşiv değişmedi; PR #9 birleştirilmedi.


## 2 Kasım 2026 — Master Engine ilk bütünleşik uygulama
- `v2/master_engine.py` commit 9192b00: mevcut discover.py ayrıştırma/kaynak indirme, historical_url_recovery.py, real_ibo_scan.py HLS manifest kontrolü ve encrypted_archive.py birlikte çağrılır. Ana İBO salt okunur; URL tekilleştirme ve kaynak geçmişi tutulur; cihaz testi yapılmış iddiası yok; en fazla 500 kayıtlık ayrı M3U8 çıktısı.
- `v2/test_master_engine.py` commit 549ca72: offline entegrasyon regresyonları eklendi.
- `.github/workflows/v2-master-engine.yml` commit 528941a: manuel tetiklenen gerçek ağ workflow'u, şifreleme anahtarı GitHub Secret, çıktı artifact'i 30 gün saklanır. Bu artifact bağımsız kalıcı arşiv değildir.
- Durum: AŞAMA 1 KOD ENTEGRASYONU İLK SÜRÜM; gerçek CI başarı sonucu ve uçtan uca test henüz doğrulanmadı. Kaynakların tamamı erişilebilir kabul edilemez; eksik kaynaklar raporlanır. Segment oynatımı, yönlendirme güvenliği, sağlam dil/ülke sınıflandırması, kalıcı bağımsız arşiv ve 4.955 gerçek URL kurtarma açık işlerdir.
- Ana İBO/YEDEKLER/YENİLER/FAVORİLER değişmedi; PR #9 merge edilmedi.


## 2 Kasım 2026 — Master Engine Actions yeşil testler ve devam kaydı
- Kullanıcı GitHub Actions ekran görüntülerinde V2 Master Engine 1–6 çalışmalarının yeşil olduğunu doğruladı; sonraki `f8d88d1` ve `21047d7` testlerini ve `da9c7b3` testini de yeşil bildirdi. GitHub connector commit-workflow sorgusu boş sonuç döndürdüğünden run ID/log bağımsız doğrulanamadı; bunu test başarısızlığı sayma.
- Commitler: `877f473` push otomatik CI; `032b0ce` push dosya filtresinin kaldırılması; `3819238` M3U kaynak doğrulaması; `6676436` onaylı GitHub/forge envanterleri; `e4f5785` entegrasyon girişinde geçersiz M3U reddi; `210b071` regresyon; `f8d88d1` stream checker istisna yalıtımı; `21047d7` regresyon; `da9c7b3` sıfır adayda başarılı çıkışı engelleme.
- Yeşil olanlar otomatik çevrimdışı regresyonlardır; gerçek kaynak taraması, segment/video/audio oynatımı, 4.955 URL kurtarma, bağımsız kalıcı şifreli arşiv, İBO cihaz oynatma doğrulaması tamamlandı denemez.
- Sonraki işlemler çalışma dalında; PR #9 kesinlikle merge edilmez. Ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER, YENİLER, FAVORİLER ve cihaz favorilerine dokunulmaz. Eski repo kullanılmaz.


## 2 Kasım 2026 — Actions izleme erişimi kök neden ve otomasyon
- GitHub connector `fetch_commit_workflow_runs` yalnızca pull_request tetiklemeli run'ları döndürüyor; Master Engine push tetiklemeli olduğu için sonuç boş. Boş yanıt, testin çalışmadığını göstermez.
- Alternatif doğrudan `api.github.com` erişimi bu oturumun container'ında DNS çözümleme hatası verdi; web üzerinden de API okunamadı. Bu yüzden son 10 gerçek run ID ve durumunu sohbet içinde doğrulamak mümkün olmadı.
- `v2/actions_monitor.py` GitHub Actions içinde `github.token` ve `actions: read` izniyle son 10 Master Engine run ID, SHA, queued/in_progress/completed durumu, conclusion, URL ve başarısız job/step özetlerini `actions-last10.json` dosyasına çıkarır. Gizli token'ı rapora yazmaz.
- `.github/workflows/v2-actions-monitor.yml` push, manual ve cron tetiklemeli izleme workflow'u; artifact saklama 30 gün. GitHub cron tetikleyicileri varsayılan dalda tanımlı workflow için çalışır; bu dal üzerindeki cron'un gerçekten tetiklendiği ayrıca doğrulanmalıdır.
- `v2/test_actions_monitor.py` çevrimdışı durum/başarısız step regresyonu; Master Engine ve monitor CI akışlarına bağlandı. CI yeşil ve gerçek run ID sonucu henüz doğrulanmadı; kullanıcıdan ekran görüntüsü isteme.
- Koruma: Ana İBO/YEDEKLER/YENİLER/FAVORİLER değişmedi; PR #9 merge edilmedi.


## 2 Kasım 2026 — Actions Monitor 9 kırmızı, düzeltme
- Kullanıcının GitHub Actions ekran görüntüsü: Monitor 9 (`c6b34c4`) failure (10 sn); Monitor 8 (`c83532c`) success (10 sn); Monitor 7 (`8463872`) success (21 sn). Ekran görüntüsü job/step logu göstermiyor.
- Olası regresyon: repository-wide `/actions/runs?per_page=10` sayfası diğer workflow çalışmalarıyla dolabilir; sadece Master Engine filtrelenince sıfır kayıt ve bilerek hata oluşur. `f3c569f` ile workflow-scoped API sorgusuna geri dönüldü; `9127251` ile test güncellendi. Gerçek hata logu/run ID elde edilmediği için kök neden kesin doğrulanmış değildir.
- Yeni commitlerin yeşil durumu henüz doğrulanmadı; ana İBO değişmedi, PR #9 merge edilmedi.

## 3 Kasım 2026 — Aşama 2 kaynak adaptörleri: kod ve toplu CI doğrulaması tamamlandı

- Çalışma dalı: `madsc/v2-discovery-bulk-20261031`. Ana IBO `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, `main`, eski depo ve PR #9 değiştirilmedi.
- GitLab/Codeberg normalize etme, platform adresi denetimi ve tek tarayıcı kullanımı düzenlendi. GitLab ağacında yeni API `pagination=keyset&page_token=...` desteklendi, eski yanıtlarda numaralı sayfa uyumluluğu korundu. Hatalı GitLab/Codeberg JSON yanıtları başarı diye gösterilmiyor.
- GitHub/Gist arama ilk sayfa, repo başına dosya ve Gist sayfa sınırları `limits_hit` içinde raporlanıyor. Güvenilmeyen repo adları/path girdileri ve geçersiz Gist metadata öğeleri eleniyor. Onaysız kaynağın otomatik ana listeye aktarılması yasak.
- Kod commitleri: `d87d18eb`, `5eb5916e`, `edf98a13`, `1a062ed0`, `a0f6c5e6`, son kod commit `172b08a1`.
- `v2/source_adapter_service_health.py` altı gerçek kaynak/API servisinin yalnızca erişimini/sözdizimini sınar: IPTV-org TR, Free-TV, GitHub repo API, genel Gist API, GitLab proje API, Codeberg repo API. Kanal stream URL taraması, oynatma doğrulaması, ana playlist yazımı YOKTUR.
- GitHub Actions `V2 Source Adapter Bulk Validation` run **41559468171 SUCCESS**: bir seferde **62 ilgili regresyon testi OK**, altı gerçek kaynak/API kontrolü **6/6 AVAILABLE**, rapor artifact `v2-source-service-health-41559468171`.
- Son kod commit `172b08a1` için ayrıca `V2 Eight-Stage Runner Verification` run **41559468062 SUCCESS**: **194 unittest OK**, **14 koruma testi OK**, FFmpeg test işi SUCCESS, korunan playlist SHA256 `7e62b0beec0b928ed30ac86827077f2dd6d7e739f42a573ce849c7d64f5e8eb4`.
- Aynı commit: `V2 Master Engine` **41559468053 SUCCESS** (offline-tests başarılı, gerçek master görevi SKIPPED); `Current Scanner Offline Gate` **41559468066 SUCCESS**; `Actions Status Monitor` **41559468100 SUCCESS**.
- **Aşama 2 kod entegrasyonu, servis ulaşılabilirliği ve toplu CI doğrulaması bitmiştir.** Bu durum tüm keşif adaylarının, gerçek görüntü/ses dekodunun, şifreli arşiv geri yüklemenin veya IBO Player cihaz oynatmasının başarıyla doğrulandığı anlamına gelmez. Yeni geniş kanal taraması bu aşamada yapılmadı.

## 3 Kasım 2026 — Aşama 3: geçmiş 4.955 aday için koruma ve TR/AZ çakışma önlemi

- Çalışma dalı `madsc/v2-discovery-bulk-20261031`; ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER, YENİLER, FAVORİLER, `main`, eski depo ve PR #9 değiştirilmedi.
- Mevcut `historical_inventory_guard.py` gerçek geçmiş satırlarının tümünü ham şifreli kanıtta saklıyor; yayın URL'si mevcut olan adayları gerçek URL'nin SHA-256 değeriyle tekilleştiriyor; hash-only, başarısız ve adsız kayıtları geçmişten silmiyor. Verilen `--expected-historical-records 4955` sayısı uyuşmazsa hata veriyor; sahte yayın URL'si üretmiyor.
- Yeni commit `bb3defec61be4eda1a63ce97d11f41af0d22a1e6`: aynı URL için tarihî veya yeni kaynakta TR ve AZ çelişkisi varsa **raw geçmişi ve provenance'ı koruyarak** adayın `region_candidate` alanını `UNKNOWN`, kanıtını `CONFLICTING_TR_AZ_EVIDENCE` yapıyor ve `conflicting_tr_az_candidate_urls` sayısını raporluyor. Konuşulan dil doğrulanmış sayılmıyor.
- `v2/test_historical_region_collisions.py` dört regresyon testi içeriyor; `.github/workflows/v2-stage3-historical-inventory.yml` mevcut konu bazlı toplu işine bağlandı.
- GitHub Actions `V2 Stage 3 Historical Inventory Loss Protection` run **41613346076 SUCCESS**: **63 test OK**, şifreli koruma, geçmiş kaynak/kayıp, tekilleştirme, TR/AZ ve hash-only kanıt testleri bir toplu işte yürütüldü.
- Aynı run kanıt raporu açıkça `historical_dataset_present_in_checkout=false`, `historical_4955_real_records_restored=false` raporluyor. Testlerdeki 4.955 kayıt **sentetik test fikstürüdür, gerçek #60 envanteri değildir**. Gerçek 4.955 kayıt kaynağı gelmeden fiilî arşiv kurtarması tamamlandı denemez.
- Tekilleştirme yalnızca aday görünümündedir, orijinal geçmiş satırları silinmez. Kaynak coğrafyası, TVG-ID ve yayın adı **konuşulan Türkçe/Azerice kanıtı değildir**; İBO cihaz testi kullanıcıya aittir.

## 3 Kasım 2026 — Aşama 3: Tarihî kaynak kaybını önleme, tekilleştirme ve Türk/Azeri aday sınıflandırması

- Çalışma dalı `madsc/v2-discovery-bulk-20261031`. Ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER, YENİLER, FAVORİLER, `main` ve eski repo değiştirilmedi. PR #9 birleştirilmedi. İBO Player cihaz testi yapılmadı; kanal keşif taraması başlatılmadı.
- `v2/historical_inventory_guard.py` eklendi: eski JSONL, eski AES-GCM arşivi, SHA-only karşılaştırma CSV'si veya tamlık doğrulanmış oynatma JSON aggregate dosyasından tarihî kayıt alabilir. Her tarihî ham satır (tekrarlar, başarısızlar, hash-only, geçersiz adresli olanlar dahil) korunur; ayrı aday görünümü **gerçek ve birebir aynı URL** üzerinden SHA256 ile tekilleştirilir. Eksik URL'ler hash'ten üretilmez. Mevcut envanter ile kaynak geçmişi birleştirilir; URL/EPG/logo/grup bilgileri özgün kayıtlarla korunur.
- `TR`, `AZ` ve `UNKNOWN` yalnız ülke/TvG ID/isim/grup kanıtına dayalı **aday bölgesi** olarak raporlanır; ses dili kanıtı değildir. Korunan ham satırların tamamı için ayrıca TR/AZ/UNKNOWN sayımı vardır. İBO deneme çıkışına sadece gerçek video decode edilmiş, TR/AZ adayı girebilir; belirsiz tarihî kayıtlar şifreli arşivde kalır.
- `v2/master_engine.py` tarihî ham kaydı şifreli arşivde muhafaza ediyor, kaynak tekrarlarında eski #60 provenansını da koruyor; arşiv restore eşitliği kontrol ediliyor. Yeni güvenli `.enc` çıktı önceki çıktıların üzerine yazılmaz.
- Commitler: `84a85154`, `96f0ed64`, `0959a5aa`, `d126309c`, `6a244ded`, `85746a90`, `6945335b`, `b3be27ea`, `daa91102`, `85655c05`, `5bb9be4d`.
- **Toplu CI doğrulaması:** Son Stage 3 run **41613028982 SUCCESS** (59 ilgili test), Eight-Stage run **41613029196 SUCCESS** (208 genel unittest + 14 koruma testi + FFmpeg). Master Engine offline **41613029001 SUCCESS**, Scanner Offline Gate **41613029036 SUCCESS**; Master Engine canlı tarama adımı `SKIPPED`. Korunan playlist SHA256 `7e62b0beec0b928ed30ac86827077f2dd6d7e739f42a573ce849c7d64f5e8eb4`.
- **Gerçek tarihî veri bulundu:** 28 Ekim 2026 `Kanalları ara — Tek Birleşik Görev` run **40743765437** (#60), `turkish-stream-review` artifact **12844533683**: aday kimlikleri 27.047 (SHA256 URL hash'leri, kaynak/isim/TVG/grup bilgileri); tam video playback aggregate 27.047, `VIDEO_DECODED` 11.860. Aynı run `unified-source-candidates` artifact **12841145691** aynı 27.047 hash'i içerir.
- Son karşılaştırma: 2 Kasım 2026 Worldwide Discovery run **41549488708**, artifact **13189578938**: 8.077 benzersiz hash. Eski ve yeni arasında **5.626 eşleşme**, **21.421 eski hash son aday raporunda yok**; önceki video decode edilenlerden **11.310 hash** son aday raporunda yok. Bu rapor farkı, yayınların artık çalışmadığının veya adresin yeniden kurulabildiğinin kanıtı değildir.
- Gerçek #60 metadata içeren 27.047 adet SHA-only satır, çalışan ortamda `V2_STAGE3_REAL_RUN60_HISTORICAL_27047.jsonl` olarak çıkarıldı. Aynı satırlar AES-256-GCM ile `V2_STAGE3_REAL_RUN60_HASH_ONLY.enc` dosyasında şifrelendi ve geri açılarak **27.047/27.047 eşitlik testi başarılı**. Şifre anahtarı ayrı yerel dosyaya kaydedildi, **GitHub'a veya bu not içine konmadı**. Yerel denetim raporu `V2_STAGE3_REAL_HISTORICAL_AUDIT.json`. Bu dosyalar sohbet çıktısıdır, GitHub deposuna veya bağımsız kalıcı yedeğe yüklenmiş sayılmaz.
- Bu gerçek kayıtların metadata kanıtına göre **1.491 TR**, **73 AZ**, **25.483 belirsiz** aday etiketi bulunuyor; ses dili doğrulanmadı. Hash-only arşivde doğrudan stream URL yoktur. Bu yüzden **kullanıcının sözünü ettiği spesifik 4.955 kayıp aday altkümesi** eldeki karşılaştırma ile bağımsız tanımlanamadı; `4.955/4.955 canlı URL kurtarıldı` demek yasaktır. Gerçek koruma, kaynak hash kanıtının ve orijinal 27.047 kaydın korunmasıdır; URL'lerin gerçek kurtarılması ayrı koşuldur.

### 3 Kasım 2026 — DÜZELTME: Gerçek 4.955 tarihî adayın orijinal #60–#72 karşılaştırma verisi bulundu

- Önceki nottaki “spesifik 4.955 altküme bağımsız tanımlanamadı” tespiti **artık geçerli değildir**. GitHub Actions run **40968303248** artifact **12938054572** (`historical-60-vs-72-recovery`) açıldı: `historical-decoded-not-retested.csv` tam **4.955 satır** ve **4.955 tekil URL SHA256 kimliği**, `historical-comparison.json` karşılaştırma özeti.
- Veriler hem gerçek #60 run **40743765437**, artifact **12844533683** (27.047 test / 11.860 VIDEO_DECODED), hem de gerçek #72 run **40948768782**, artifact **12936474481** (13.518 test / 7.254 VIDEO_DECODED) ile bağımsız denetlendi. Eski/yeni ortak 13.136, yalnızca eski 13.911, yalnızca yeni 382. **4.955 CSV kimliği = #60 VIDEO_DECODED kimlikleri eksi #72'de test edilmiş tüm kimlikler**, birebir küme eşitliği sağlandı.
- En güncel 8.077 adaylık Worldwide run **41549488708** hash raporu ile bu 4.955 gerçek kimlik karşılaştırıldı: **100 yeniden görülen hash**, **4.855 son aday raporunda görülmeyen hash**. Bunlar **gerçek yeniden oynatma veya gerçek URL kurtarma kanıtı değildir**.
- Gerçek 4.955 satırın özgün #60 kaynak, ad, TVG-ID, grup, logo metadata'sı ve #60/#72 karşılaştırma video kanıtı hash temelinde birleştirildi; `V2_STAGE3_REAL_4955_HISTORICAL.jsonl` üretildi. URL uydurulmadı, token-bearing stream URL bulunmuyor.
- Gerçek 4.955 satır `V2_STAGE3_REAL_4955_HISTORICAL.enc` içinde **AES-256-GCM ile şifrelendi** ve decrypt/restore sonrası **4.955/4.955 özgün kayıt birebir eşit** bulundu. `V2_STAGE3_REAL_4955_AUDIT.json` ile kriptografik SHA256 ve orijinal artifact kimlikleri kaydedildi. Anahtar `V2_STAGE3_REAL_4955_ARCHIVE_KEY_HEX.txt` olarak ayrı üretildi; **GitHub'a veya bu nota yazılmadı**. Bu dosyalar kullanıcıya sohbet ortamında verildi, otomatik olarak bağımsız kalıcı depoya aktarılmış sayılmaz.
- Konservatif isim/TVG/grup kanıtına göre gerçek 4.955 satırda **50 TR adayı, 1 AZ adayı, 4.904 UNKNOWN** bulunuyor. “Türkçe/Azerice sesli yayın” kanıtı değildir; belirsiz ve başarısız adaylar ham geçmişten silinmedi. Tekil URL SHA-256 bazında tekrar olmaması bağımsız doğrulandı.
- **Aşama 3 gerçek tarihî kimlik koruması, 4.955/4.955 doğrulaması, tekilleştirme ve metadata sınıflandırması tamamlandı.** Ancak bu SHA-only kaynaklardan eski 4.955 URL adresi geri çıkarılamaz; yeniden gerçek URL bulma, güncel AV decode ve İBO cihaz oynatma doğrulaması ayrı işlerdir.

## 3 Kasım 2026 — Aşama 3 gerçek #60/#72 4.955 tarihî kimlik kurtarma kanıtı

- Bu kez **gerçek GitHub Actions arşivleri doğrudan alınıp karşılaştırıldı**: #60 run `40743765437` ve #72 run `40948768782`, her ikisinde `turkish-stream-review` artifact'i mevcut (Kasım 2026 itibarıyla süresi dolmamış).
- #60 tamamlanmış oynatma agregası: **27.047 benzersiz SHA-256 yayın kimliği**, **11.860 VIDEO_DECODED**. #72: **13.518 benzersiz kimlik**. #60'ta olup #72'de bulunmayan: **13.911** kimlik; bunların #60'ta VIDEO_DECODED olanı tam **4.955**. 4.955 kimlik tekil (tekrar 0). Bunlar **gerçek tarama kanıtıdır**, sentetik test verisi değildir.
- #60 `candidates.json` içindeki **27.047** aday SHA-256'sı ile #60 oynatma kimlikleri bire bir eşleşti ve kesilmemiş envanter kanıtı doğrulandı.
- 4.955 korunan gerçek anonim kimliğin metadata temelli **bölge aday sınıflandırması**: **TR 50, AZ 1, UNKNOWN 4.904**. Konuşulan dil veya güncel yayın erişimi kanıtı **değildir**. Çoğu kaynak için güvenilir bölge metadata kanıtı yoktur; zorla TR/AZ sayılmaz.
- İndeks SHA-256 parmak izi: `e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83`. Kaynak URL'leri hiçbir rapora yazılmadı; **4.955 URL geri getirildi iddiası YOK**, yalnızca 4.955 gerçek hash kimliği korundu.
- Kod commit `4263b003820d3e46b3fbddb746ea416450e924e3`: `v2/real_historical_stage3.py` #60/#72 tamlık ve SHA doğrulamasını yapar; hash-only envanter üretir. `v2/test_real_historical_stage3.py` toplu regresyon paketi ve `.github/workflows/v2-stage3-real-history.yml` orijinal arşivleri indiren ve **kanal taraması yapmayan** CI işidir.
- Kod commit `ece6de8e0e887eb0bc6e7b0afcb1fbfc3939224f`: hash-only kayıtlarda önceki bölge-aday metadata kanıtını `historical_inventory_guard.classify` korur; yeni test ve gerçek 4.955 kayıt üzerinde AES-GCM şifreleme/geri yükleme kontrolü eklendi.
- **GitHub Actions gerçek veri toplu çalışma `41615219947` SUCCESS**: **65 regresyon testi OK**, 4.955 gerçek hash kayıt korundu, gerçek sayılar ve TR/AZ kanıtları doğrulandı, **AES-GCM ephemeral anahtarla 4.955 kaydı tamamen encrypt/restore karşılaştırması başarılı**, artefakt `stage3-real-history-4955-41615219947` (artifact ID `13220573447`). Bu ephemeral CI anahtarı kalıcı güvenli yedek anahtarı değildir.
- Ayrıca Stage 3 genel toplu `41615219948` SUCCESS; Master Engine offline `41615219968` SUCCESS; Scanner Offline Gate `41615219981` SUCCESS; Status Monitor `41615219932` SUCCESS.
- Yerel çalışma ortamında **orijinal 4.955 hash-only gerçek kimlik** için ayrı AES-GCM arşivi oluşturuldu ve şifresi ayrı dosyada tutularak tüm kayıtlar decrypt/restore ile doğrulandı. Kullanıcıya her iki dosya ve anonim özet sunuldu; GitHub'a gizli anahtar ya da açık yayın URL'si konmadı.
- Ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER, YENİLER, FAVORİLER, `main`, PR #9, eski depo değiştirilmedi.
- Sınır: Orijinal #60/#72 kamuya açık oynatma agregalarında URL değil SHA-256 var. **4.955 oynatılabilir adresi yalnızca SHA'dan yeniden üretmek mümkün değildir**. Bunları güncel gerçek URL ile yeniden eşleştirmek, sonra kaynak/medya/device doğrulamak farklı aşamadır.

## 3 Kasım 2026 — Aşama 3: gerçek 4.955 kimliğin kalıcı korunması ve mevcut M3U URL eşleştirme kanıtı

- GitHub Actions gerçek geçmiş tarama kaynakları: #60 `40743765437`, #72 `40948768782`. Gerçek #60'da 27.047 benzersiz URL SHA-256, 11.860 VIDEO_DECODED; #72'de 13.518 SHA-256. #60 VIDEO_DECODED iken #72'de kaybolan **4.955 benzersiz hash kimliği** korundu. Baseline SHA256 `e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83`.
- **Kalıcı GitHub envanteri commit `ff5e241229357e64e2b3d30b9bf0a0b3addc2528`**: `v2/history/stage3-4955-hash-only.jsonl` (**4.955 gerçek kayıt, 1.532.991 bayt**). Git blob SHA `c91c94a3f19097dec2855105da26d8b9a8329f8b` yerel gerçek dosyanın `git hash-object` sonucu ile birebir doğrulandı. Dosya sadece hash, kaynak kimliği ve metadata sınıflandırma kanıtı içerir; URL/erişim bilgisi içermez.
- Gerçek bölge adayları: **TR 50, AZ 1, UNKNOWN 4.904** (yalnızca metadata; Türkçe/Azerice ses kanıtı değildir). Tekrarlanan kimlik **0**; 4.955 kimliğin tamamı geçmiş koruma modülünde saklandı ve **AES-GCM şifreleme/deşifre tam geri yükleme** doğrulandı. Arşiv kimlikleri oynatılabilir URL değildir.
- Kod commit `d839e267cdb1cb7a9b0370ca8dcba302181435e6`: `v2/historical_local_match.py` mevcut M3U'ları **çevrimdışı** ve salt-okunur işler; gerçek URL'yi hash'leyerek yalnızca SHA-256 eşleşmesini kabul eder; isim benzerliğini kabul etmez; eşleşen URL'yi yalnızca program belleğinde tutar; açık raporda URL üretmez. İsteğe bağlı AES-GCM arşiv çıktı desteği vardır. `v2/test_historical_local_match.py` testleri aynı toplu Stage 3 CI içine eklendi.
- Gerçek CI eşleştirme run `41617269449` **SUCCESS, 69 test OK**. Depodaki ana İBO ve YEDEKLER test M3U'su ile #60/#72 arşivlerinden dört M3U dosyası (toplam **6 mevcut yerel playlist**) karşılaştırıldı. **4.955 kayıp hash için kesin URL eşleşmesi 0; hâlâ hash-only 4.955**. Bu önemli sonuç, geçmişin kaybolduğu anlamına gelmez; gerçek URL'ler bu altı mevcut listeden yeniden elde edilemedi. Yeni canlı kanal araması yapılmadı.
- Kalıcı tarihî envanteri koruma workflow commit `838d4b748c19d4466aadca37e7e5769906d8613f`: orijinal #60/#72 raporlarından çıkardığı indexi beklenen SHA-256 ile kontrol ederek yalnızca `madsc/v2-discovery-bulk-20261031` dalına bir kez commit eder, sonrakilerde **değiştirmeyi reddeder**. CI run `41617688783` SUCCESS, kimlik dosyası GitHub'a gerçekten commit edildi.
- Sürekli değişmezlik test commit `304b22f00325f872ac0e9f0d0366645d7f597e6b`: `v2/test_stage3_immutable_history.py` gerçek dosya SHA256'sını (`ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27`), kimlik-seti digestini, 4.955 tekil sayısını, TR/AZ/UNKNOWN dağılımını ve URL'siz olmasını doğrular. Stage3 toplu işlerine eklendi.
- Commit `304b22f0` için GitHub Actions: `V2 Stage 3 Real Historical 4955 Evidence` **41618215586 SUCCESS, 71 test OK**, ayrıca gerçek 4.955 kimlik/AES-GCM kontrolü + yerel URL eşleştirmesi; `V2 Stage 3 Historical Inventory Loss Protection` **41618215807 SUCCESS, 65 test OK**; `V2 Eight-Stage Runner Verification` **41618215989 SUCCESS**; `V2 Master Engine` **41618215924 SUCCESS** (offline), `V2 Current Scanner Offline Gate` **41618215911 SUCCESS**.
- Koruma: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, `main`, PR #9 ve eski depo değiştirilmedi. **Gerçek 4.955 URL'si geri üretildi veya cihazda oynuyor iddiası yoktur.** URL'lerin yeniden bulunabilmesi için gerçek adres kaydı barındıran yeni kanıt gereklidir. Çevrimiçi kaynak/kanal taraması bu aşamada özellikle yapılmadı.

## 3 Kasım 2026 — Aşama 3 hash-only eşleşme kaynak/provenance ve TR/AZ çakışma bütünlüğü

- Çalışma dalı `madsc/v2-discovery-bulk-20261031`; ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` ve YEDEKLER/YENİLER/FAVORİLER, `main`, eski depo ve PR #9 değiştirilmedi. Yeni çevrimiçi kanal taraması, otomatik playlist yayını veya IBO cihaz oynatması yapılmadı.
- Başlangıçtaki gerçek #60 ve #72 envanterleri: #60 = 27.047 farklı yayın hash'i, 11.860 `VIDEO_DECODED`; #72 = 13.518 farklı hash. #60'ta görüntüsü çözülmüş ancak #72'de bulunmayan **4.955 eşsiz anonim SHA-256** güvenli biçimde `v2/history/stage3-4955-hash-only.jsonl` dosyasında korunuyor. Dosyaya yeni URL, parola veya erişim token'ı yazılmadı. Kaynak sıralaması/metadata TR=50, AZ=1, UNKNOWN=4.904; bunlar konuşulan dil veya güncel erişim kanıtı değildir.
- Commit `ba4d67a93d356da94e964d73f8b9cc658e7f5cc1` ile `historical_inventory_guard.reconcile` iyileştirildi: **hash-only geçmiş satırları URL kimliğiyle kesin eşleştiğinde** geçmiş `source_ids` kaybolmadan aday görünümüne taşınır. Aynı URL/hash için geçmiş ve güncel TR/AZ kanıtları çelişirse `UNKNOWN / CONFLICTING_TR_AZ_EVIDENCE` korunur; geçmişte çakışma işareti varken güncel tek taraflı metadata tarafından silinemez. Yalnızca geçmiş kanıtında tek bölge varsa ve güncel aday UNKNOWN ise `HISTORICAL_REGION_EVIDENCE` ile aday bölgesi korunur; hiçbir zaman konuşulan dil, güncel yayın veya cihaz testi olarak sayılmaz.
- Yeni özet sayaçları: `historical_duplicate_identity_rows` (URL/hashes dahil tekrar eden tarihî kimlik satırları), `historical_hash_only_provenance_linked` (gerçek URL ile eşleşen tarihî hash kaynağı), önceki sayaçlar aynı kalır. **Orijinal tekrar/hatalı tarihî satırlar arşivden silinmez**; tekilleştirme sadece URL aday görünümünde yapılır. `v2/test_stage3_hash_evidence_linkage.py` 5 ek regresyon testi içeriyor.
- İlgili testler **tek tek değil, iki toplu Stage 3 CI paketinde** çalıştırıldı. Run `41619445169` SUCCESS = **70/70** tarihî kayıp, sınıflandırma, AES-GCM ve kimlik testleri; run `41619445126` SUCCESS = **76/76** gerçek #60/#72 ve URL hash eşleme testleri. Run `41619445251` genel regresyon + FFmpeg SUCCESS; run `41619445090` scanner offline SUCCESS; Master Engine offline ve monitor SUCCESS.
- Gerçek 4.955 kimlik yeniden #60/#72 artifact'larından doğrulandı, AES-GCM encrypt/restore başarılı. 6 mevcut M3U dosyasıyla tam SHA-256 eşleme sonuçları **0 kesin URL, 4.955 eşleşmemiş hash**. Bu **kayıt kaybı değildir**; gerçek URL'nin bu mevcut altı kaynakta bulunmadığı anlamına gelir. SHA-256'dan URL tahmin edilmez. `main` ve korunan playlist dosyasına dokunulmadı.

## 3 Kasım 2026 — Aşama 3 yeni kimlik çelişkisi ve satır içi TR/AZ sınıflandırma koruması

- Gerçek #60/#72 kayıp envanteri `v2/history/stage3-4955-hash-only.jsonl`: **4.955 benzersiz SHA-256 tarihî kimlik**, görünümde tekrar **0**. Ana dosya ve hash-only orijinal envanter değişmedi. #60'da video dekodu kanıtlı, #72'de bulunmayan kimliklerdir; güncel yayın/İBO cihaz testi değildir. Sabit metadata etiket dağılımı: **TR 50, AZ 1, UNKNOWN 4.904** (konuşulan dil kanıtı değildir).
- Kod commit `1472c75549510e67821f8640fa3fb4e6a029bf23`: `v2/historical_inventory_guard.py` artık aynı satırda hem gerçek `url` hem `url_sha256` bulunursa digest eşitliğini zorunlu tutar. Yanlış SHA-256 ile eski veya yeni kaynak kimliğinin gizlice değiştirilmesi **ValueError** ile reddedilir; başarısız veri çıktı ya da şifreli arşiv üretimine geçemez.
- Ek `region_signals` denetimi, aynı satırdaki bağımsız country/scope, `tvg_id`, kanal/grup adı işaretlerini birlikte okur. TR ve AZ çelişiyorsa yalnızca URL'ye erişilebilir diye tek taraflı kategoriye almaz; `UNKNOWN / CONFLICTING_TR_AZ_EVIDENCE` olarak karantinaya alır. Önceden kaydedilmiş tarihî sınıflandırma ve ham kayıtlar silinmez. Ek sayaç: `historical_rows_with_internal_region_conflict`.
- `v2/test_stage3_identity_integrity.py` içine kimlik uyuşmazlığı, doğru hash, aynı-satır TR/AZ çelişkisi, hash-only→URL eşleştirme çelişkisi ve farklı token'lı gerçek URL tekilliğini kapsayan **5 toplu regresyon testi** eklendi. İki ayrı tarihî CI iş akışında konu bazlı batch'e bağlandı; testler tek tek çağrılmadı.
- GitHub Actions commit `1472c755`: `V2 Stage 3 Historical Inventory Loss Protection` **41620864305 SUCCESS, 75/75**; `V2 Stage 3 Real Historical 4955 Evidence` **41620864243 SUCCESS, 81/81**, gerçek 4.955 kimlik/AES-GCM roundtrip OK, 6 mevcut M3U ile exact SHA eşleştirme **0 URL, 4.955 unmatched**; `V2 Eight-Stage Runner Verification` **41620864249 SUCCESS**; `V2 Current Scanner Offline Gate` **41620864352 SUCCESS**; `V2 Master Engine` **41620864247 SUCCESS** (çevrimdışı testler, canlı master taraması tetiklenmedi); `V2 Actions Status Monitor` **41620864281 SUCCESS**.
- Kural: Orijinal ham geçmiş satırları, hash-only kayıtlar, başarısız yayınlar, URL/EPG/logo kaynakları korunacak; yeni veri için yalnızca gerçek URL'nin SHA'sıyla birebir eşleme yapılacak. Açık URL uydurulmayacak, hash-only kanıt oynatılabilir kanal diye sunulmayacak. Ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, `main`, PR #9 ve eski depo değiştirilmedi.

## 3 Kasım 2026 — Aşama 3 şifreli geçmiş arşivinin ayrıştırılması ve 4.955 kimlik baz çizgisi

- Devam dalı `madsc/v2-discovery-bulk-20261031` (main veya eski depo, ana İBO/YEDEKLER/YENİLER/FAVORİLER, PR #9 değişmedi). Bu aşamada canlı kanal taraması ve cihazda oynatma doğrulaması yapılmadı.
- Orijinal #60/#72 Actions ZIP arşivleri ve #60 source snapshot/toplu candidates tekrar yerel olarak tarandı: **83 JSON/M3U türü dosya**, yaklaşık **60.302 URL biçimindeki değer**, SHA-256 ile **4.955 geçmiş kimliğe kesin eşleşen URL: 0**. İsimden veya hash'ten URL uydurulmadı. Bu tarama medya/oynatma taraması değil, saklı rapor ve listelerin çevrimdışı değer eşleştirmesiydi.
- **4.955 gerçek kimlik** `v2/history/stage3-4955-hash-only.jsonl` içinde kalıcı ve URL'siz; kayıp hashler tekrar içermiyor. 50 TR / 1 AZ / 4.904 UNKNOWN sadece metadata bölge aday sınıflandırmasıdır; dil/oynatma kanıtı değildir.
- Commit `1ed2d9291427408a926ebad3e993ea2c8c9f0049`: `historical_inventory_guard.unpack_archive_snapshot` AES-GCM restore içinden `raw_historical_and_new` bloklarını güvenle okur, korunan **orijinal tarihî prefix** ile daha sonra eklenen gerçek URL kanıtını baseline satır sayısına göre ayırır. Daha önce karışık arşiv biçimleri, eksik/yeniden sıralanmış bloklar ve bilinmeyen blok türleri güvenli biçimde reddedilir; eskiden kullanılan yalnızca tarihî satırlı düz arşivler baseline sayısı tam ise desteklenir. Aday görünümünde eski URL kimlikleri eksilirse reddedilir.
- `verify_historical_baseline` ek kontrolü, yalnızca `--expected-historical-records 4955` sayısına güvenmek yerine `--baseline-index` ile gerçek hash kimlik setinin **birebir korunmasını** doğrular. `historical_inventory_guard.py --historical-archive` yeniden çalıştırıldığında önceki şifreli arşivden gelen gerçek eşleşme kayıtlarını yok saymadan yeni kanıtlarla birleştirir.
- `v2/test_stage3_archive_lineage.py` 4 ilave regresyon testi: şifreli geçmiş arşivinde tarihî kayıt ve yeni URL ayrımı, kapalı hata yönetimi, baseline seti ile sayı/kimlik bütünlüğü, eski düz arşiv uyumu. Bu testler tek tek çalıştırılmadı; **iki Stage 3 toplu işine** eklendi.
- GitHub Actions: `V2 Stage 3 Historical Inventory Loss Protection` run `41621843316` **SUCCESS, 79/79**; `V2 Stage 3 Real Historical 4955 Evidence` run `41621843366` **SUCCESS, 85/85**, 4.955 gerçek hash/AES-GCM yeniden doğrulandı, 6 yerel M3U'da kesin URL eşleşmesi yine 0. `V2 Current Scanner Offline Gate` run `41621843320` SUCCESS, `V2 Master Engine` run `41621843355` SUCCESS (yalnızca offline-tests), `V2 Actions Status Monitor` run `41621843427` SUCCESS.
- Açık sınır: **4.955 orijinal hash kimliği korunuyor fakat 4.955 oynatılabilir yayın adresi geri getirildi denilemez**. SHA-256 geri döndürülemez; yalnızca özgün URL barındıran yeni güvenilir envanterle kesin kimlik eşleştirme yapılabilir.

## 3 Kasım 2026 — Aşama 3: değişmez 4.955 geçmiş metadata ve şifreli geri yükleme doğrulaması

- Aktif dal: `madsc/v2-discovery-bulk-20261031`. Eski repo, `main`, PR #9, korunan ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER değiştirilmedi; yeni kanal taraması ve otomatik yayın yapılmadı.
- Orijinal #60/#72 gerçek kanıtlarından korunmuş `v2/history/stage3-4955-hash-only.jsonl` **4.955 benzersiz URL-SHA256 kimliği** ve kimlik metadata'sını içerir; TR 50, AZ 1, UNKNOWN 4.904 metadata bölge adaylarıdır, ses/dil/İBO oynatma kanıtı değildir. Bu dosya değiştirilmedi.
- Önceki `verify_historical_baseline` aynı kimlik SHA kümesini ve sayıyı denetliyordu; ancak aynı hash için `source`, `region_candidate`, `classification_evidence`, `device_verified` gibi metadata alanlarının değiştirilmesini algılamıyordu. **Kod commit `2cb460ffe1198c121cd9f2fd9523004c26366b3f`** ile geçmiş **her satırın bütün metadata değerleri**, kimlik bazında asıl immutable geçmiş indeksle birebir doğrulanır; sıralama farkı kabul edilir, içerik değişimi **ValueError** ile reddedilir.
- `v2/test_stage3_archive_lineage.py` içine metadata değişimi (TR→AZ, kaynak, kanıt etiketi, cihaz/dil doğrulama bayrağı) ve sıralama bağımsızlığı için 2 ek regresyon testi eklendi.
- `.github/workflows/v2-stage3-real-history.yml` gerçek #60/#72 arşivinden oluşturulan **4.955 satırı**, kalıcı geçmiş dosyasının hem hash kümesi hem **orijinal metadata içeriği** ile karşılaştırır. AES-GCM roundtrip sonrası `unpack_archive_snapshot` ile gerçek kayıtlar açılıp aynı 4.955 metadata yeniden doğrulanır; yeni URL uydurulmaz.
- GitHub Actions commit `2cb460ff` için **tüm 6 iş akışı SUCCESS**: Aşama 3 tarihî kayıp koruması run `41622887986` **81/81 test OK**; Aşama 3 gerçek kanıt run `41622887860` **87/87 test OK**, 4.955 gerçek kimlik/metadata ve AES-GCM geri yükleme başarılı; 6 mevcut playlist kesin URL eşleştirmesi **0**, eşleşmeyen **4.955**. Genel FFmpeg + regresyon `41622887884` SUCCESS; Scanner Offline Gate `41622887901` SUCCESS; Master Engine offline `41622887968` SUCCESS, Status Monitor `41622888001` SUCCESS.
- **Aşama 3'ün kalıcı tarihî kayıt koruması, URL SHA kimlik doğrulaması, tekrarların sadece aday görünümünde temizlenmesi, kaynak/metadata/Türk-Azeri sınıflandırma tutarlılığı ve AES-GCM geri yükleme doğrulandı.** Gerçek yayın URL'leri mevcut 6 listeden geri kazanılamadığı için 4.955 kanalın güncel oynatılabilir olduğuna dair kanıt yoktur.

## 3 Kasım 2026 — Aşama 3: tam blok kaybını algılayan şifreli arşiv manifesti

- Çalışma dalı `madsc/v2-discovery-bulk-20261031`; korunan ana İBO `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, `main`, eski depo ve PR #9 değiştirilmedi. Yeni internet kaynak taraması veya cihaz oynatma testi yapılmadı.
- Gerçek 4.955 kayıp geçmiş kimlik hâlâ `v2/history/stage3-4955-hash-only.jsonl` dosyasında URL'siz, benzersiz ve kaynak kanıtlarıyla korunuyor. Bölge adayları: TR 50, AZ 1, UNKNOWN 4.904 (yalnızca metadata; konuşulan dil/oynatılabilirlik kanıtı değil). #60 ve #72 karşılaştırma kimlikleri değişmedi.
- **Kod commit `7de0d749c542a767343c3c107e4b694b424a3d29`**: AES-GCM kayıtları ayrı ayrı doğrulasa da arşiv sonundaki tam/sağlam şifreli blokların silinmesinin fark edilmeyebileceği sorunu giderildi. `historical_inventory_guard.py` yeni arşivleri `historical-inventory-guard-v2` sürümünde yazar; sonuna **AES-GCM ile şifrelenmiş bütünlük manifesti** ekler. Manifest önceki blokların sırasını, SHA-256 payload bütünlüğünü, blok sayısını, ham tarihî+yeni satır sayısını ve aday görünümündeki kayıt sayısını doğrular.
- `unpack_archive_snapshot` V2 manifestini zorunlu tutar, eksik son blok/manifesti, tam şifreli kayıt silinmesini, yeniden sıralanmış veya kaybolmuş aday görünümünü ve karışık sürüm biçimlerini hata ile reddeder. **Eski V1/legacy arşivler okunabilir**; V2 arşivler manifest olmadan geçerli sayılmaz.
- Yeni `v2/test_stage3_archive_lineage.py` regresyonları: 205 kayıtlı çok-bloklu şifreli arşivde tam manifest kaybını ve orta blok silinmesini reddetme; 105 geçmiş + bir yeni gerçek URL denemesinde blok sıralaması ve aday görünümü silinmesini reddetme. Testler **tek tek çalıştırılmadı**; mevcut iki Stage3 toplu CI paketine otomatik dahil edildi.
- **GitHub Actions commit `7de0d749`**: `V2 Stage 3 Historical Inventory Loss Protection` run `41625438936` **SUCCESS, 83/83 test**; `V2 Stage 3 Real Historical 4955 Evidence` run `41625438888` **SUCCESS, 89/89 test**. Gerçek 4.955 kimliğin tam AES-GCM geri yükleme ve kalıcı envanter eşleşmesi başarılı; 6 mevcut M3U içinde gerçek URL SHA eşleşmesi **0**, eşleşmemiş **4.955**. `V2 Current Scanner Offline Gate` run `41625438934` SUCCESS, `V2 Master Engine` `41625438928` offline-tests SUCCESS ve `V2 Actions Status Monitor` `41625438872` SUCCESS.
- Bu değişiklikler **geçmiş envanter korumasını** güçlendirir; 4.955 oynatılabilir yayın URL'sinin geri bulunduğu veya IBO Player'da oynatıldığı iddia edilmez. Kaybolan adresler SHA-256 kimliğinden yeniden üretilemez. Sıradaki farklı aşama başlayana kadar yeni kaynak taraması yapılmadı.

## 3 Kasım 2026 — Aşama 3 atomik arşiv yayımı ve çelişkili TR/AZ ham kayıt sınıflandırması

- Aktif dal `madsc/v2-discovery-bulk-20261031`. Ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, `main`, eski depo ve PR #9 değiştirilmedi. Bu çalışmada yeni canlı kanal keşfi veya cihaz oynatma testi yapılmadı.
- GitHub Actions #60 (run `40743765437`) ve #72 (run `40948768782`) gerçek raporlarından çıkarılan **4.955 benzersiz SHA-256 tarihî yayın kimliği** `v2/history/stage3-4955-hash-only.jsonl` içinde değişmez biçimde korunuyor. Geçmiş kaynak, başarısızlık, tekrar ve metadata kanıtı silinmedi. Bu 4.955 URL değil; oynatılabilir kanal sayısı değildir.
- Kod commit `7ade24e7ddb80692873efbf36d6649d48a320e22`: `historical_inventory_guard.preserve_to_new_archive` AES-GCM arşivini **önce aynı dizinde 0600 izinli rastgele geçici dosyada** tamamlayıp restore + V2 manifest ile doğrular; ancak ondan sonra **`os.link` ile var olmayan hedefe atomik yayımlar**. Kısmi şifreleme/append/fsync/restore hatalarında tamamlanmamış nihai arşiv bırakmaz; hedef aynı anda oluşturulduysa üzerine yazmayı reddeder; geçici dosya `finally` ile kaldırılır.
- Yine aynı commit ile `classify` artık `_classify_preferred` ve tüm `region_signals` ipuçlarını birlikte değerlendirir. **Tek tarihî kayıt içinde** scope/country, tvg-id veya kanal adı üzerinden TR ve AZ çelişiyorsa ilk etiketi zorla tercih etmek yerine `UNKNOWN / CONFLICTING_TR_AZ_EVIDENCE` sınıflandırması yapar. Eskiden incelemeye alınmış hash-only çakışma işaretini kaldırmaz. Ham geçmiş satırlarını ve değişmez arşivi yeniden yazmaz.
- Yeni `v2/test_stage3_atomic_classification.py` **5 regresyon testi** iki toplu Stage3 CI işine dahil edildi: ham satır TR/AZ çakışması ve sayaçlar, önceki çakışma işareti, şifrelemede hata durumunda nihai dosya/kalıntı bulunmaması, rakip hedef oluştuğunda üzerine yazmama, başarılı manifest ve sahip izinleriyle tam arşiv doğrulaması.
- Commit `7ade24e7` için **altı GitHub Actions çalışması SUCCESS**: Stage 3 tarihî kayıp/toplu koruma `41626442810` **88/88 test OK**; Stage 3 gerçek #60/#72 arşivleri `41626442819` **94/94 test OK**, AES-GCM tekrar doğrulandı; genel regresyon ve FFmpeg `41626442978` SUCCESS; Scanner Offline Gate `41626442821` SUCCESS; Master Engine offline `41626442803` SUCCESS; Actions Status Monitor `41626442809` SUCCESS.
- **Gerçek 4.955 geçmiş hash için mevcut altı M3U'da kesin URL eşleşmesi halen 0**; 4.955 kimliğin hepsi korunur ve güncel oynatılabilir yayın oldukları iddia edilmez. Metadata bölge adayları 50 TR, 1 AZ, 4.904 UNKNOWN; konuşulan Türkçe/Azerice sesin doğrulandığı anlamına gelmez. Ana İBO kanal listesine hiçbir kanal eklenmedi/silinmedi.

## 3 Kasım 2026 — Aşama 3: yeni başarısız, hash-only ve tekrar kaynak kanıtlarının kayıpsız saklanması

- **Aktif depo/dal:** `Madsc55/MADSC55-TV-V2` / `madsc/v2-discovery-bulk-20261031`. Eski depo, `main`, PR #9, ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER, YENİLER ve FAVORİLER değiştirilmedi. Canlı kanal araması/cihazda İBO oynatma testi yapılmadı.
- **Gerçek tarihî baz çizgi:** `v2/history/stage3-4955-hash-only.jsonl` içindeki #60→#72 kayıp **4.955 eşsiz SHA-256 yayın kimliği** aynen korunuyor; TR **50**, AZ **1**, UNKNOWN **4.904** yalnızca tarihî metadata kanıtına dayalı bölge adaylarıdır, ses/dil veya güncel yayın doğrulaması değildir. Altı mevcut M3U dosyasında **0 kesin URL eşleşmesi**; 4.955 adres henüz URL olarak bulunmadı.
- **Gerçek kod kusuru:** `historical_inventory_guard.reconcile` daha önce `protected` ham arşiv görünümüne yalnızca *yeni benzersiz ve geçerli URL* ekliyordu. Aynı URL'nin yeni kaynakta tekrar görünmesi, geçersiz/başarısız URL, URL'siz anonim veya hash-only yeni kanıt **ham şifreli envanterden eksiliyordu**. Geçmiş 4.955 orijinal satırın korunması zaten yeşildi ama yeni kanıtlarda bu kayıp devam ediyordu.
- Kod commit'leri `195abcd88293501ea4b366089f6dd3c7c5582dcf` ve düzeltme `098a55b807b21b75868bdb3bc57a0b2f67ac5713`: şifreli `raw_historical_and_new` grubu artık **`historical + current` bütün ham kayıtlarını sırayla ve eksiksiz** korur. Tekilleştirme yalnızca URL SHA-256 bazlı aday görünümünde yapılır; hiçbir başarısız, yinelenen veya anonim gözlem silinmez. Yeni hash-only kaynak kanıtları gerçek URL ile tam SHA eşleştiğinde adayın `source_ids` alanına eklenir; **önce eski, sonra yeni kaynak sırası** korunur. Ham kayıtlar arşivlenmeye devam eder; geçersiz URL için oynatma adayı oluşturulmaz.
- Açık sayımlar: `current_records_preserved`, `current_invalid_records_preserved`, `current_duplicate_url_rows_preserved`, `total_raw_records_preserved`. Önceden mevcut geçmiş kimlik/metadata sayaçları değişmedi. `unpack_archive_snapshot` şifreli arşivde tarihî 4.955 satırlık prefix ile eklenen tüm yeni ham kanıtları ayrı gruplar halinde geri getirir.
- `v2/test_stage3_archive_lineage.py` içine 2 regresyon: önce 2 tarihî + 6 yeni (gerçek URL, URL tekrarı, başarısız/özel IP, hash-only, anonim, sonra gelen hash kaynak kanıtı) satırın eksiksiz AES-GCM kaydı ve restore sonrası ikinci tur bire bir eşleşmesi; ikinci olarak geçmiş URL + yeni tekrarlar + yeni hash-only kaynak provenansının aday görünümünde tekilleştirilip ham arşivde korunması. Bölge çakışma regresyonu, artık yeni satırların ham kanıta dahil edilmesine uyumlu güncellendi.
- İlk toplu commit `195abcd8` testte kaynak provenans sıralaması nedeniyle **başarısız** oldu; logdaki iki regresyon hatası düzeltildi ve en son `098a55b8` üzerinden **iki Stage3 toplu CI testi yeşil**: `V2 Stage 3 Historical Inventory Loss Protection` run `41627609875` **90/90 OK**, `V2 Stage 3 Real Historical 4955 Evidence` run `41627610010` **96/96 OK**, 4.955 gerçek SHA/AES-GCM geri yükleme doğrulandı, mevcut listelerle URL eşleşmesi 0. Ayrıca Master Engine çevrimdışı run `41627610002` SUCCESS, Scanner Offline Gate `41627609799` SUCCESS, Status Monitor `41627609982` SUCCESS. Genel Eight-Stage/FFmpeg run `41627609880` sonuç kontrolü ayrı yapılacak.
- **Sınır:** 4.955 kimliğin koruma/tekrar temizliği ve metadata TR/AZ sınıflandırması doğrulandı. SHA-256'dan oynatılabilir URL geri üretilmez; yerel arşivlerde eşleşen URL bulunmadı. Kullanıcı cihazında İBO Player oynatma testini kendisi yapacaktır.

## 3 Kasım 2026 — Aşama 3: tüm gerçek 4.955 geçmiş kayıtta bağımsız uçtan uca denetim

- Yalnızca `Madsc55/MADSC55-TV-V2` ve `madsc/v2-discovery-bulk-20261031` çalışma dalında işlem yapıldı. `main`, eski depo, PR #9, ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER değiştirilmedi. Yeni medya/stream veya internet kanal taraması yapılmadı.
- **Gerçek sabit envanter:** `v2/history/stage3-4955-hash-only.jsonl`, #60→#72 arşivlerinden doğrulanmış **4.955 farklı SHA-256 kimliği**; TR **50**, AZ **1**, UNKNOWN **4.904** yalnızca metadata bölge adayıdır. Konuşulan dil, yeni video dekodu veya IBO Player cihaz oynatımı doğrulanmadı. Altı mevcut listede **0 kesin URL eşleşmesi**, 4.955 hash-only kayıt hâlâ korunuyor.
- GitHub commit `85b921ee7a5d280f7ca474ffa9095ef07e2433e3`: yeni `v2/stage3_real_complete_audit.py` **yalnızca orijinal gerçek 4.955 indeksini** kullanır; dosyanın sabit SHA-256 içeriğini, kimlik kümesini, tam kayıt metadata yapısını, bütün playback/review bayraklarını ve TR/AZ/UNKNOWN dağılımını **her satır için** doğrular. `reconcile` ile sıfır kayıp, sıfır hash tekrarı ve sıfır uydurma URL ispatlanır; tüm 4.955 ham kayıt AES-GCM V2 manifestli özel geçici arşivine aktarılıp tam deşifre ve metadata geri-yükleme doğrulaması yapılır. Çıktı yalnızca **URL'siz** JSON denetim kanıtıdır; geçici şifreleme anahtarı loglanmaz.
- Workflow commit `2b839f82036e27b195f5a6e6217e9866395e44be` ile **historical-inventory** toplu CI'a, commit `b12e64fee87714cc206748546fd618ef6e21ada5` ile **real-history** toplu CI'a tam gerçek envanter doğrulaması bağlandı. İki CI artifact'i `stage3-real-4955-complete-audit.json` raporunu içerir.
- **GitHub Actions:** `V2 Stage 3 Historical Inventory Loss Protection` run `41629012107` **SUCCESS 90/90 test** ve gerçek 4.955 tam AES-GCM denetimi OK; `V2 Stage 3 Real Historical 4955 Evidence` run `41629048509` **SUCCESS 96/96 test**, orijinal #60/#72 re-compare ve tüm gerçek 4.955 tam metadata/AES-GCM denetimi OK, 6 mevcut M3U'da eşleşen URL **0**. `V2 Eight-Stage Runner Verification` run `41629048586` SUCCESS; `V2 Master Engine` offline run `41629048466` SUCCESS; `V2 Actions Status Monitor` run `41629048451` SUCCESS.
- Bu çalışma **4.955 anonim tarihî kimliğin kayıp önleme, tekilleştirme ve TR/AZ metadata sınıflandırmasını somut gerçek veriyle uçtan uca doğrular**; oynatılabilir URL'leri SHA-256'dan geri getirildi iddiası yoktur. Orijinal URL barındıran ayrı güvenilir kaynak bulunana kadar 4.955 gerçek URL kurtarma ve kullanıcı cihazı playback doğrulaması mümkün değildir; kayıp/başarısız envanter hiçbir koşulda silinmez.

## 3 Kasım 2026 — AŞAMA 3 TAMAMLANDI: gerçek 4.955/4.955 yayın URL'si kurtarıldı (yeni cihaz testi yok)

- **Bu not daha önceki '0 URL bulundu' ara durumlarını GÜNCELLER:** Önceki #60/#72 playback ve unified-source-candidates artifact'ları yalnızca anonim SHA-256 içeriyordu; bu yüzden ilk eşleştirmede 0 gerçek URL bulundu. Aynı V2 deposunun **tüm ulaşılabilir Git geçmişi**, önceki V2 dalındaki M3U'lar, 28 Ekim 2026 tarihli 25 gerçek GitHub kaynak commit'i, o günkü IPTV-org/Free-TV sabit revizyonları, Dearbulut açık kaynağı ve 27–28 Ekim tarihli **üç Dearbulut health.json sabit commit'i** incelenince **4.955 kimliğin tamamı için tam SHA256 ile doğrulanmış özgün URL bulundu**. URL'ler hash'ten üretilmedi; orijinal kaynakların gerçek URL dizgileri hash'lenerek birebir eşleştirildi.
- **Kanıt:** V2 Git tarihi 107 farklı veri blob'u tarandı: **4.902** kesin URL hash eşleşmesi. Eski GitHub kaynak sürümleri: **2.844** (25/25 dosya okunabildi). O dönemki yapılandırılmış kaynaklar: **2.075**. Tarihî Dearbulut sağlık kaynakları: **1.861**. Diğer V2 M3U arşivleri: **216**. Aynı SHA çok kaynakta bulunduğunda yalnızca bir kez sayıldı: birleşim **4.955/4.955**, eşleşmemiş **0**, tekrarlanan aday URL **0**. İlk toplu 4.955/4.955 doğrulama Actions run **`41633342078` SUCCESS**.
- Yeni güvenli dosya çıktısı: V2 geliştirme dalındaki `v2/stage3_sealed_export.py` ve `v2/config/stage3_transit_public.pem` kullanılarak Actions run **`41633732031` SUCCESS, 109/109 toplu test** içinde **dört ayrı kaynak grubundaki gerçek URL kayıtları RSA-OAEP-SHA256 + AES-256-GCM ile şifrelenmiş .sealed artifact** olarak dışa aktarıldı; **özel RSA anahtarı GitHub'a/iş akışı loglarına koyulmadı**. Kanıt artifact ID **`13229641611`**; stream URL'si/token içeren açık içerik GitHub'a yüklenmedi.
- Şifreli kanıtlar çalışma ortamında özel anahtarla açıldı; toplam **11.682 kaynak gözlemi** SHA-256 ile karşılaştırılarak **4.955 farklı gerçek URL** bulundu, çakışma/eksik/tekrar **0**. URL'lerin **tamamına** gerçek #60 `unified-source-candidates` artifact'ındaki orijinal kanal adı, tvg-id, logo ve grup metadatası eklendi (**4.955/4.955**). Bunlar sentetik yayın adresi değildir.
- Çalışma ortamında kullanıcıya teslim edilmek üzere mevcut ana İBO playlistinden tamamen ayrı dosyalar oluşturuldu: **`MADSC55_V2_STAGE3_4955_GECMIS_KURTARMA_TEST.m3u8`** (4.955 gerçek URL), ayrıca **2.000 + 2.000 + 955** ayrı M3U test paketi. Tam M3U SHA-256: `d7a0725a1120753ef72a5561a09cdde66abc82f94f6c9e52d6a37401acdde1d3`. Sahte/mock URL kullanılmadı.
- Ayrıca **`MADSC55_V2_STAGE3_4955_REAL_URLS_RECOVERED.enc`** AES-256-GCM V2 arşivi, ayrı gizli kullanıcı anahtarıyla üretildi; **151 şifreli blok + tam manifest** geri yüklenip byte-eşdeğer doğrulandı. Arşivde: ilk 4.955 değişmez tarihî hash-only satır, ardından 4.955 gerçek URL kaydı, 4.955 tekilleştirilmiş aday görünümü; toplam 9.910 ham satır. Kullanıcıya ayrıca **`MADSC55_V2_STAGE3_4955_RECOVERY_KEY.txt`** ayrı dosyada iletilecek; anahtar asla GitHub'a işlenmedi. Doğrulama raporu: `MADSC55_V2_STAGE3_4955_KURTARMA_DOGRULAMA.json`.
- **Türk/Azeri sınıflandırması** #60 tarihî metadata'sına dayanıyor: **TR 50, AZ 1, UNKNOWN 4.904**; bu değerler konuşulan sesin dilini kanıtlamaz ve herhangi bir kanalı Türkçe/Azerice oynuyor diye etiketlemez.
- **Kalan farklı doğrulama:** Kurtarılan URL'lerin *bugünkü* oynatılabilirliği ve İBO Player cihaz testleri **henüz yapılmadı**, URL'ler 28 Ekim'den beri değişmiş veya süreleri dolmuş olabilir. Bu ayrı aşama kullanıcı cihazında test edilecek; #60 tarihî VIDEO_DECODED kanıtı geçerli ama güncel yayın garantisi değildir.
- **KORUMA:** `Madsc55/MADSC55-TV-V2` içindeki yalnızca `madsc/v2-discovery-bulk-20261031` dalı kullanıldı. Ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER ve cihaz favorileri, `main`, PR #9 ve eski depo **değiştirilmedi**. 4.955 URL yalnızca ayrı test dosyalarında ve şifreli arşivde; ana listeye otomatik eklenmedi.

## 3 Kasım 2026 — Aşama 3 KESİN SONUÇ: 4.955/4.955 gerçek tarihî URL, kayıpsız ve güvenli dışa aktarım

- **Bu bölüm, önceki altı mevcut M3U kaynağında "0 URL eşleşmesi" bulunan eski Aşama 3 notlarını günceller.** Sıfır sonucu yalnızca o altı dosyanın sınırlı taramasıydı; V2 Git geçmişi ve orijinal #60 haricî kaynaklar eklenince artık **4.955/4.955 gerçek yayın URL'sinin tam SHA-256 eşleşmesi bulundu. URL kimliği eksik: 0**. Bu kanıt stream'lerin bugün oynadığı anlamına gelmez.
- **Değişmez tarihî kaynak:** `v2/history/stage3-4955-hash-only.jsonl` (gerçek #60 `40743765437` ile #72 `40948768782` karşılaştırmasından), 4.955 benzersiz hash ve metadata satırı. Orijinal kimlik SHA256 toplamı `e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83`. Tekrar eden kimlik: 0; Türk aday 50, Azeri aday 1, sınıflandırılamayan 4.904. Bunlar ülke/metadata adaylarıdır, konuşulan dil teyidi değildir.
- **Gerçek URL bulma kanıtları (örtüşen kümeler):** V2'nin bütün erişilebilir Git M3U/JSON geçmişinde 107 ayrı tarihî blob üzerinden **4.902** URL hash'i; 28 Ekim'deki 25 orijinal GitHub kaynak dosyasında **2.844**; aynı dönemin pinlenmiş IPTV-org/Free-TV ve Dearbulut mevcut feed eşleştirmesinde **2.075**; 27–28 Ekim'de yazılmış Dearbulut sağlık durum envanterlerinde **1.861**. Tam SHA256 ile ortak kayıtları tekilleştirince **4.955 farklı gerçek yayın adresi** doğrulandı. Kaynak kümelerinin sayılarını toplamak yanlıştır; aynı URL çoğunda vardır. Hiçbir URL SHA'dan tersine hesaplanmadı, isim veya kanal benzerliğiyle uydurulmadı.
- **Repo kod/CI:** `v2/stage3_git_history_forensics.py`, `v2/stage3_historical_source_recovery.py`, `v2/stage3_original_configured_source_recovery.py`, `v2/stage3_dearbulut_health_recovery.py` ve `.github/workflows/v2-stage3-real-history.yml` gerçek URL kanıtını karşılaştırıp yalnızca anonim hash sayımını ve kaynak kökenini GitHub raporlarına yazar. 4.955 kimlik, sınıflandırma, tekrar, kaynak geçmişi ve arşiv kaybı testleri bir toplu Stage3 regresyon setinde çalıştırıldı.
- **Gerçek kanıtın gizli aktarımı:** `v2/stage3_sealed_export.py` kullanılarak 4 kaynak kümesinin bire bir URL kayıtları **RSA-OAEP-SHA256 + AES-256-GCM** ile şifrelendi ve Actions artifact'ında yalnızca `.sealed` içerik yayımlandı; özel RSA anahtar GitHub'a aktarılmadı. Aşama 3 Actions `41633732031` SUCCESS (tam 4.955 kurtarma ve şifreli dosyalar), ayrıca Stage3 loss protection `41634505447` SUCCESS (96/96 toplu regresyon), Eight-Stage `41634505389` SUCCESS, offline Master Engine `41634505429` SUCCESS.
- **Kullanıcıya verilen yerel fiziksel çıktılar (yalnızca bu sohbet çalışma alanında, genel GitHub deposuna açık metin URL yüklenmedi):** `STAGE3_4955_GERCEK_GECMIS_URL.m3u8` (**4.955 gerçek eski URL, 0 tekrar**); `STAGE3_TR_AZ_ADAY_51.m3u8` (TR 50 + AZ 1); `ibo_1000.m3u` (1.000); `ibo_2000.m3u` (2.000); `STAGE3_2000_PARCA_1.m3u` (2.000), `STAGE3_2000_PARCA_2.m3u` (2.000), `STAGE3_955_PARCA_3.m3u` (955); toplu ZIP `STAGE3_4955_GERCEK_URL_PAKETLERI.zip`; detaylı `STAGE3_4955_KURTARMA_DOGRULAMA_RAPORU.json`. Her dosyadaki URL yeniden SHA256'landı, sayılar ve ZIP bütünlüğü ayrıca doğrulandı. #60 gerçek kanal adları, TVG-ID, logo ve grup metadata'sı kullanıldı; uydurma yayın eklenmedi.
- **Kritik koruma:** Aktif dal yalnızca `madsc/v2-discovery-bulk-20261031`; eski `Madsc55/madsc-tv` deposu, V2 `main`, PR #9 ve korunan `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` / YEDEKLER / YENİLER / FAVORİLER değiştirilmedi. Yeni M3U'lar **ayrı İBO cihaz deneme paketidir**, ana listeye otomatik eklenmedi. **Güncel canlı yayın/video-ses ve İBO cihazında oynatma doğrulaması 0 olarak raporlanır; eski VIDEO_DECODED kanıtı bugün oynatma garantisi değildir.** Fiziksel dosyalar tarihî URL kurtarma çıktısıdır, yeni oynatılabilir kanal sayısı değildir.

## 3 Kasım 2026 — Aşama 3 kesin SHA kimlik üyeliği ve eski "0 URL" rapor ayrımı (toplu CI doğrulandı)
- Bu kayıt **önceki yalnızca hash-only/altı yerel M3U için 0 URL** raporlarının kapsamını açıklığa kavuşturur; **tarihî gerçek URL kurtarma = 4.955/4.955**. Orijinal #60/#72 hash-only baz çizgide doğrudan açık URL sayısı sıfırdır; buna karşın Git geçmişi, tarihî kaynak sürümleri ve tarihli Dearbulut kayıtlarında tam SHA256 karşılıkları bulunmaktadır. Güncel video/ses ve İBO cihaz testi bu çalışmada yapılmadı; tarihî eşleşme bugün çalışan kanal sayısı değildir.
- Kod commit **`32fc374924a605aacc6e05012512a11e3311d2fb`**: yeni `v2/stage3_exact_coverage.py` ve beş regresyon testi, aynı sayıda fakat orijinal 4.955 kümesinden olmayan SHA eklenmesini, eksik kimliği, bozuk/tekrarlı geçmiş baz çizgiyi reddeder. `.github/workflows/v2-stage3-real-history.yml` önceki zayıf yalnızca 4.955 sayımını, **gerçek korunmuş SHA kümesine birebir üyelik** koşuluyla güçlendirdi. Kaynaklar arası tekrarlar bir kez sayılır; uydurma URL veya kimlik kabul edilmez.
- `v2/stage3_real_complete_audit.py` içindeki eski `actual_stream_urls_recovered: 0` ifadesi, yalnızca orijinal hash-only baz çizginin URL'siz olduğunu belirten `original_hash_only_baseline_plaintext_url_count: 0` olarak düzeltildi. Tarihî koruma workflow'undaki belirsiz `historical_playable_urls_restored: 0` alanı kaldırıldı; önceki şifreli kurtarma kanıtı için 4.955 eşleşme ve ayrı doğrulama koşusu kaydediliyor, **bu çevrimdışı işte özel URL'lerin yeniden deşifre edilmediği açıkça belirtiliyor**. Bugünkü oynatma doğrulaması false kalır.
- **Yeni tek commit için Actions gerçek sonuçları:** Stage3 Historical Inventory Loss Protection run **`41637717198` SUCCESS, 101/101 toplu test**; Stage3 Real Historical Evidence run **`41637717158` SUCCESS, 114/114 toplu test**; gerçek kaynaklarla tam üye küme **4.955**, URL'siz tarihî kimlik **0**, erişilemeyen tarihî kaynak revizyonu **0**; korunan Stage3 artifact **`13230628803`**. Ek olarak Eight-Stage Runner Verification `41637717160` SUCCESS, Master Engine `41637717542` SUCCESS, Current Scanner Offline Gate `41637717719` SUCCESS, Actions Status Monitor `41637717334` SUCCESS.
- Arşivleme ve tekrar koruma testleri şifreli V2 AES-GCM geri yükleme, ham geçmiş kaynak/provenans, TR/AZ/UNKNOWN metadata sınıflandırması (TR 50, AZ 1, UNKNOWN 4.904; **konuşulan dil kanıtı değil**) ve kayıp aday korunumu için yeniden geçti. Tarihî geri kazanımın şifreli URL artifact'ı yalnızca özel anahtar sahipleri tarafından açılabilir; herkese açık depoya URL/token veya deşifre anahtarı eklenmedi. Bu çalışmada yeni canlı yayın testi, otomatik IBO aktarımı, 500/2000 kanal cihaz testi yapılmadı.
- Koruma: yalnızca `madsc/v2-discovery-bulk-20261031` geliştirme dalında Stage3 kodu ve bu not değişti; `main`, ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, PR #9 ve eski depo değiştirilmedi. Sonraki bağımsız konu bugünkü yayın video/ses uygunluğu ve kullanıcının İBO cihaz testidir.

## 3 Kasım 2026 — Türkçe M3U/M3U8 kaynak kaybı denetimi, gerçek #60/#72 kanıtı ve 404 koruması
- Çalışma dalı: `madsc/v2-discovery-bulk-20261031`; ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, `main`, eski depo, YEDEKLER, YENİLER, FAVORİLER, EPG ve PR #9 değiştirilmedi.
- `514470c501a8885ba91459f4d5560d9832240a1c`: `v2/source_loss_audit.py` artık kaynak sayısı sabit kalsa da önceki ve yeni anonim aday SHA256 kümelerini karşılaştırır; kaybolan adayları, bozulan/tekrarlanan SHA'yı ve eksik/kırpılmış raporun doğrulanamaz durumunu birbirinden ayırır. Ayrı `v2/turkish_m3u_source_audit.py` kaynak başlığı erişimini, gerçek #60/#72 aggregate raporlarını ve değişmez 4.955 tarihî kimlik kümesini topluca kontrol eder; yayın URL'sini, token'ı veya görüntü oynatma iddiasını rapora dökmez.
- Gerçek Actions run `41640828422` **SUCCESS 41/41 toplu test**: 47 kaynak tanımından 46'sı geçerli M3U başlığı döndürdü, `ilyswch-iptv-tr` **HTTP 404**. #60 run `40743765437` **27.047** URL; #72 run `40948768782` **13.518** URL; ortak **13.136**, #60'a özgü **13.911**, #72'ye özgü **382**. #60'da VIDEO_DECODED olup #72'de bulunmayan **4.955** kimlik, kalıcı `stage3-4955-hash-only.jsonl` gerçek baz çizgisiyle birebir eşleşti. Bu 13.911 adres bugün çalışmıyor demek değildir; #72'de görünmemiştir.
- Kaynak başına gerçek eski/yeni sayaçlar: `iptv-org` 11.204/9; `free-tv-independent` 1.347/5; `github-auto-7` 4.931/0; `github-auto-8` 1.854/1. Bunlar kaynak kapsama düşüşü, güncel medya/konuşma dili doğrulaması değildir. Tarihî URL kurtarma Aşama 3'te **4.955/4.955** olarak tamamlanmıştı; geçmişte başarısız veya kayıp hiçbir kimlik silinmedi.
- 404 kök neden: `ilyswch/IPTV-TR` herkese açık deposunun GitHub API güncel dizininde `box.m3u` yok (yalnızca `.gitignore` var). Dokunulmaz tarihî kaynak kimliği `v2/config/sources.json` içinde korundu, `enabled=false` ve tarihli gerekçe ile aktif taramadan çıkarıldı (commit `7d1660ba1ae8f487ee9ff73da4bc1e21c3b3d91b`). Bu kaynağın yerine farklı IPTV-org listesini aynı kaynakmış gibi kullanma kuralı kaldırıldı; alternatifler orijinal provenans/önbellek diye sunulamaz.
- `dd91e185549ec4fbe8173f18c5b6676b8eebd83f`: `discover.py` kapatılan kaynağı açıkça rapora işler; başka bir alternatif besleme kullanılmışsa farklı kaynak kimliği ve `ORIGINAL_SOURCE_UNAVAILABLE` ile fail-closed etiketler. `source_failover.py` yalnız asıl başarılı kaynağı onun cache'ine yazar. Geliştirme dalındaki otomatik Worldwide keşfi, son kullanıcı final tarama kararı için yalnız `workflow_dispatch` olarak sınırlandı.
- Son kaynak doğrulaması: run `41641788187` **SUCCESS, 43/43 toplu test**; kaynak envanteri **47 tarihî tanım, 46 etkin, 1 korunan/kapatılan kaynak**; etkin kaynakların **46/46** tanesi geçerli M3U başlığı verdi, etkin kaynak başlığı 404 **0**. #60/#72 farkı ve 4.955 korunmuş kimlik yeniden doğrulandı; rapor Actions artifact `13233366640` (anonim, token ve playlist yayını içermez).
- V2 Turkish TV Health eski otomatik push workflow'unu `discover.py` değişikliği tetikledi (run `41641788093`); bu çalışma salt-okunur ve yeni ana liste aktarımı yapmaz, ancak **otomatik kanal taraması kullanıcı final kararına kadar istenmiyor**. Bu nedenle geliştirme dalındaki health workflow tetikleyicisi de yalnız manuel `workflow_dispatch` yapılır. Önceden başlamış koşu ayrı takip edilir; tamamlandı diye iddia edilmez.
- Açık ayrı aşama: 46 etkin M3U kaynağının içindeki **gerçek yayın URL'leri** bugün medya/video/ses sağlıyor mu, her kanal gerçek Türkçe/Azerice konuşuyor mu ve kullanıcı cihazında İBO açılıyor mu **henüz doğrulanmadı**. Kaynak başlığı HTTP_OK bu kanıt değildir. Tüm hazırlıklar bitince tek izinli toplu yayın taraması ve 500'lük kullanıcı test paketleri; ana playlist otomatik değiştirilmez.

## 3 Kasım 2026 — Türkçe M3U tam içerik ve dinamik kaynak kaybı doğrulaması
- **Bağlam:** Yalnız V2 geliştirme dalı `madsc/v2-discovery-bulk-20261031`. Ana İBO listesi, `main`, YEDEKLER, YENİLER, FAVORİLER, PR #9 ve eski depo kesinlikle değiştirilmedi. Tüm denetimler kaynakların M3U dosyalarını salt okunur indirir; **video/ses stream URL'lerine hiçbir istek atmaz**, IPTV cihaz testini üstlenmez.
- **Kod:** `b040e2914dcde203bb028fa896ecf30634be5830` tam M3U içerik/URL SHA256 küme denetimini ve koruma regresyonlarını aynı `V2 Turkish M3U Source Coverage and Historical Loss` toplu işine bağladı. `0d2fc8bddf359b201d7707c5f68385d7fd9243a2` HTTP dışı (UDP/RTMP/RTSP vb.) `EXTINF` referanslarını bozuk URL gibi saymayı düzeltti. `27d35dc0a8d2511b94048a3f36a48a6d22f3dc94` eşleşmemiş `EXTINF` testini doğru hata sınıfına aldı. `e068cf9540660bf188086ad483c46dcf46edb83a` eski `github-auto-*` kaynakların kaybolmasını ayrı denetim maddesi yaptı. Tüm iş tek konu bazlı toplu testtir.
- **Gerçek son kaynak dosyası sonucu:** Actions run `41644493862` **SUCCESS, 54/54 unittest**. 47 korunmuş kaynak tanımı; biri upstream silindiği için tarihî kayıt olarak kapalı, **46 aktif M3U başlığı erişilebilir**. Bu 46 dosyanın tamamı tam okunabildi, toplam **24.955 benzersiz HTTP(S) yayın URL SHA256** görüldü. Dosya/EXTINF eşleşmesinde **43 kaynak temiz** (31 yalnız HTTP(S), 12 HTTP(S) ile birlikte desteklenmeyen protokoller), **3 kaynak ek inceleme gerektirir**: `free-tv-independent` 6, `discevisita-tr` 19, `onureroz-turk-karma` 1 eşleşmemiş EXTINF = **26 gerçek eksik/sorunlu satır**. 90 HTTP dışı referans vardır; bunlar kayıp/bölüm hata sayılmaz. Geçerli 24.955 URL kimliğinin hiçbiri bozuk satır ayıklaması yüzünden arşivden silinmez.
- **Gerçek 4.955 kurtarma ile güncel feed kıyası:** 4.955 geçmişte video decode edilmiş ve #72'de eksik kalmış tarihî kimlikten **2.312'si şu anda bu 46 aktif kaynakta exact SHA256 karşılığıyla tekrar var**, **2.643'ü bu güncel M3U dosyalarında yok**. Yokluk ölüm, oynatılamama, Türkçe dil veya cihaz hatası kanıtı değildir. 4.955/4.955 asıl tarihî URL'lerin Stage 3 şifreli kurtarma kanıtı korunur.
- **Eksik kaynağın somut kök nedeni:** #60/#72 tarihî source audit içinde, mevcut 47 sabit config'e karşılık gelmeyen **17 eski dinamik kaynak kimliği** var; bunların `old_only_url_identities` toplamı **8.449**. En büyükleri `github-auto-7` 4.682 ve `github-auto-8` 1.854 tarihî old-only URL. Bu, toplam tarihî kayıp 13.911'in alt kümesidir; 8.449'u yeniden sayıp ekleme. Geliştirme dalı checkout'ında `v2/reports/github-source-discovery.json` yok, `v2/config/approved-github-source-sha256.json` içinde **0 onaylı URL SHA256**. Tarihî isimlerden URL uydurulmaz; onaysız yeni kaynak sessizce içeri alınmaz.
- **Koruma ve açık işler ayrımı:** Türkçe M3U **kaynak erişimi, tam içerik sayımı, kök neden/kayıp tanısı ve toplu regresyon** tamamlandı ve yeşil. Buna karşın 3 upstream beslemedeki 26 eşleşmemiş kayıt, 17 dinamik kaynak envanter boşluğu, güncel listelerde yeniden görünmeyen 2.643 tarihî URL ve canlı video/ses oynatma kontrolü **otomatik çözüldü denmez**. Bunlar takip/karantina ve son bütünleşik kaynak doğrulama konularıdır; çalışır link uydurma, kayıp URL silme ve otomatik ana playlist yayını yasak.
- **Kanıt:** `41644493862` SUCCESS; artifact `13233323845` anonim `turkish-m3u-source-loss.json` ve toplu test logu. Önceki kök tespit `41641788187` SUCCESS (46/46 etkin kaynak başlığı ve 4.955/4.955 tarihî hash), kaynak kapatma `7d1660ba...`, kaynak provenans ayırımı `dd91e185...`. Son tamamlanan kaynak içerik raporu **REVIEW_REQUIRED** statüsünü dürüstçe taşır; CI SUCCESS raporun bütünlükle üretilip testlerin geçtiğini gösterir, eksik upstream içeriklerin onarıldığını göstermez.

## 3 Kasım 2026 — Türkçe M3U kaynak kurtarma: #60 dinamik kaynaklar, 8 canlı kanıt, 41 satır karantinası
- Çalışma dalı yalnızca `madsc/v2-discovery-bulk-20261031`. **Korunan ana İBO playlisti, main, YEDEKLER, YENİLER, FAVORİLER, cihaz favorileri, eski depo ve PR #9 değiştirilmedi.** Yeni geniş kanal taraması manuel final aşamasına ertelendi.
- Orijinal #60 GitHub Actions run `40743765437`, artifact `12840886350` içindeki **orijinal kaynak keşif listesi**, #60/#72 geriye dönük aggregate kayıtlarıyla birebir karşılaştırılarak **17 gerçek tarihî `github-auto-*` kaynak kimliğinin gerçek M3U kaynak adresleri** geri kuruldu. Kanıtlı kimlikler `v2/history/run60-dynamic-source-ledger.json` içinde saklandı; tam eşleşme ve tekrar koruma testleri var. Bu 17 kaynakla ilgili #60'da bulunup #72'de görünmeyen 8.449 URL kimliği, genel 13.911 tarihî kayıp kimliğin **alt kümesidir**; tekrar sayılmaz.
- Yeni `v2/run60_source_ledger.py`, `v2/test_run60_source_ledger.py`, tam içerik SHA256 kıyasları; `github-auto-8` orijinal listesi **headerless `#EXTINF`** olduğu için sadece kanıtlı tarihî kaynaklara izin veren `#EXTM3U` normalizasyonu eklendi. İlk önce geçici indirme başarısız görülen `github-auto-6` sonraki doğrulamada okunabildi. **17/17 tarihî kaynak konumu geri kazanıldı**, ancak sağlayıcılardan gelen M3U içeriklerinde geçerli olmayan kayıtlar otomatik düzeltilmez.
- Orijinal 46 aktif M3U'ya 17 doğrulanmış tarihî GitHub feed'i eklenerek **63 etkin dosya / toplam 64 tanım (1 eski kapalı)** incelendi. Son gerçek toplu kaynak kanıtı: Actions **`41650576939` SUCCESS, 68/68 test**, artifact **`13237032871`**, **33.628 benzersiz HTTP(S) URL SHA256**; tam ayrıştırılan **60/63**; orijinal **4.955/4.955** tarihî URL kimliğinin **4.947'si bu güncel kaynaklarda birebir SHA256 eşleşti**, **8'i kaynaklarda yok**. 33.628 URL kimliği bağımsız Türk kanalı veya güncel video oynatma sayısı değildir.
- Sekiz ayrı tarihî SHA kimliği **V2 Git geçmişinden %100 exact hash ile gerçek URL olarak kurtarıldı**; `v2/historical_targeted_playback.py` ve `v2/test_historical_targeted_playback.py` korumalı, yalnız sekiz URL için toplu FFprobe denetimi eklendi. İlk üç medya çalışmasında eksik/uyumsuz ffprobe komut seçenekleri düzeltildi (`ffprobe` kurulumu, `-max_redirects`, `-nostdin`). **Son geçerli video/ses koşusu `41649713460` SUCCESS**, artifact **`13236373238`**: **6/8 URL için video ve ses akışı gözlendi**; **bir HTTP 403 ve bir HTTP 404** (geçmiş kimlikler Arica TV ve Antena Stars; Türkçe kanal oldukları kanıtlanmadı). 403/404 sebebiyle tarihî kayıtlardan silme yok, cihazda İBO oynatma iddiası yok. Bu medya testi sadece sekiz tarihî URL'yi kapsadı; 33.628 adayın tümünün video/audio testi yapılmadı.
- M3U satır kayıp analizinde `free-tv-independent` içindeki altı adet **`[NO PUBLIC STREAM]`** yer tutucusu bozuk URI diye sayılmıyor; eksik gerçek akış URL'si gösterilmeden saklandı. 90 HTTP dışı referans ayrı tutuldu. Gerçek yanlış/eksik EXTINF kaydı **41**: `discevisita-tr` 19 (kayıt sonrası URI eksik); `onureroz-turk-karma` 1 (geçersiz/göreli URI); `github-auto-24` 21 (20 eksik URI, 1 geçersiz/göreli). **41 kayda ait `line_number`, `extinf_sha256` ve sabit hata türü** ile, URL/channel adı/token içermeyen karantina kanıtı `v2/m3u_source_content_audit.py` içine işlendi. Son kod commit'i **`f1aef2e8bf8438fa1b150cff043a7450715434dc`**. Kaynak sağlayıcısında URI bulunmadığı için URL uydurulmadı; doğru görünmeden "tam onarıldı" denmez. Kaynak içerik raporu **`REVIEW_REQUIRED`**, çünkü 60/63 tam ayrıştırılmıştır; GitHub CI başarısı yalnız testlerin ve raporlamanın başarılı olduğunu gösterir.
- `v2/discover.py` artık `--include-original-run60-github-sources` ile 17 provenanslı özgün kaynağı gelecek tek **manuel** Worldwide keşfine ekleyebilir (commit `5cf3297d3f692b9999956dc7da6075f2c55d602a`, CI `41650001790` SUCCESS, 67 test). Ana playlisti otomatik düzenleme yok, synthetic URL yok, tahmini kanal birleştirme yok. Orijinal 4.955 kayıt şifreli tarihî kurtarma kanıtlarında korunur; son canlı video/ses doğrulamasının kapsamı yalnızca sekiz hedef URL'dir.
- **Durum sınırı:** Türkçe M3U kaynak kimliği kurtarması, kayıp envanteri ve aynı konudaki toplu regresyonlar tamamlandı; 41 upstream eksik URI çözülmeden "tüm kaynaklar kusursuz" denemez. Sonrası: sağlayıcıların gerçek güncellenmiş yayın adresi varsa kanıtlı biçimde eşleştirmek; projenin hazırlık işleri bittiğinde final geniş toplu video/audio ve kullanıcının İBO cihaz testi.

## 3 Kasım 2026 — Türkçe M3U: 4 kaynak, 55 bozuk satır / 50 kimlik, 4 doğrulanmış AV ve toplu kapanış kanıtı
- Kapsam: **yalnız `Madsc55/MADSC55-TV-V2` geliştirme dalı `madsc/v2-discovery-bulk-20261031`**. `main`, eski depo, PR #9, `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER, YENİLER, FAVORİLER ve cihaz favorileri değiştirilmedi. Büyük yeni kanal araması yapılmadı; yalnız mevcut 63 M3U kaynak belgesinde eksik olduğu önceden tespit edilen metadata ve orijinal sürümlerdeki birebir kanıtlar denetlendi.
- Tarihî kaynak kurtarma korunuyor: #60 orijinal kaynak arşivinden **17/17 dinamik GitHub kaynak konumu** çıkarıldı ve gelecekteki **manuel** V2 tarama girişine bağlandı. **4.955/4.955 orijinal tarihî URL kimliği** halen korunuyor; **4.947'si güncel 63 M3U kaynağında birebir SHA256 ile bulunuyor; 8'i bu kaynaklarda yok**. Önceki sekiz URL'lik bağımsız sınırlı FFprobe run `41649713460`: 6 video+ses gözlemi, 1 HTTP 403, 1 HTTP 404; bu 8 kimlik tarihî envanterden silinmedi. Bunlar farklı bir kanıt kümesidir, aşağıdaki dört onarımla karıştırılmamalı.
- Bozuk M3U satırlarının genişletilmiş kaynak kıyası: `discevisita-tr` 19; `github-auto-24` 21; `onureroz-turk-karma` 8; **eklenen `onureroz-turk-all` 7** = **55 bozuk satır örneği**, ancak birden fazla listede aynı `EXTINF` bulunduğundan **50 farklı SHA256 metadata kimliği** ve 5 tekrar. Nedenler: **39 kayıt sonrası gerçek URI yok**, **14 HTTP URI'de ana makine adı yok**, **2 geçersiz/bağıl URI**. Eski 41 sayısı bu 55'in alt kümesiydi; 14 hatalı HTTP satırı önceki okuyucu tarafından yanlışlıkla geçerli sayılıyordu. 6 kasıtlı `[NO PUBLIC STREAM]` yer tutucu ayrı tutuluyor ve bu sayıya dahil edilmiyor.
- Ayrıştırıcı düzeltmesi `2fd98f1f043e330e743ed3e18acb28a8de25b395`: `v2/discover.py` artık `http://` veya `https://` ile başlayıp **hostname taşımayan** bozuk referansları aday URL diye içeri almıyor; özgün kaynak dosyaları ve kanal metadata kayıtları otomatik silinmiyor. `v2/m3u_source_content_audit.py` bunları SHA256+satır numarası+sebep ile açıkça karantinaya işliyor.
- Düzeltme/onarım kanıtı `832af1e6190c7652a0be8a54f61997594f8f5a49`, `134ef2e232493f76792981da83a595363729199c`, `b23d52fe560bfbf08d4d8f60fc5aae561e96c361`: 20'şer gerçek Git geçmiş sürümü, yayımlayıcının iki resmî Onur Eröz alternatifi, önceden konfigüre edilmiş **63/63** kaynak ve birebir metadata/EPG kimliği çapraz kıyası tamamlandı. **16 farklı tarihî/resmî/mevcut kaynak URL adayı** anonim SHA256 ile doğrulandı; **4 benzersiz URL FFprobe video+ses testinden geçti**, video+ses kanıtı RSA+AES-GCM ile `three-source-av-verified.sealed` dosyasına alındı. Başarılı dört eşleşme: Kuzey Kıbrıs TV ile **ZDF, 3sat ve Welt**. Bu son üçü Alman kanallarıdır ve Türkçe ana listeye taşınmadı. Kuzey Kıbrıs TV için konuşulan Türkçe dili/IBO cihaz testi kanıtlanmadı. Kalan **51 bozuk satır örneği / 46 benzersiz metadata kimliği** için bugün AV doğrulanmış, güvenilir eşleştirme bulunmadı; URL uydurulmadı veya silinmedi.
- İş akışı kanıtları: **`41656341381` SUCCESS, 69/69 toplu kaynak/parser/koruma testi**, artifact `13238674475`; **`41656937616` SUCCESS, 63/63 toplu dört-kaynak tarihî/alternatif/AV ve regresyon testi**, artifact `13239268429`. Kaynak raporu `REVIEW_REQUIRED` kalır: 63 etkin kaynağın **59'u tam ayrıştırıldı, 4'ünde upstream bozuk kayıt var**. Sağlayıcının orijinal dosyaları ve yeni URL'leri bizim değiştirmemiz mümkün olmadığından açık kaynakta 46 tekil metadata kimliği hâlâ kanıtlı oynar URL bekliyor.
- Ayrı kullanıcının sohbetine verilen kalıcı SHA-kanıt dosyası: `MADSC55_V2_M3U_SHA_KAYIP_KANITI_20261103.json` SHA256 **`89e458e12fe95e10461a07e4ca273a3828af853dad8c4ab451dbd7d6a9aa19cd`**, 55 kaynağa özgü satır kaydı, 50 benzersiz kimlik ve dört doğrulanmış AV kanıt hash'ini içerir, **çıplak yayın URL veya token içermez**. Başarılı dört akışın şifreli kanıtı `MADSC55_V2_DOGRULANAN_4_YAYIN_SIFRELI.sealed` SHA256 **`9824dacb01d32cdccf583c3970ed94cce8b234a093f960cebf3656b39a6f5fdc`**. Şifreli çıktıyı açmak için karşılık gelen özel RSA anahtarı gerekir; anahtar GitHub'a veya bu notlara eklenmedi.
- **Açık kalan sınır**: Upstream sağlayıcıların kendisinde gerçek URL verilmeyen/kusurlu 46 benzersiz metadata kimliği; bugünkü video/ses başarısı olmayanlar İBO'da çalışan kabul edilmez. Sonraki geniş tarama ve cihazda İBO Player doğrulaması ancak korunan ana playlisti etkilemeyen ayrı paketlerle yapılır. Hata vermiş veya kayıp geçmiş adaylar arşivden asla silinmez.

## 3 Kasım 2026 — Türkçe M3U eksik kayıtların son toplu kurtarma ve deduplikasyon kanıtı

- **Güncel kapsam (eski 2.643 ve 17 eksik sayılarının yerine):** Gerçek #60 kaynak keşif arşivinden **17/17 dinamik GitHub kaynak kimliği ve özgün M3U doküman adresi** kurtarıldı; bunlar manuel keşif modülüne de bağlıdır. Orijinal **4.955/4.955 tarihî SHA-256 URL kimliği** şifreli aşama-3 arşivinde korunur; 63 etkin M3U kaynak içeriğinde **4.947/4.955** birebir URL hash'i yeniden gözlendi. Kalan **8/4.955** tarihî URL Git geçmişinden birebir çıkarıldı; önceki sınırlı FFprobe testinde **6 video+ses**, bir **403** ve bir **404** sonucu vardı. Bunların hiçbiri kayıttan silinmedi. 4.947 URL'nin bugün video/ses sağladığı bu karşılaştırmadan kanıtlanmaz.
- **Güncel bozuk doküman satırları (4 kaynak):** Son M3U kaynak bütünlük koşusu `41656341381` **SUCCESS**: 63 aktif M3U kaynak içinde **59 tam ayrışan, 4 inceleme gereken**; bunlarda toplam **55 bozuk veya eksik EXTINF/URI satırı** var: `discevisita-tr` **19**, `github-auto-24` **21**, `onureroz-turk-karma` **8**, `onureroz-turk-all` **7**. Son iki kaynağın tam metadata SHA karşılaştırmasında **5 tekrar** var; yani 55 satır = **50 benzersiz bozuk EXTINF kimliği**. Bunlar 55 ayrı Türk kanalı diye sayılmaz. Bozukluğun türleri: **39 kayıt sonrası URI yok, 14 host adı olmayan HTTP URI, 2 geçersiz/göreli URI**. Free-TV'deki 6 bilerek yazılmış `[NO PUBLIC STREAM]` işareti ve 90 HTTP dışı protokol referansı bu 55 bozuk satıra katılmaz. Açık HTTP URL/kimlik bilgileri GitHub raporuna yazılmadı.
- **Dört kaynak için son hedefli kurtarma:** `v2/orphan_m3u_recovery.py` 4 kaynak ve 63 önceden tanımlı kaynak üzerinde yalnız özgün `EXTINF` eşleşmesi veya kesin EPG kimliği+tam kanal adı eşleştirmesi yapar; 17 eski kaynak kanıtını da korur. Önce eski Git tarihinin 20 sürümü, ardından **35 sürümü** karşılaştırıldı. Son koşu **`41657354333` SUCCESS, 63/63 toplu regresyon testi**, şifreli ve anonim artifact `13240197472`. **35+35 Git sürümü başarıyla okundu**; eski/var olan kaynaklardan **18 tekil gerçek URL adayı** bulundu. Bunlardan FFprobe ile **4 ayrı URL'de video+ses** görüldü (Kuzey Kıbrıs TV, ZDF, 3sat, Welt), **Sözcü TV'ye ait ek bir URL'de video var fakat ses gözlenmedi**; bu sonuncusu video+ses kabulüne alınmadı. Dört video+ses URL, artifact içindeki RSA ile mühürlenmiş aktarım çıktısında; ana M3U listesine eklenmedi. ZDF, 3sat ve Welt Alman kanallarıdır, Türkçe sayılmaz. Toplam **50 eşsiz bozuk metadata kimliğinin 4'ünde** sesli-görüntülü kanıt; **46 eşsiz kimlikte** cihaz/bugünkü video+ses kanıtı henüz yok. Satır bazında 55'in 4'ü doğrulanmış, 51 satırı doğrulanmamıştır.
- **Hata nedenleri ve sınır:** Bazı haricî kaynaklarda yayın adresi hiç belirtilmiyor, bazılarında host adı yok; bu bilgilerden geçerli stream URI'si yeniden üretilemez. Kaynak sahibinin güncellemesi ya da birebir güvenilir tarihî/eşdeğer URI kanıtı olmadan 46 kimliğe sahte URL eklemek yasak. Test edilen URL'nin FFprobe sonucu İBO Player cihaz testi değildir. Kaynak kapsamı/doğrulama raporları **REVIEW_REQUIRED** statüsünde kalmalı; GitHub Actions **SUCCESS** kod/test çalışmasının yeşil olduğunu, tüm upstream yayınların onarıldığını söylemez.
- **Koruma:** `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` içeriği, YEDEKLER ilk TRT 1/DHA kanalları, YENİLER, FAVORİLER, main, PR #9 ve eski `madsc-tv` deposu değiştirilmedi. Yeni dünya genelinde kanal keşfi yine ertelendi. Kurtarma araçları yalnız geliştirme dalında, salt okunur kaynak kıyası + anlık test + RSA şifreli kanıttır. Sonraki işlerde aynı 55 satır/50 kimlik ve 8 tarihî kayıp tekrar sıfırdan sayılmayacak.

## 3 Kasım 2026 — 35 tarihî sürüm ve EPG-kimliği eşleştirmesi ile M3U kurtarma son kanıtı
- **Çalışma yalnız `Madsc55/MADSC55-TV-V2` üzerindeki `madsc/v2-discovery-bulk-20261031` geliştirme dalında.** `main`, ana İBO playlisti, YEDEKLER, YENİLER, FAVORİLER, cihaz favorileri, eski depo ve PR #9'a dokunulmadı. Ana playlistin geliştirme dalındaki değişmez Git blob SHA'sı `4b1c3cea4b5107a425abab60f62d41f9f81e05a7` olarak yeniden kontrol edildi; main dalındaki blob bu dalla zaten farklıdır, iki dalı karıştırma.
- Daha önceki **17/17 özgün tarihî GitHub kaynak eşleştirmesi ve 4.955/4.955 tarihî URL kimliği koruması** geçerlidir. **4.947** geçmiş URL mevcut 63 etkin kaynak dosyasında SHA-256 birebir bulundu, diğer **8** gerçek URL Git geçmişinde kurtarıldı: sınırlı mevcut koşuda 6 video+ses, 1 HTTP 403, 1 HTTP 404; hiçbir kayıt silinmedi. 4.947 URL'nin bugün oynadığı/İBO'da açıldığı bu raporla kanıtlanmaz.
- 63 aktif kaynakta 4 sorunlu kaynak var: `discevisita-tr` 19, `github-auto-24` 21, `onureroz-turk-karma` 8, `onureroz-turk-all` 7 = toplam **55 kaynak satırı**, ancak son iki Onur listesinde **5 birebir metadata tekrarı** nedeniyle **50 farklı `EXTINF` SHA kimliği**. Tür dağılımı: 39 `EXTINF` sonrası URI yok, 14 hostu olmayan HTTP URI, 2 geçersiz/göreli URI. 6 `[NO PUBLIC STREAM]` yer tutucu bu sayıya katılmaz. Kaynak satırı/kanal kimliği silinmez.
- `c0a6adc39945df3c6f630cfc93447e3d8bc9d48d` ile iki orijinal GitHub kaynağının geçmiş doğrulaması 20'den **35'er sürüme** çıkarıldı. 35+35 tarihlendirilmiş orijinal dosyanın tamamı okunabildi. `18d3004bbb3319f7555ba6cb5774b430d07a44f4` ile eski `EXTINF` tam satırı logo veya kategori değiştiği için tutmasa bile yalnız **birebir EPG kimliği + birebir kanal adı** karşılaştırmasına izin veren ek kurtarma geliştirildi; yanlış ID/isim eşleştirmesi testle reddedilir. Bunlar yeni kanal arama işlemi değildir; yalnız 4 bilinen bozuk upstream dokümanına yönelik salt-okunur restorasyon.
- En son toplu doğrulama GitHub Actions **`41658208634` SUCCESS**, **65/65** unittest, anonim + RSA mühürlü artifact **`13240098553`**. **55 farklı geçmiş/var olan URL adayı** ortaya çıkarıldı; `github-auto-24` içindeki 21 bozuk satırın **17'si** için tarihî URL adayları var, ama bu adayların hiçbiri son FFprobe ses+video kanıtını geçmedi. 55 adaydan **4 gerçek URL** video+ses doğrulaması aldı ve yalnız RSA ile mühürlendi (Kuzey Kıbrıs TV, ZDF, 3sat, Welt); **Sözcü TV'nin bir URL'sinde video görüldü ama ses görülmedi**, bu nedenle AV-verified sayılmadı. Diğer 50 adaya erişim başarısız/güvensiz/DNS yok; video+ses başarısızlığı kesin yayın ölümü değildir.
- **Açık sınır:** 50 farklı bozuk metadata kimliğinden **4** tanesinde güncel ses+video kanıtı; **46** benzersiz kimlik için henüz ses+video kanıtı yok (**55 kaynak satırından 51'i**). Sağlayıcı kaynağında gerçek URI verilmeyen satırları isimden/tahminden URL üreterek doldurmak yasak. Dört doğrulanmış URL de kullanıcı İBO cihaz testini henüz geçmedi. Dünya genelinde yeni kanal taraması son adıma ertelendi; korunmuş ana playlist otomatik güncellenmez.
- Raporun `REVIEW_REQUIRED` olması doğrudur; CI testlerinin `SUCCESS` çıkması bütün upstream bozuk satırların onarıldığı anlamına gelmez. Bir sonraki devamda **17 kaynak kimliği kurtarma, 2.643 eksik URL ve 41 satır eski rakamları** yeniden yapılacak iş gibi tekrarlanmamalı; güncel doğrulanmış durum **17 kaynak kurtarıldı, 4.955 kimlik korundu, 4.947 kaynaklarda görüldü, 8 ayrı FFprobe denendi; 4 kaynak/55 satır/50 eşsiz bozuk metadata ve 4 ses+video doğrulaması**dır.

## 3 Kasım 2026 — 485 Git sürümü, 107 gerçek aday ve eksiksiz şifreli URL koruma
- **Çalışma kapsamı:** Yalnız `Madsc55/MADSC55-TV-V2` deposundaki `madsc/v2-discovery-bulk-20261031` geliştirme dalı; `main`, ana İBO playlisti, YEDEKLER, YENİLER, FAVORİLER, cihaz favorileri, eski `madsc-tv` deposu ve PR #9 korunur. Büyük yeni kanal keşfi çalıştırılmadı. Kullanıcı İBO Player cihaz testini ayrı yapacak.
- **Önceki 2.643 ve 17 eksik sayıları güncel değil:** 17/17 tarihî `github-auto-*` M3U kaynak kimliği orijinal GitHub #60 kanıtıyla geri kuruldu. **4.955/4.955** tarihî stream URL kimliği kurtarılmış ve şifreli aşama-3 veri korumasında. Bilinen 63 etkin M3U kaynakta **4.947** tarihî hash birebir görünüyor, kalan **8** birebir Git geçmişinde mevcut ve FFprobe ile sınırlı olarak denendi (6 video+ses; 1 HTTP 403; 1 HTTP 404). İBO cihaz oynatma kanıtı yok.
- **Kalan dört haricî M3U kaynak dosyasındaki doğrulanmış sorun:** `discevisita-tr` 19, `github-auto-24` 21, `onureroz-turk-karma` 8, `onureroz-turk-all` 7 satır = **55 bozuk URI satırı / tekrarlar temizlenince 50 ayrı EXTINF metadata kimliği**. Sebepler 39 eksik URI, 14 host adı bulunmayan HTTP URI, 2 geçersiz/göreli URI. Free-TV altı adet `[NO PUBLIC STREAM]` ifadesi ve 90 HTTP dışı protokol URI'si bunlara dahil edilmez. Haricî sağlayıcıların değiştirmediği bozuk URI'ler otomatik "iyileşti" sayılamaz.
- **Yeni derin tarihî inceleme:** `58803b43057bf8df98784ef3763483805f3121e9` gerçek GitHub REST sayfalamayı, sınırlandırılmış paralel geçmiş erişimini ve toplu güvenlik regresyonlarını ekledi; 150'şer eski sürüm kontrolü `41659782649` **SUCCESS, 68/68** olup 98 tarihî aday verdi. `a1a263d282fe658b7cc6b0e3f84c2c1895dfa337` ile limit 300'e yükseltilerek **iki kaynak deposundaki tüm 273+212=485 tarihî Git commit'i listelendi; 484 M3U arşiv dosyası okunabildi, bir eski kaynak dosyası erişilemedi ve ayrı hatada saklandı**. Son kaynak kanıtı Actions **`41661347263` SUCCESS, 72/72 toplu regresyon**; artifact **`13241662530`**. 107 farklı gerçek tarihî URL adayı SHA256/provenans kanıtıyla elde edildi, tahmin kullanılmadı.
- **Veri kaybı sorununun somut çözümü:** Eski kod yalnız video+ses testini geçen az sayıdaki URL'yi şifreli dosyaya alıyordu; bugünkü ağ hatası veren **kalan gerçek tarihî URL adayları yeniden kaybolma riski taşıyordu**. `f347e5b770e8ffb5be936bf4a4116d4a8967bdc8` tüm adayların kaynak kimliği, orijinal EXTINF SHA, geçmiş Git commit kanıtı ve video/ses durumuyla **ayrı RSA-OAEP-SHA256 + AES-256-GCM `.sealed` dosyasına** korunmasını ekledi. Son artifact `13241662530`: `three-source-all-historical-candidates.sealed` = **107 farklı URL**, `three-source-av-verified.sealed` = **4 video+ses doğrulanmış URL**, `three-source-orphan-anonymous.json` = açık URL içermeyen rapor ve `three-source-orphan-regressions.log` = 72/72 başarılı test. 103 URL ses+video doğrulanmamış olsa da kanıtlı özgün adres olarak şifreli ve kayıpsız tutulur; `failed stream` ≠ `dead stream`.
- **Son açık sınır:** 50 eşsiz bozuk metadata kimliğinin **4'ü** güncel video+ses kanıtına sahip; **46'sı** henüz güncel video+ses kanıtı olmadan korunuyor. Toplu geçmiş taramasından çıkan 107 adayın 103'ü test anında ses+video veremedi veya güvenli erişim kuralı tarafından reddedildi. Bu, sağlayıcının gerçek URL vermediği 46 kimliğe tahmini/sentetik URL yazmayı meşrulaştırmaz. Testler yeşildir; ancak kaynak içerik raporunun `REVIEW_REQUIRED` olmasını iptal etme. `main` ve ana İBO listesi değiştirilmez. Gelecekteki yalnız kaynağı kanıtlanmış güncelleme ve cihaz testi ayrı aşamadır.

## 3 Kasım 2026 — 50 orphan kimliği süresiz Git korumasına alındı ve yeni upstream URI kurtarma kapısı doğrulandı
- **Dal ve sabit kapsam:** Yalnız `Madsc55/MADSC55-TV-V2` `madsc/v2-discovery-bulk-20261031` geliştirildi. Korunan ana `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` (bu daldaki blob `4b1c3cea4b5107a425abab60f62d41f9f81e05a7`), YEDEKLER ilk TRT 1/DHA, YENİLER, FAVORİLER, cihaz favorileri, `main`, PR #9 ve eski repo değiştirilmedi. Yeni geniş IPTV kanal taraması başlatılmadı; yalnız dört bilinen kusurlu M3U belgesinin salt-okunur hedefli incelemesi yapıldı.
- **Kesin başlangıç kanıtı:** Önceki orijinal #60/#72 karşılaştırmasında 4.955/4.955 tarihî URL kimliği kurtarılmış ve korunmuştu; 4.947 URL hash'i 63 etkin kaynak dosyasında yeniden göründü. Kalan 8 gerçek URL Git geçmişinden birebir kurtarılıp sınırlı FFprobe ile denendi (6 video+ses; 1 HTTP 403; 1 HTTP 404). 17/17 tarihî dinamik GitHub kaynak konumu geri kazanıldı. Eski "2.643 URL bulunamadı, 17 kaynak eksik" durumu artık güncel değildir.
- **Sorunlu güncel M3U:** Dört bilinen upstream kaynakta **55 sorunlu EXTINF/URI satırı = 50 benzersiz tam metadata SHA256 kimliği**. `discevisita-tr` 19, `github-auto-24` 21, `onureroz-turk-karma` 8, `onureroz-turk-all` 7 (son iki kaynakta beş tekrar). Bunların **4 benzersiz kimliğinde güncel video+ses kanıtı**, **33'ünde kanıtlı URL adayı var ama AV doğrulanmamış**, **13'ünde güvenilir URL adayı henüz yok**. 50 kimliğin 46'sı bugünkü video+ses kanıtından yoksun. Adresi eksik satıra sahte URL uydurulmaz, içerik bilinmeden Türkçe kanal denmez.
- **Kalıcı SHA envanterindeki yeni somut düzeltme:** Eski anonim kanıt artifact `13241662530` eninde sonunda süresi dolacağından, yalnız Actions artifact tutmak 55 bozuk satırın tarihî kimliğini kaybettirirdi. `9f553f7b7d8ae1c8c39808bd0da8b3cec3aaa7f5` commit'i `v2/history/m3u-orphan-50-hash-baseline.json` içinde özgün `three-source-orphan-anonymous.json` dosyasının SHA256 ile bağlı, zlib/base64 sıkıştırılmış **tam 55 kaynak bazlı SHA kimliğini** V2 Git geçmişine kalıcı olarak kaydetti. `v2/orphan_baseline_guard.py` dosyası özgün 55/50 kaydını doğrular, dört kaynağın bugünkü tam EXTINF kimlikleriyle tek tek eşleştirir, bir kimlik URI olmasa bile kaynak dosyasından kaybolursa bunu `LOSS_RISK_REVIEW_REQUIRED` diye açık kanıtla raporlar; yeni URI bulunduğunu playback doğrulaması diye göstermeyi reddeder.
- **Yeni URI kurtarma mekanizması:** `bb1dbf398aea09f09e7e6adf5bee9aa707392730` commit'i `v2/orphan_m3u_recovery.py` ve toplu testlerine `candidate_repairs_from_current_verified_sources` ekledi. Haricî sağlayıcı kayıp EXTINF kimliği altına gelecekte geçerli HTTP(S) URL koyarsa aynı özgün source ID + SHA256 ile yakalanır, yalnız hedefli FFprobe kontrolüne alınır, video+ses başarılıysa RSA/AES-GCM özel arşive alınır. Eski URI hâlâ bozuksa kayıt `STILL_UNPAIRED`, metadata bütünüyle kaybolmuşsa `LOSS_RISK` olarak kalır. İBO cihazında oynama ayrıca kullanıcı tarafından sınanır; otomatik ana playlist yazımı yok.
- **Son toplu koşu:** GitHub Actions `41669860900` **SUCCESS, 81/81 unittest**, artifact `13247127468` RSA şifreli aday URL arşivleri + anonim JSON + test günlüğü. Gerçek kaynak raporunda `immutable_orphan_identity_guard.status=NO_ORIGINAL_METADATA_IDENTITY_LOSS`, `original_source_occurrences_still_present=55/55`, `original_occurrences_missing_metadata=0`, `original_occurrences_with_current_valid_source_uri=0`. 485 tarihî Git commit'i ve bilinen 63 kaynak içerik karşılaştırması sonucu **107 gerçek tarihî aday**, **4 video+ses doğrulanmış aday**, **103 henüz doğrulanmamış aday** RSA-OAEP-SHA256/AES-256-GCM şifreli dosyalarda korunuyor. Böylece bugünkü ağ/oynatma başarısızlığı nedeniyle tarihî adresler tekrar silinmiyor.
- **Mevcut dış kaynak sınırı:** 46 benzersiz metadata kaydı için bugün AV kanıtı sağlanamadı; 13'ü için bilinen kaynaklarda gerçek URL adayı bile yok, 33'ünün eski bağlantıları var fakat erişim/DNS/403/codec/ses gibi sebeplerle doğrulanmıyor. Bu 46 kaydı düzeltilmiş sayma; kaynak sahibi geçerli URI sağlar veya güvenilir, birebir kanıtlı yeni alternatif çıkarsa aynı korumalı işte topluca test et. Bu ayrım projenin DEVAM_NOTU'nda korunsun, önceki kapsam yeniden taranmış gibi raporlanmasın.


## 3 Kasım 2026 — Aşama 5, bağımsız şifreli arşiv kabulü / toplu CI
- Çalışma dalı: `madsc/v2-discovery-bulk-20261031`. Önceki doğrulanan commit `fd56a192`; kabul güvenliği düzeltmesi `616b2c49b3c176fd90653f105e0731e8ea710282`.
- `v2/archive_acceptance_gate.py` artık yalnızca JSON bayrağı ve SHA eşleşmesini yeterli görmüyor: AES-256-GCM ile gerçek restore, doğrulanmış V2 manifesti, değişmez 4.955 kimliğin tam metadata eşleşmesi, bağımsız kaydedilmiş beklenen SHA-256 ve özel dosya izinleri zorunlu.
- `v2/independent_s3_restore.py` ile sürüm numarası açıkça verilen özel S3 nesnesi AWS API üzerinden yeni çalışma ortamına indirilip yeniden açılabiliyor. S3 yanıtındaki nesne sürümü ve bağımsız sabitlenen özgün checksum eşleşmeden kabul yok. Gerçek üretim koşusu için kimlik doğrulama, sürümlü S3 nesnesi ve `V2_ARCHIVE_KEY_HEX` gereklidir; depodan secrets okunamaz.
- `.github/workflows/v2-independent-archive-restore.yml` adlı ayrı offsite kabul iş akışı eklendi. Geliştirme dalındaki push tetiklemesi yalnız offsite nesne değişkenleri tanımlıysa çalışacak; tanımlı değilse **üretim kabulü yapılmış sayılmaz**. Manuel workflow_dispatch yalnız GitHub tarafından kullanılabilir hâle getirildiğinde/varsayılan dal kısıtları izin verdiğinde işlevseldir.
- Gerçek GitHub Actions sonuçları, commit `616b2c49`: Eight-Stage run 41685806258 **SUCCESS**; Master Engine run 41685806240 **SUCCESS**; Current Scanner Offline Gate run 41685806227 **SUCCESS**; Actions Status Monitor run 41685806252 **SUCCESS**.
- Master Engine grouped unittest: **339 tests, OK**, yeni şifre çözme, sahte arşiv reddi, şifreli 4.955 satırlık immutable-history snapshot ve ağsız taklit S3 yürütmesi dahil. Ağsız test gerçek offsite S3 erişimi değildir.
- **Üretim Aşama 5 kabulü AÇIK**: gerçek sürümlü bağımsız depoya yazılmış üretim şifreli arşivin uzak sistemden başarıyla yeniden indirilip, özgün anahtar ile açıldığına ilişkin gerçek offsite run ID henüz yoktur. Bunu herhangi bir yeşil offline testle eşdeğer sayma. S3 nesnesi/versiyon, AWS OIDC erişimi ve bağımsız beklenen arşiv SHA değeri sağlandığında ayrı kabul akışı gerçek denetimi yapacaktır.
- Ana İBO playlisti, YEDEKLER/YENİLER/FAVORİLER, `main`, PR #9 ve eski depo değiştirilmedi. Büyük kanal araması başlatılmadı.

## 3 Kasım 2026 — AŞAMA 5 ŞİFRELİ ARŞİV KALICILIĞI VE BAĞIMSIZ GERİ YÜKLEME: KABUL EDİLDİ
- Yalnız `Madsc55/MADSC55-TV-V2` `madsc/v2-discovery-bulk-20261031` geliştirildi. `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` sabit blob `4b1c3cea4b5107a425abab60f62d41f9f81e05a7`, `main`, PR #9, YEDEKLER/YENİLER/FAVORİLER ve eski depo değiştirilmedi; yeni dünya kanal taraması başlatılmadı.
- Tarihî gerçek #60 URL kayıtları GitHub kaynakları ve tarihli envanterden, **yeni RSA-3072 açık anahtarına** tekrar mühürlendi. 4.955/4.955 özgün URL yeni özel RSA anahtarı ile URL SHA256 ve özgün metadata eşleşmesi korunarak RAM'de geri açıldı; Actions run **41694682852 SUCCESS**, şifreli artifact **13258931483**. GitHub'a özel anahtar veya açık URL yazılmadı.
- 55 orijinal sorunlu M3U satırı / 50 benzersiz metadata kimliği için 107/107 kanıtlı tarihî URL yeniden RSA mühürlendi. Yeni özel anahtar ile açıldı; eski 107 aday SHA kimliğiyle **107/107 birebir aynı**, 4 önceki video+ses kanıtı yeniden mühürlendi; Actions run **41695537221 SUCCESS**, şifreli artifact **13260592739**.
- Gerçek 4.955+107 URL ve kaynak/EPG/hash/provenans kanıtı **AES-256-GCM** özel bütünleşik üretim arşivine kaydedildi. Arşiv: `MADSC55_TV_V2_4955_PLUS_107_FINAL_PRODUCTION_AES_20261103.enc`; SHA256 **38db9b094c48e49eb0b5b1234ddc6a109f215d6d9fa732a1a4d0cf592673fe4c**, **5.234.628 bayt**. Kullanıcının özel ChatGPT Library `/MADSC55-TV-V2/` konumunda, AES ve yeni RSA özel kurtarma anahtarları yalnız **özel** `/MADSC55-TV-V2/Private-Recovery-Keys/` klasöründe tutulur. GitHub'a key veya plaintext URL taşınmaz.
- **Gerçek bağımsız geri yükleme denendi ve BAŞARILI:** Kalıcı Library'den yeni container kopyası alındı, bağımsız sabitlenmiş SHA256 doğrulandı, AES-256-GCM açıldı, 4.955/4.955 ve 107/107 gerçek URL tekrar SHA256 ile eşleşti, tüm orijinal metadata ve 50/55 yetim kayıt kimliği korundu. Yanlış SHA, yanlış AES anahtarı, eksiltilmiş arşiv, değiştirilmiş şifreli içerik ve dünyaca okunabilir anahtar için **5/5 beklenen güvenlik reddi**.
- CI'nin özel Library dosyasına erişimi bulunmadığından gerçek offsite geri yükleme bu oturumun bağlı Library/çalışma ortamında yapılmıştır; GitHub Actions kod regresyonu bunu taklit etmez. Doğrulanmış özel kanıt özeti: `v2/history/stage5-production-acceptance-20261103.json`. Tek toplu test `v2-stage5-final-production-archive.yml` olarak ayrı tutulur.
- **Aşama 5 gerçek şifreli arşiv kalıcılığı ve bağımsız geri yükleme üretim kabulü: TAMAM.** Bu yalnız gerçek tarihî URL verisinin kayıpsız şifreli saklanması/geri yüklenmesidir; güncel akış oynatıcısı, ses/video kontrolü, Türk/Azeri son sınıflandırması ve İBO Player cihaz testi henüz kanıtlanmamıştır. Sonraki aşamalar ayrı devam edecektir.

## 3 Kasım 2026 — Aşama 5 bağımsız ikinci sağlayıcı geri yükleme kanıtı
- Nihai AES-256-GCM şifreli üretim arşivinin hem özel ChatGPT Library kopyası hem de özel Google Drive kopyası mevcuttur. İkinci kopyanın Drive dosya kimliği 1nSKpgpkHh_iNihtZBIEqF9YzNpWy6tUJ. Kullanıcıya özel erişim doğrulandı; dosya paylaşılmış değil.
- Her iki sağlayıcı kopyası ayrı indirilip orijinal 5.234.628 baytla ve değişmez SHA256 38db9b094c48e49eb0b5b1234ddc6a109f215d6d9fa732a1a4d0cf592673fe4c değeriyle karşılaştırıldı.
- Google Drive'dan ham ikili indirilen kopya bağımsız çalışma ortamında gerçek AES-256-GCM doğrulamasıyla çözülerek 4.955/4.955 tarihî URL ve 107/107 gerçek yetim URL adayı, kaynak metadata/kimlikleri bozulmadan yeniden açıldı. Private AES anahtarı GitHub'a veya Google Drive'a yüklenmedi; yalnız özel Library anahtar deposunda.
- Yanlış SHA, tahrifat, kesilmiş arşiv, yanlış anahtar ve genel okuma izinli anahtar için 5/5 beklenen reddetme doğrulandı. Bu olay 5. aşamanın gerçek tarihî URL arşivini iki bağımsız depoda saklama ve geri yükleme kabulünü tamamlar.
- Güncel akışların video+ses çalışması ve İBO Player cihaz testi bu kabule dahil değildir. Ana playlist, main, PR #9 ve eski repo korunmuştur.

## 3 Kasım 2026 — Actions tetikleyici / koruma denetimi: 58 geliştirme workflow'u ve doğrulanmış main sınırı
- **Tek aktif kapsam:** `Madsc55/MADSC55-TV-V2`, yalnız `madsc/v2-discovery-bulk-20261031` geliştirildi; V2 `main`, PR #9 ve korunan `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` değiştirilmedi. Playlistin geliştirme dalındaki Git blob kimliği **`4b1c3cea4b5107a425abab60f62d41f9f81e05a7`** ve 4.955 tarihî SHA envanteri CI ile kontrol edildi. Yeni genel kanal taraması yapılmadı.
- **Gerçek açıklık:** Geliştirme dalında toplam ilk **53** Actions workflow'u denetlendi. **13** eski playlist-yazıcı, `v2-bruksel-logo-png` ve `v2-promote-yedekler` (toplam **15**) `contents: write` + `git push` kombinasyonuyla eski playlisti veya doğrudan `main`i yazabiliyordu. Bu 15 dosya `workflow_dispatch` ve `contents: read` ile salt-okunur koruma kilidine dönüştürüldü; hash eşleşmesi dışında playlist işlemi yapamaz. `v2-epg` ile `v2-logo-backup` otomatik push/schedule ve yayınlama yerine manuel **artifact çıktısı** üretir; izinleri `contents: read`. `v2-stage3-real-history` içinde bulunmuş gizli `git add/commit/push` satırları sonradan kaldırılarak yalnız orijinal 4.955 envanterini `cmp` ile doğrular. Ağır full-decoder, GitHub/YouTube/resmî site keşfi, M3U katalog/probe/decode, tarihî replay ve S3 restore gibi işler otomatik push/schedule yerine **manuel** tutuldu. Read-only çevrimdışı CI, kaynak kapsama ve koruma iş akışlarının yalnız uygun dallardaki push tetikleyicileri korundu.
- **Ana daldaki eksik workflow dosyalarının da dev karşılığı hazırlandı:** `main`de olup geliştirme dalında bulunmayan `v2-yedekler-logos` (kilitli), `v2-real-iptv-scan`, `v2-public-source-audit`, `v2-offline-inventory` (üçü manuel, salt-okunur) eklendi. Böylece **58/58** geliştirme dalı workflow'u ve ana daldaki **40/40** özgün workflow dosya adı denetim kapsamındadır. `v2/actions_trigger_protection_audit.py`, `v2/test_actions_trigger_protection_audit.py` ve `v2-actions-trigger-protection.yml` ile tüm YAML tetikleyicilerini, izinsiz repo yazma yetkilerini, `git push/commit/add` komutlarını, yeni cron ve sınırsız push olaylarını **tek fail-closed grup** olarak kontrol eder. S3 bağımsız kurtarmada sadece manuel `id-token: write` istisnası vardır; `contents: read` korunur.
- **Toplu CI kanıtı:** Önce `8e9f39f3d89ed15acb08ec2ff5c10664889883dd` ile 40 dosyalık dev güvenlik değişikliği; ilk deneme `41702168530` eksik test bağımlılığını ve tarihî workflow'daki son `git push` satırını doğru şekilde yakalayarak **FAIL** oldu. `291b58ad38666c47fd93678783ba004b32268614` ile eksik `cryptography==44.0.2` bağımlılığı ve son yazma komutu düzeltildi. `41702558555` **SUCCESS; 54 YAML, 38/38 test, 15 publisher lock, 0 ihlal**. `d56f7b93f4e9903e82bbf54d641eebd834084337` ile main'in diğer dört workflow dosyasının korumalı dev sürümleri eklendi. Son `41703320127` **SUCCESS; 58/58 workflow, 16/16 kilitli yayınlayıcı, 38/38 toplu test, 0 ihlal**. Ayrıca playlist ve tarihî SHA değişmezliği testten geçti. Son Actions rapor artifact `13263379547`.
- **ÖNEMLİ: MAIN GLOBAL OLARAK HENÜZ KAPANMADI.** `main` üzerindeki 40 YAML dosyası ayrı ayrı okundu: **19** workflow dosyasında `contents: write` + `git push` yolu ve **16** dosyada zamanlanmış cron/schedule tetikleyici hâlâ yazılıdır. Bunlara eski `ibo-real-scan`, `v2-yedekler-logos`, `v2-promote-yedekler`, `v2-bruksel-logo-png`, `v2-epg` gibi doğrudan yazabilen işler dahildir. GitHub `branches/main` okuması **`protected:false`**, repo rulesets listesi **boş** döndü; ayrıntılı branch-protection endpoint'i bağlı entegrasyona **403** döndürdü. Geliştirme dalındaki workflow değişiklikleri `main`in zamanlanmış Actions davranışını **etkilemez**. Bağlı araçlar ile sunucu düzeyinde workflow disable veya branch protection yazma işlemi kullanılamıyor. Kullanıcının `main` izinsiz değiştirilmeyecek talimatı nedeniyle `main`e commit/merge yapılmadı ve PR #9 birleştirilmedi. **Geliştirme dalı güvenlik kapısı tamam/yeşil; ana dalın aktif runtime tetikleyicilerinin kapatılması ve branch protection ise açık risk olarak kalır.** Ana dal koruması ayrı, açık kullanıcı yetkilendirmesi ve uygun yönetim izinleriyle çözülmeden "bütün Actions tetikleyicileri üretimde güvenli" denilemez.

## 3 Kasım 2026 — Actions toplu CI kök nedeni giderildi: 6/6 başarılı; main ayrı risk
- **Kod commit**: `cf98cbb0e2e5874ea12a601df411adedfd420770`. Önceki `8e9f39f`, `291b58a`, `d56f7b9` dev koruma commitlerinde 58 YAML ve 16 eski/yayınlayıcı korunmasına karşın, Master Engine, Eight-Stage ve sıralı preflight koşularının `052726d` commit'inde FAIL ettiği bağımsız Actions loglarıyla belirlendi. Sadece 58-workflow güvenlik kapısının yeşil olması bu genel başarısızlıkları kapatmıyordu.
- **Hataların kesin kökü:** Yeni `v2/test_actions_trigger_protection_audit.py` offline test keşfi `yaml` modülünü import ederken Master/Eight-Stage test koşucularında `PyYAML` eksikti; `v2/test_unified_safety_contract.py` hâlâ önceki `v2-ordered-preflight.yml` gece cron tetikleyicisini zorunlu sayıyor, halbuki otomatik tarama/tetikleme güvenliği için preflight cron'ı kaldırılmıştı. Her iki sebep de ilgili GitHub Actions loglarında gerçek `ModuleNotFoundError: No module named 'yaml'` ve `AssertionError` olarak gözlendi.
- **Uygulanan düzeltmeler**: `v2-master-engine.yml` ve `v2-eight-stage-verification.yml` toplu test kurulumu `cryptography==44.0.2` ve `PyYAML==6.0.2` sabit sürümlerini kuruyor. `v2/test_unified_safety_contract.py` cron'un `yok` olmasını, yalnız doğru geliştirme dalında push ve manuel hazırlık tetikleyicilerini kontrol ediyor. `v2-ordered-preflight.yml` son güvenlik aşamasında `PyYAML==6.0.2` kurup **tüm 58** workflow trigger/yetki denetimini ilave olarak çalıştırıyor. Ana playlist ve tarihî koruma dosyalarına hiçbir yazma yok.
- **Aynı SHA üzerinden doğrulanan 6 GitHub Actions koşusu tamamı SUCCESS:** `41704882199` Actions Trigger & Protected Playlist Gate: **58/58 YAML, 16/16 kilitli yayınlayıcı, 0 ihlal, 38/38 test**. `41704882123` Eight-Stage Verification: **359/359 unittest** ve **14/14 playlist/kontrol testi**. `41704882164` Master Engine: **359/359 unittest** ve **14/14 playlist/kontrol testi**. `41704882213` Ordered Preflight: **compile, protect, discovery-tests, safety = 4/4 SUCCESS**. `41704881974` Current Scanner Offline Gate: iki test işi SUCCESS. `41704882003` Actions Status Monitor SUCCESS. Altı workflow'un da `head_sha` değeri aynıdır: `cf98cbb0e2e5874ea12a601df411adedfd420770`. Bu koşularda büyük ağ/kanal taraması başlatılmadı.
- **Dış/üretim sınırı:** Geliştirme dalındaki `58/58` dosya ve CI koruması bu aşamada gerçek kanıtla tamamlandı. Ama GitHub varsayılan `main` dalının commit'i son kontrol sırasında `5caf278831a641b96968d077c9d25de62f3e8d64` idi; `main` için `protected:false`, rulesets listesi boş. `main` YAML'larının önceki denetiminde 19 dosyada `contents: write`+repo push ve 16 dosyada `schedule` tanımlı. **Geliştirme dalındaki değişiklik `main`in otomatik işlerini kapatmaz**; bu riske yeşil deme. Kullanıcı `main`i ve PR #9'u izinsiz değiştirmeme emrini verdiğinden `main`e commit/merge yapılmadı. Bağlı GitHub araçlarında workflow disable/branch protection yazma yetkisi bulunmuyor; `main`in riskleri sunucu düzeyinde yetkili müdahale gelene kadar açıktır. Bu önkoşulu tutmadan "bütün GitHub Actions üretim güvenliği tamam" denilmez.

## 3 Kasım 2026 — Varsayılan main Actions etkinlik durumları canlı doğrulandı (47 toplu test)
- **Kapsam / kesin kısıt:** Yalnız `Madsc55/MADSC55-TV-V2` üzerinde `madsc/v2-discovery-bulk-20261031` geliştirme dalı değiştirildi. `main`, PR #9, `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` ve YEDEKLER/YENİLER/FAVORİLER değişmedi. Yeni tüm-kanal ağı taraması çalıştırılmadı.
- **Somut ekleme:** `ce47d81ad5e71767753504dc2ca2f0e4bd8dd959` commit'i ile `v2/actions_default_branch_audit.py`, `v2/test_actions_default_branch_audit.py` ve `v2-actions-trigger-protection.yml` güncellendi. GitHub Actions artık default `main` commit'ini **yalnız salt-okunur `git fetch`** ile alıyor, 40 gerçek `main` YAML dosyasını gerçek Git SHA'sı üzerinden inceliyor; GitHub'ın **`actions/workflows` etkinlik durumunu**, `branches/main.protected` ve kuralları read-only API ile aynı snapshot SHA'sına bağlayarak raporluyor. Ana playlist, dev branch harici GitHub ref'i ve production ayarları değiştirilmiyor. API erişim hatası olursa güvenli üretim onayı verilmez.
- **Toplu CI kanıtı:** GitHub Actions run **`41707375463` SUCCESS**, 58/58 geliştirme workflow'u, 16 kilitli yayınlayıcı, **47/47 birleşik güvenlik/kayıp regresyon testi**, 0 geliştirme ihlali. Aynı `ce47d81` SHA üstünde **6/6** Actions koşusu SUCCESS: `41707375470` Eight-Stage, `41707375662` Master Engine, `41707375551` Ordered Preflight, `41707375757` Scanner Offline Gate, `41707375594` Actions Monitor ve `41707375463` yeni birleşik Actions gate. Anonim, sadece config ve yol adları içeren rapor artifact ID **`13266940658`** (`main-default-branch-risk.json`).
- **Yeni canlı bulgular (main kontrolü, artık yalnız varsayım değil):** `main` Git SHA **`5caf278831a641b96968d077c9d25de62f3e8d64`**. 40 gerçek main workflow dosyasından **19'unda `contents:write` + `git push`**, 16'sında `schedule`, 17'sinde ana İBO playlistini yazma ihtimali var. GitHub Actions API **19/19 yazma workflow'unun** ve **16/16 zamanlayıcı workflow'unun** etkin `state=active` olduğunu bildirdi; `state_unknown=0`. `branches/main.protected=false`, etkin ruleset=0. Raporda `readiness=MAIN_DEFAULT_BRANCH_NOT_SAFE` ve `main_branch_modified=false`. Bu açıklar **geliştirme dalındaki kapıdan bağımsızdır**. Varsayılan dalın repository yönetim yetkileri ya da açık ve özel kullanıcı izni olmadan main'i korumak için dev değişikliklerini main'e otomatik aktarmak/merge etmek kesinlikle yasaktır.
- **Geçiş notu:** Geliştirme dalındaki 58 workflow denetim ve test sözleşmesi kapatılmıştır; fakat **Actions sistemi üretim seviyesinde tamamlanmadı**. Main'deki 19 aktif yazma yolunu, 16 aktif scheduler'ı kapatmak, en azından main dalını PR gerektiren bir kuralla korumak ve ardından canlı API ile 0 açık iş bulunmasını doğrulamak gerekir. Bağlı GitHub tool seti workflow enable/disable ya da ruleset/branch protection yazma eylemi sağlamıyor. Bu yetki verilmeden/uygun yönetim aracı olmadan main'e dokunulmayacak. 47 testin yeşil olması **main'in korunmuş olduğunu kanıtlamaz**.

## 3 Kasım 2026 — Actions canlı main denetimi genişletildi: 6/6 CI, 51/51 güvenlik testi
- Yalnız `Madsc55/MADSC55-TV-V2` geliştirme dalı `madsc/v2-discovery-bulk-20261031` güncellendi. **Kod commit**: `c122572d8c7d7a63366bf7f7c1e8a96cd6332a22`. Ana playlist, `main`, YEDEKLER/YENİLER/FAVORİLER, eski repo ve PR #9 değiştirilmedi. Büyük kanal araması başlatılmadı.
- `v2/actions_default_branch_audit.py` ve `v2/test_actions_default_branch_audit.py` tek atomik kod commitinde güçlendirildi. `main.protected=true` artık zorunlu PR inceleme ve yönetici bypass engeli için tek başına hazır kanıt sayılmaz; branch-protection detay API'si okunamazsa `required_pr_policy_verified=false` ve `MAIN_DEFAULT_BRANCH_NOT_FULLY_VERIFIED` olur. GitHub işlemleri yalnız salt-okunurdur. Çok sayfalı Actions API okuması sonrasında `main` SHA ikinci kez karşılaştırılır.
- `contents:write` fakat açık `git push` olmayan işler; git add/commit/push komutları ve `workflow_run`, `pull_request_target`, `repository_dispatch` ayrı risk sütunlarıyla sayılır. Dört yeni regresyon testi eklendi. 6 workflow tek commit üzerinden eşzamanlı GitHub Actions ile doğrulandı: Current Scanner Offline Gate `41711698151` SUCCESS; Eight-Stage `41711698321` SUCCESS; Actions Status Monitor `41711698311` SUCCESS; Ordered Preflight `41711698315` SUCCESS; Master Engine `41711698250` SUCCESS; Actions Trigger & Protected Playlist Gate `41711698726` SUCCESS.
- Son birleşik gate `41711698726`: **51/51** regresyon, **58/58** geliştirme workflow, **16/16** korumalı eski yayımlayıcı, geliştirme güvenlik ihlali **0**, playlist ve tarihî SHA hash denetimi başarıyla geçti; anonim kanıt artifact `13266878990`.
- **Üretim hâlâ açık risk:** Bu koşuda `main` SHA `5caf278831a641b96968d077c9d25de62f3e8d64`, `protected=false`, rulesets boş. Canlı `main`de **19/19 etkin contents-write+git-push**, **16/16 etkin schedule**, 40 workflow dosyası; önceki hedefli analizde 17 playlist-yazma ihtimali. Çıktı `MAIN_DEFAULT_BRANCH_NOT_SAFE`, `required_pr_policy_verified=false`. GitHub bağlantısı admin-level protection okumada 403 döndürüyor ve mevcut araçlar workflow disable/branch protection yazma eylemi sağlamıyor. Kullanıcının `main`i değiştirmeme kuralı nedeniyle canlı üretim ayarlarına müdahale edilmedi. Açık riskleri çözülmüş olarak **ASLA RAPORLAMA**.
## 3 Kasım 2026 — Son kanal AV kabul taraması ve iki sağlayıcı bağımsız arşiv doğrulaması
- **Yalnız aktif repo** \`Madsc55/MADSC55-TV-V2\`; geliştirme dalı \`madsc/v2-discovery-bulk-20261031\`. \`main\`, ana \`MADSC55_TV_IBO_CALISANLAR_TEST.m3u8\`, YEDEKLER/YENİLER/FAVORİLER, PR #9 ve eski repo değiştirilmez. Kullanıcı İBO Player testlerini kendisi yapar.
- Daha önce tamamlanmış orijinal 4.955 + 107 üretim arşivinin gerçek AES-256-GCM bağımsız geri yüklemesi **iki farklı sağlayıcı** kopyasından tekrar doğrulandı: özel Library dosyası ve özel Google Drive dosya ID'si \`1nSKpgpkHh_iNihtZBIEqF9YzNpWy6tUJ\`. Her biri **5.234.628 bayt**, SHA-256 \`38db9b094c48e49eb0b5b1234ddc6a109f215d6d9fa732a1a4d0cf592673fe4c\`, 4.955/4.955 tarihî URL ve 107/107 orphan URL kimliği metadata, AES-GCM authenticator ve SHA eşleşmesiyle geri açıldı. İki depo kopyası bayt düzeyinde aynıdır. Tam URL, AES anahtarı veya özel RSA anahtarı GitHub'a koyulmadı; kurtarma yalnız özel çalışma ortamında yapıldı.
- **46 benzersiz AV kanıtı eksik kimliğin toplu yenilemesi:** GitHub Actions \`41669860900\` **run attempt 2 SUCCESS**; 81/81 tarihî/bozuk-kaynak/kayıp koruma regresyonu başarılı. Gerçek 4 upstream M3U denetiminde 55 özgün sorunlu satırın tamamı mevcut, 50 eşsiz EXTINF kimliği; 107 URL adayı tamamen RSA-şifreli; **4** URL için güncel video+ses gözlendi, 51 sorunlu satırın güncel AV çözümü bulunamadı (**46 benzersiz kimlik için kanıt eksik**). Bu eksiklere tahmini URL yazılmaz ve tüm tarihî adaylar korunur. Yeni artifact \`13269760949\`.
- **Kapsamlı dünya taraması için yeni gerçek kabul kodu:** \`v2/final_batch_acceptance.py\` ve \`v2/test_final_batch_acceptance.py\` commit \`9c93b76670ea85c17111666bb33aeb7dd0a39780\`. Yapılandırılmış sabit kaynaklar, 17 orijinal #60 kaynağı, onaylı Github/forge dinamikleri ve açık HTML M3U indeksleri; HTTP URL SHA256 tekrarsız kimlikleri; yalnız public DNS/HTTP(S) güvenliği; gerçek FFprobe video+ses ve başarıysa kısa FFmpeg ses+video decode; TR/AZ/foreign/unknown yalnız **metadata dil yönlendirme ipucu**, konuşulan dil doğrulaması değil. Her adayın başarısızlığı dahil kaynak/AV/provenans statüsü korunur; tüm orijinal URL'ler ayrı RSA-OAEP-SHA256/AES-256-GCM \`.sealed\` artifact dosyalarına alınır. Ana playlisti yazmaz, canlıya otomatik kanal almaz.
- **Tek olaylık GitHub read-only çalıştırma:** \`.github/workflows/v2-actions-trigger-protection.yml\` içine yalnız belirli commit mesajıyla tetiklenen \`final-worldwide-acceptance\` bağımlı işi eklendi. İlk tetiklemede koşulun YAML kaçışı düzeltildi; ikinci çalışmada hosted runner'ın FFmpeg paket eksikliği gerçek logla görülüp \`8c2720092b9b42aff7c9e62b06198ca623272c65\` commitinde eksik FFprobe/FFmpeg kurulum adımı eklendi. Aktif Actions **\`41715476184\`**, güvenlik önkoşulu \`grouped-protection-check\` SUCCESS, tam tarama işi başlatıldı. Son canlı AV sayıları ve dil kabulü bu workflow'un \`v2/reports/ci/final-worldwide-acceptance.json\` artifact raporunda sonuçlanmadan başarılı gibi gösterilemez. \`readiness=REVIEW_REQUIRED\` ve \`spoken_language_verified=0\` gerçek sınırlamayı dürüstçe yansıtır.
- **Kalıcı açık risk:** \`main\`de 19 etkin yazma yolu, 16 etkin cron ve \`protected=false\` önceki canlı denetimde teyit edildi. Bağlı GitHub aracında workflow disable/branch protection admin yazma eylemi bulunmadığı ve kullanıcı \`main\` değişikliğini yasakladığı için değiştirilmedi; üretim için \`READY\` iddia edilemez.

## 3 Kasım 2026 — Üç belge kaynağı kabulü ve 65 kaynaklı bozuk kanal kurtarma sonucu
- **Kapsam:** Yalnız `Madsc55/MADSC55-TV-V2` geliştirme dalı `madsc/v2-discovery-bulk-20261031`; `main`, `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`, YEDEKLER/YENİLER/FAVORİLER, eski repo ve PR #9 değiştirilmedi. İBO Player cihaz doğrulaması yalnız kullanıcıya aittir.
- **Belge adaptörleri:** Scribd, SlideShare, Internet Archive için `v2/document_platform_discovery.py` ve `v2/test_document_platform_discovery.py` hazırlandı ve `v2/run_all_discovery.py`, `v2/discover.py`, `v2/final_batch_acceptance.py`, birleşik keşif workflow'una bağlandı. URL'ler ilk önce public HTTPS, DNS ve M3U gerçek kanal kaydı kontrollerinden geçiyor. Kimlik/provenans korunuyor; tokenli URL, oturum açma veya paywall aşma yok. Doğrulanan kaynaklar kanal oynatma kanıtı sayılmaz.
- **Gerçek canlı adaptör kabulü:** Actions `41723036558`, **5/5 jobs SUCCESS**, **34/34** toplu test. Scribd 2 sorgu, 0 M3U; SlideShare 2 sorgu, 0 M3U; Internet Archive 1 sorguda 8 öğe, 3 ham M3U bağlantısı; **2** dosya gerçek `#EXTM3U/#EXTINF` kanal listesi, **18.035** ham kayıt; 1 kaynak reddedildi. Bu 18.035 benzersiz veya video+ses doğrulanmış kanal değildir.
- **Orphan kurtarma genişletmesi:** `v2/orphan_m3u_recovery.py` artık ilk 46 etkin sabit + 17 orijinal #60 = 63 kaynak yanında gerçek olarak doğrulanmış 2 public-document M3U kataloğunu da kaynak kimliklerini bozmadan inceliyor. Eşleştirme yalnız **aynı tvg-id + birebir kanal adı**; kaynaklardan metadata eşleşmesi oynatma/kimlik kesin kabulü değildir. Yeni belgeler ayrı güvenli yönlendirmeli fetch ve public DNS kontrolünden geçer.
- **Gerçek toplu AV koşusu:** Actions `41724096783` **SUCCESS**. 65 kaynak, 55 bozuk EXTINF satırı, 50 ayrı metadata kimliği, 107 gerçek tarihî URL adayı (`107/107` yine RSA/AES sealed), 4 ayrı kimlikte video+ses FFprobe gözlemi; **46 benzersiz kimlikte hâlâ kabul edilebilir güncel AV kanıtı bulunmadı** ve bunların 13'ünde hiç alternatif URL adayı bulunmuyor. 2 yeni belge kaynağından ek *birebir kimlik eşleşmesi* çıkmadı; **0** yeni kanal kurtarıldı. Kaybolan ve başarısız adaylar hiçbir koşulda silinmez; tahmini stream URL üretilmez. Artefact `13273646591`. `4` FFprobe video+ses gözlemi, cihaz veya video+ses decode kabulü değildir.
- **Güvenlik ve CI düzeltmesi:** Ağ taramalı orphan workflow'a yanlışlıkla eklenen `push` tetikleyicisi geliştirme safety gate'i düşürdü; bu gerçek hata `4ab17ce075f2d227143ae8d2e195c6181e015e7d` ile düzeltildi. Ağ taraması workflow'u yine **workflow_dispatch only**. Dünya taraması job'una belge-platformu taramasını aynı run'ın kaynak snapshot'ına ekleyen adım ve private-DNS koruması geldi. `e72458a226f9809c7893cb454d8f5a2a8ef0b2cc` üç ek regresyonla kurtarma ve dünya taraması kaynak aktarımını denetledi. Son Master Engine `41724921459` SUCCESS; Ordered Preflight `41724921137` SUCCESS; Current Scanner Offline Gate `41724921133` SUCCESS; Eight-Stage Runner `41724921193` SUCCESS.
- **Açık kalanlar:** 46 gerçekten eksik AV kimliğinin kurtarılması için yeni, güvenilir ve canlı URL kanıtı şarttır; kaynağı olmayan 13'te URL tahmini kesin yasak. Dünya geneli eski tek seferlik uzun AV taraması `41715476184` kontrol sırasında `in_progress` durumundaydı; bitmeden sonuç sayısı uydurulmaz. `main` üzerinde production Actions yazma/schedule/dal koruması açıkları önceki rapor gibi sürüyor. Cihaz testi kullanıcıda. Yeni manuel tarama için GitHub workflow_dispatch gerekli; bağlı GitHub konektörü workflow_dispatch admin eylemi sunmuyor. Pratik devam işi: yeni onaylı resmî/alternatif kaynakları bul, immutable kayıpları ve exact matching'i koru, toplu FFprobe+FFmpeg kanıtıyla onayla; nihai İBO'ya yalnız kullanıcı onayı sonrası taşı.


## 7 Kasım 2026 — Toplu tamamlama kabulü ve gerçek görev envanteri
- Kullanıcı `02892adb` commit'i üzerindeki **6 ana Actions kontrolünün başarılı** olduğunu teyit etti ve ilk aşamanın kapatılmasını istedi. Bu teyide dayanarak `[V2 SIRA] 01` ve `02` tamamlandı olarak kapatıldı. Bağlı GitHub commit-status API'si ayrı status döndürmediği için altı işin logları bu oturumda bağımsız teyit edilmiş sayılmaz.
- GitHub issue aramasında `[V2 SIRA]` olarak **8 ana görev** bulundu; 01–02 kapalı, 03–08 açık. Kullanıcının andığı **33 alt görevin** ayrı Issue kaydı bu aramada bulunmadı; sayı teyit edilmeden 33'ün tamamı kapatılmış sayılmaz.
- Öncelik: 03 K2/K5 offline eşdeğerliği; 04 TR/AZ kaynak adaptörleri; 05 #60/#74 hash kaybı; 06 özel URL arşivi/restore; 07 toplu offline CI; 08 yalnız açık kullanıcı onayıyla manuel canlı tarama, 45 kurtarılmamış kimlik, 2.643 adres ve IBO 2.000'lik partileri.
- Ana IBO playlist, `main`, PR'lar ve eski repo değişmedi. Cihaz testi kullanıcıda. Canlı tarama yalnız kullanıcı onayından sonra.


## 7 Kasım 2026 — KULLANICI EMRİ: kurtarma ve uzun canlı AV taramaları EN SON
- Kullanıcının açık emri: **45 kurtarılamayan kanal (#3), tarihî kayıtların ayrıntılı AV/kurtarma doğrulaması (#4, #15, #17 ile ilişkili kısım) ve 2.643 kayıp yayın adresinin gerçek görüntü+ses taraması (#6) en sona bırakılacak.** Bu işler tamamlanmış sayılmayacak; mevcut kayıtlar, şifreli arşiv ve kanıtlar korunacak.
- Önce bu üç ağır işe bağımlı **olmayan** görevler ele alınacak: kaynak adaptörleri #7–#10, hata sınıflandırma #12, arşiv bütünlüğü/restore #13, tarihî kimliklerin kayıpsız korunması #14 (uzun AV taraması olmadan doğrulanabilen kısmı), güvenli otomasyon #23/#25/#26/#27 ve uygun diğer bağımsız görevler.
- `v2/tasks/master_tasks.json` bağımlılık grafiği bozulmayacak; bağımlı görevler, öncülleri bitmeden sahte tamamlanmayacak. #32 cihaz testi yalnız kullanıcı tarafından doğrulanabilir. Korunan IBO, `main`, PR #9 ve eski repo değiştirilmeyecek.
- Bu talimat **önceki P0 öncelik sırasını uygulama bakımından geçersiz kılar**; teknik güvenlik ve gerçek AV kanıtı koşullarını kaldırmaz.


## 7 Kasım 2026 — ANA GELİŞTİRME İÇİN KALICI HIZLANDIRILMIŞ TAMAMLAMA KURALLARI
- Bu bölüm **saatlik takip otomasyonu için değil**, kullanıcının `V2 DEVAM` ile yürüttüğü ana geliştirme içindir. Saatlik otomasyonun talimatı ve zamanlaması değiştirilmez.
- Tek geçerli depo `Madsc55/MADSC55-TV-V2`, tek yazılabilir geliştirme dalı `madsc/v2-discovery-bulk-20261031`. Eski `madsc-tv`, `main`, PR #9 ve `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` değişmez. YEDEKLER/YENİLER/FAVORİLER, cihaz favorileri, YEDEKLER'in ilk iki TRT 1 1440P QHD ve DHA CANLI 720P HD kaydı, 4.955 tarihî kimlik ve tüm kanıtlar korunur.
- Her turda `v2/tasks/master_tasks.json`, `v2/tasks/state.json`, [V2 SIRA] ve bu dosyanın **en güncel** kayıtlarını oku; tamamlananları tekrarlama. Bağımlılıkları karşılanan 3–5 bağımsız/ilişkili açık işi mümkünse aynı turda gerçek kod/entegrasyonla ilerlet. 7/33 yalnız son kayıtlı başlangıç durumudur, güncel defter esas alınır.
- Önce gerçek çözüm, sonra **ilgili testleri tek toplu kabulde** çalıştır; gerçek GitHub Actions run/commit kanıtı olmadan görevi tamamlandı işaretleme. Hataları aynı çalışma kapsamında düzelt; gereksiz tarama, boş commit ve sadece rapor üretme. Mock, demo, simülasyon veya sırf yeşil test üretimi tamamlanma kanıtı değildir.
- Gerçek IPTV adresi ve FFmpeg ile **video+ses** doğrulaması şarttır; HTTP 200, kanal adı/EPG/metadata, statik test veya Actions yeşilliği tek başına canlı yayın kanıtı değildir. Başarılı tarihî taramaları tekrar çalıştırma; cihaz IBO testi kullanıcıya aittir. Önceki açık emir uyarınca ağır #3/#4/#6 kurtarma/AV işleri en sona ertelenir; bağımsız #13/#23/#25/#27 gibi işleri önce ilerlet.
- Saatlik otomasyonla ortak GitHub görev sahipliği ve gerçek atomik çalışma kilidi kullanılmadan eşzamanlı yazma/dispatch yapılmaz. Önce çalışan/queued Actions ve başka yürütücü durumunu denetle; kilit alınamıyorsa yazma yapma, çakışmayan salt-okunur iş seç. **Yalnız talimat yazılması kilidin kurulduğu anlamına gelmez.** Aynı dal ve dosyadaki güncel SHA'ları kontrol et, değişiklikleri çakışmadan uygula.
- Her gerçekten tamamlanan iş için kanıtı [V2 SIRA] ve görev defterine kaydet; bu devam notunu **silmeden ekleyerek** güncelle. Test/Actions veya dış erişim engelinde görevi açık bırak, somut engeli kaydet, sonraki bağımsız işe geç.
- Tur sonu kısa rapor: gerçekten tamamlanan görevler, tamamlanan/33, commit bağlantıları, doğrulanmış Actions sonuçları, kalan somut engeller ve sıradaki iş grubu. Yeni sohbet de bu kalıcı kayıttan devam eder.


## 7 Kasım 2026 — KESİN ENGEL GİDERME VE 26 GÖREV İÇİN KALICI UYGULAMA EMRİ
- Bu bölüm ana geliştirme `V2 DEVAM` çalışmasına aittir; mevcut saatlik takip otomasyonunun istemi ve zamanlaması **değiştirilmez**.
- Yalnız `Madsc55/MADSC55-TV-V2` deposunun `madsc/v2-discovery-bulk-20261031` geliştirme dalında çalış. Eski depo, `main`, PR #9, korunan ana IBO playlist, YEDEKLER/YENİLER/FAVORİLER, cihaz favorileri ve tarihî kimlikler değişmez.
- Başlangıç kaydı 7/33, 26 açık görevdir; **her turda** kanonik `state.json`, `v2/tasks/master_tasks.json`, [V2 SIRA] issue'ları ve son commit/Actions kanıtıyla güncel durum doğrulanır. Başlangıç sayısı yeni kanıt olmadan artırılmaz.
- **Araştırma tek başına teslim değildir.** Her turda gerçek kod, entegrasyon veya çalışır üretim düzeltmesi yap; bağımlılığı karşılanan birden çok bağımsız işi mümkünse birlikte ilerlet. #3/#4/#6 gibi ağır kurtarma işleri öncelik kararı gereği daha sonra ele alınır; diğer açık işler ihmal edilmez.
- Actions tetikleme/dal filtreleri, permissions, eksik bağımlılıklar, gerçek CI hata logları, concurrency ve yazma çakışması incelenip **somut kök neden** giderilir. GitHub'ın eski commit status API'sinde sonuç olmaması, Actions'ın çalışmadığını kanıtlamaz. Erişilemeyen run için başarı veya başarısızlık uydurulmaz.
- İlgili değişiklikleri **toplu kabul** halinde test et; boş commit, mock/prototip/simülasyon ve göstermelik yeşil test yok. Gerçek FFmpeg video+ses kanıtı olmadan kanal oynatılabilir sayılmaz. Geçici HTTP/DNS/decoder hataları tarihî kayıt silme nedeni değildir.
- Aynı dal/dosya yazmalarında güncel blob SHA ile optimistic concurrency uygula; farklı workflow'ların concurrency grupları ortak GitHub yazar kilidi sayılmaz. Saatlik yürütücüyle gerçek çakışma varsa paylaşılan görev sahipliği veya atomik kilit olmadan çakışan yazmayı yapma; bağımsız işleri sürdür.
- Görev ancak gerçek uygulama, çalışmış test, gerekli **başarılı Actions run**, göreve özgü kabul ve commit/run kanıtı varsa tamamlandı olur. #32 yalnız kullanıcının IBO Player cihaz testine bağlıdır. Kanıtları görev kaydına ekle; engelleri açık bırak.
- Tur sonunda önceki ve yeni tamamlanan/33, yeni kapanan görevler, commit URL'leri, **doğrulanmış** Actions run URL/sonuçları, somut engeller ve sonraki bağımsız iş grubu dışında uzun durum tekrarı yapma. Her sonraki `V2 DEVAM` bu emri uygular.


## 7 Kasım 2026 — Kullanıcı tarafından eklenen arşiv anahtarı için canlı kabul
- Kullanıcının GitHub Actions repository secrets ekranında iki secret kaydı görülüyor; değerler ve tam adlar ekranda görünmüyor. Secret varlığı/formatı yalnız gerçek canlı job tarafından doğrulanabilir.
- Önceki canlı Master Engine #42396041860, `V2_ARCHIVE_KEY_HEX` eksik olduğu için güvenli biçimde durmuştu. Yeni canlı kabul, `offline-tests` ve koşullu `master` job sonuçları ile logları üzerinden yapılacak.
- Bu tetikleme arşiv anahtarını okumaz/yazmaz, önceki Stage 5 anahtarlarını değiştirmez; `main`, PR #9 ve korunan IBO listesine dokunmaz. Sonuç gelmeden #23 kapanmaz.


## 7 Kasım 2026 — Gerçek passphrase uyumluluğu ve canlı kabul
- Yeni canlı arşivler için `v2/live_archive_key.py` mevcut `V2_ARCHIVE_PASSPHRASE` secret'ından sabit alan ayrımlı scrypt ile kalıcı 256-bit anahtar türetir. Geçerli `V2_ARCHIVE_KEY_HEX` varsa önceliklidir; geçersiz/eksikse güçlü mevcut passphrase kullanılır. Gizli değerler yazdırılmaz.
- Geçmiş Stage 5 AES arşivleri ve özel kurtarma anahtarları **değiştirilmez**; bu yeni türetme yalnız canlı Master Engine çıktılarını etkiler. Regresyon testleri toplu offline gate içindedir.
- Bu commit `[run-live-master]` ile gerçek kaynak keşfi ve arşiv kabulünü ister. Canlı sonuç ve job logu doğrulanmadan #23 tamamlanmış sayılmaz.


## 7 Kasım 2026 — Canlı Master Engine gerçek hata analizi
- Gerçek run #42406632255: offline-tests başarılı; canlı master başarısız. `V2_ARCHIVE_PASSPHRASE` ile scrypt türetme başarılı; şifreli arşiv geri okuma başarılı ve korunan playlist SHA değişmedi. 47 kaynak; `ilyswch-iptv-tr` HTTP 404; 7.785 benzersiz aday, fakat HLS erişim sayacı 0.
- Kök neden bulundu: `real_ibo_scan.check_hls` başarıda aynı entry nesnesini döndürürken `master_engine.build` checker sonucunu `is True` ile kabul ediyordu. `hls_reachable` adaptörü ve `test_real_hls_scanner_returns_entry_not_boolean` regresyonu eklendi. Bu düzeltme henüz yeni canlı FFmpeg kanıtı değildir.
- Gerçek kaynak 404 ve canlı AV tarama sonuçları yeniden doğrulanmadan #23 veya yayın paketi görevleri tamamlandı sayılmaz. 7.785 aday için 0 AV raporu artık güvenilir erişilemezlik kanıtı sayılmamalıdır.
