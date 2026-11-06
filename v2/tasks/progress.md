# MADSC55 TV V2 — Kalıcı görev ilerlemesi

**Kaynak:** `state.json` (proje), `v2/tasks/state.json` (33 görevin tek durum kaydı), `master_tasks.json` (değişmez görev tanımları).

- 33 görev kayıtlı; 0 kanıtla tamamlandı, 1 devam ediyor, 32 bekliyor.
- P0 #1: [Kaynak entegrasyonu #42216075104](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42216075104): 11 başarılı, 1 çalışıyor; AV kabulü **tamamlanmadı**.
- P0 #2 bağımsız toplu test denetimi yapılabilir.
- Geliştirme dalında en son doğrulanan toplu testler: [Master Engine #42244284859](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42244284859), [Eight-Stage #42244284904](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42244284904), [Sıralı Hazırlık #42244284944](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42244284944), [Actions Monitor #42244284900](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/42244284900) başarılı; yeni görev sistemi commitlerinin testleri ayrıca gereklidir.

**Kesin kural:** Yeşil CI, gerçek FFmpeg görüntü+ses kanıtı değildir. Korunan `main`, PR #9 ve ana İBO listesi değiştirilemez. Yeni görev sisteminin kurulumu ve test kabulü tamamlanmadan görevler kapatılmaz.
