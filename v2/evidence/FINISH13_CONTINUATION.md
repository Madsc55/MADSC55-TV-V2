# 13 açık görev — doğrulanabilir bitirme kaydı

Bu kayıt, tamamlanmamış işi tamamlandı göstermemek için oluşturuldu.

- Açık görevler: #15, #17, #18, #19, #20, #21, #28, #29, #30, #31, #32, #33, #34.
- #28–#32: gerçek cihazda görüntü/ses ve M3U içe aktarma kanıtı gelmeden **pending_device** olarak tutulmalı.
- #15–#21: tek ffprobe çağrısıyla ses+görüntü, kaynak/EPG ve yeniden deneme raporları gerçek URL'lerle doğrulanmalı.
- #33: 7z arşivi oluşturma, parola ile 7z t, SHA-256 kontrolü ve bağımsız geri yükleme gerekli.
- #34: GitHub/GitLab/Codeberg keşfi gerçek API yanıtları ve AV doğrulamasıyla kabul edilmeli.
- Yerel finish_all.sh taslağı henüz güvenli üretim kabulü için yeterli değil: eksik state.json oluşturma, yalnızca dosya varlığına göre done yazma ve eski kanıtları yeni sayma riskleri var.
- Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmemeli.

Bu PR bir **devam notudur**; hiçbir görev kapatılmadı ve gerçek test çalıştırıldığı iddia edilmiyor.
