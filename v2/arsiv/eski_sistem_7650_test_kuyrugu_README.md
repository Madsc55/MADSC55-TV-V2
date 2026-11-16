# 7.650 eski sistem adayının güvenli test kuyruğu

Bu kuyruk 4 dosyadaki 7.650 benzersiz URL'yi 500'erlik dilimlerle gerçek ffprobe ve ffmpeg ses+görüntü testinden geçirir. Ana IBO playlistine, YEDEKLER'e ve 2.881 arşive yazmaz.

**Güvenlik:** V2 ana dalı yeni workflow ve zamanlanmış cron işleri yasaklar. Bu yüzden otomatik zamanlayıcı eklenmedi. Kodu mevcut izinli tarama akışına bağlamak için ayrı bir güvenlik değerlendirmesi gerekir.

Bir çalışma ortamında ffmpeg kuruluysa:
```bash
python v2/verify_legacy_7650_queue.py --state v2/reports/legacy-queue/state.json --output v2/reports/legacy-queue/summary.json
```
Her çalışmada 500 URL ilerler; state.json dosyası kalıcı saklanmalı. 16 çalışmada tüm adaylar birer kez incelenir. 'av_verified' sadece ses ve görüntü çözümleme testi başarılı anlamına gelir; canlı yayın kimliği ve IBO cihaz testi ayrıca gerekir. Bağlantılar ana YEDEKLER'e otomatik aktarılmaz.
