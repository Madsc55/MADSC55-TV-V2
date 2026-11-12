# Aşama 5 — #31 → #32 → #33 kanıt denetimi (2026-11-12)

**Durum: KABUL EDİLMEDİ.** Bu belge yalnızca GitHub API üzerinden okunan mevcut iş sonuçlarını kaydeder. Yeni bir Actions koşusu, canlı yayın kanıtı, İBO Player cihaz onayı veya nihai arşiv geri yüklemesi değildir.

## Denetlenen toplu Actions koşuları

| Run | Doğrulanan iş sonuçları | Kabul sınırı |
|---|---|---|
| [43139744799](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43139744799) | offline-tests: success; master: skipped | Canlı Master Engine kabulü yok |
| [43139744816](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43139744816) | compile, protect, discovery-tests, safety: success; live public audit: skipped | Canlı kaynak kabulü yok |
| [43139745432](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43139745432) | offline regressions/protected playlist: success; local FFmpeg guard: success | Gerçek İBO cihazı kabulü yok |
| [43139744855](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43139744855) | Actions triggers/write permissions/protected playlist/history: success; three evidence jobs: skipped | Gerçek AV tarama ve kanıt zinciri tamamlanmadı |
| [43139744839](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43139744839) | read-master-runs: success | Yalnız izleme işi |

## Görev kabul kapıları

- **#31 — AÇIK:** `v2/tasks/master_tasks.json` kabul sözleşmesi #17, #24, #26, #27 ve #30 ön koşullarını, tüm zorunlu toplu kontrollerin yeşil olmasını, şifreli AV kanıtını ve değişmez ana playlist kontrolünü gerektirir. Yukarıdaki skipped işler nedeniyle nihai kabul kanıtlanmadı.
- **#32 — AÇIK:** #31 sonrasında kullanıcı tarafından gerçek İBO Player cihazında görüntü/ses oynatma kanıtı gereklidir. GitHub Actions, ffprobe veya HTTP yanıtı bunun yerine geçmez.
- **#33 — AÇIK:** #31 ve #32 kabulü, nihai şifreli arşiv bütünlüğü ve gerçek geri yükleme kanıtlarıyla raporlanmalıdır.

## Depo ve güvenlik

Bu rapor `stage5-evidence-gated-ibo-20261112` dalı için hazırlanmıştır. Bu dalda sorgulanan `v2/tasks/state.json` ve `v2/tasks/master_tasks.json` bulunamadı; görev sözleşmesi `madsc/v2-discovery-bulk-20261031` dalından okundu. Farklı dalların durumları kanıt olmadan birleştirilmedi.

**Korunanlar:** `main`, ana İBO playlisti, YEDEKLER/YENİLER/FAVORİLER, cihaz favorileri ve PR #9 değiştirilmedi. Görevlerin durumu completed yapılmadı.

## Kalan kabul eylemleri

1. Kanonik görev durumunun doğru geliştirme dalıyla uyumunu denetle; #30 dahil tüm bağımlılıkları tamamla.
2. #31 için atlanan gerçek kanıt işlerini içeren tek toplu Actions kabul koşusunu çalıştır; başarısız işleri loglara göre düzelt ve yeniden çalıştır.
3. #32 için kullanıcıdan gerçek İBO Player görüntü/ses test kaydı al.
4. #33 için nihai şifreli arşivin bağımsız geri yükleme bütünlüğünü ve kabul bağlantılarını rapora bağla.

Bu maddeler tamamlanmadan #31, #32 veya #33 kapatılmayacaktır.
