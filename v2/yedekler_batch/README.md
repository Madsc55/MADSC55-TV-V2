# YEDEKLER 2.500'lü paket yönetimi
Bu araç **ana İBO playlistini değiştirmez**. Kaynak: `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` içindeki 18.074 YEDEKLER kaydı.

## İlk kurulum (depo kökünden)
`python v2/yedekler_batch/arsiv_hazirla.py MADSC55_TV_IBO_CALISANLAR_TEST.m3u8`

Bu adım beklenen kayıt sayısı ve `state.json` içindeki SHA-256 eşleşirse **yerel** `YEDEKLER_ARCHIVE.m3u8` üretir; eşleşmezse güvenli biçimde durur. Dosya GitHub'a eklenmez.

## Kullanım (v2/yedekler_batch dizininden)
- `python yonet.py status`
- `python yonet.py batch` — varsayılan **2.500**
- `python yonet.py batch --count 300` — esnek paket
- `python yonet.py assign --start 1 --end 100 --to TURK`
- `python yonet.py assign --start 101 --end 200 --to YABANCI`
- `python yonet.py assign --start 1 --end 100 --to ANA_ARSIV`
- `python yonet.py undo` — son atamayı geri al

**Sınırlar:** Durum atamaları yayınların görüntü/ses çalışırlığını doğrulamaz. Sınıflandırma kullanıcı onayıyla yapılır. GitHub Actions üzerinden otomatik test/taşıma henüz bağlı değildir. Arşiv dosyası üretimi ve uçtan uca kabul ayrıca doğrulanmalıdır.
