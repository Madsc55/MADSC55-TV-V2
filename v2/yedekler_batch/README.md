# YEDEKLER paket çalışma sistemi
Ana İBO playlistine dokunmaz. Arşiv 18.074 kanalın değişmez kaynağıdır. Durumlar: ANA_ARSIV, TEST, TURK, YABANCI.
`python yonet.py status`
`python yonet.py batch` (varsayılan 1500)
`python yonet.py batch --count 300`
`python yonet.py assign --start 1 --end 100 --to TURK`
`python yonet.py assign --start 101 --end 200 --to YABANCI`
`python yonet.py assign --start 1 --end 100 --to ANA_ARSIV`
`python yonet.py undo`
Not: Arşiv dosyası ve SHA-256 eşleşen state.json olmadan komutlar çalışmaz. Gerçek görüntü/ses testi bu kodun kapsamı dışındadır. Kullanıcı talimatı olmadan sınıflandırma yapılmaz.
