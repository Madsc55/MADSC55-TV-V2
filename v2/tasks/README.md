# MADSC55 TV V2 — V2 DEVAM

Bu dizin 33 işin kalıcı kaydıdır. Yalnızca `Madsc55/MADSC55-TV-V2` deposunun `madsc/v2-discovery-bulk-20261031` dalında çalışılır. Eski `madsc-tv`, `main`, PR #9 ve `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` değiştirilemez.

**Tek kaynak düzeni:** Kök `state.json` genel proje durumunun kanonik kaydıdır ve `task_tracking` ile bu dizine işaret eder. `master_tasks.json` görev tanımı ve bağımlılıklar için tek kaynaktır; `v2/tasks/state.json` ise **yalnızca görev durumları** için tek kaynaktır. `next_action.json` ve `progress.md` türetilmiş görünüm olup kanıt yerine geçmez. Çelişkide yeni GitHub verisi doğrulanır, başarı varsayılmaz.

**Yeni sohbette `V2 DEVAM`:** Bu ifade tek başına GitHub tetikleyicisi değildir. Asistan önce kök `state.json`, `master_tasks.json`, görev `state.json` ve son GitHub Actions sonuçlarını yeniden okur; bağımlılıkları tamamlanmış ilk P0→P3 görevi seçer. Devam eden test varsa bağımsız işi yapar. Değişiklikleri sadece geliştirme dalına commit eder, ilgili toplu testleri doğrular, yalnızca kanıtla `completed` kaydeder. Bir iş başarısızsa gerekçesi ve bağlantısı `blocked`/`in_progress` durumuna yazılır; yanlış başarı yoktur.

**Çakışma:** GitHub dosya güncellemelerinde mevcut blob SHA ile koşullu `update_file` kullan; çatışma olursa dosyayı tekrar oku ve uzlaştır. Aynı durum dosyasına eşzamanlı yazma; `state.json` görev durumlarını tekrar tutmaz. Ağ/GitHub erişimi yoksa `completed` işaretleme. Kullanıcı cihaz testi #32 yalnızca kullanıcı kanıtıyla kapanır.

**Otomatik çalışma:** Sadece mevcut yetkili zamanlanmış takip görevi kullanılabilir; yeni üretim yayıncısı, playlist değiştirici veya otomatik `main` yazıcısı eklenmez. Bu dizindeki Python motoru salt-okunur seçim ve doğrulama yapar; kendi başına GitHub yazmaz veya test başarısı uydurmaz.

**Kabul:** `PYTHONPATH=v2/tasks python -m unittest -v v2/tasks/test_task_engine.py` ve ilgili mevcut toplu Actions kontrolleri. 33 görev, döngüsüz bağımlılık, tekrar seçmeme, başarısız işin tamamlanmaması, kaldığı yerden devam, çakışma ve çevrimdışı güvenli hata doğrulanır.
