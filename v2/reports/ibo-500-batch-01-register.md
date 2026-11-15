# MADSC55 TV V2 — IBO YEDEKLER 500'lü test kayıt defteri

- İlk paket: 500 kanal, dosya: MADSC55_V2_500_YEDEKLER.m3u8
- SHA-256: de060b0f0227481c01156141216cc13bcc003dab0b1915341697a72dc4aa7ddc
- Kaynak: başarılı gerçek tarama #43653012989, artifact 14136864383 (v2-real-scan-evidence)
- Arşivdeki aday listesi: IBO_YENI_ADAYLAR_PART1.m3u8
- Ana liste: MADSC55_TV_IBO_CALISANLAR_TEST.m3u8; başlangıç 876 kayıt; FAVORİLER korunmalı.
- İlk 500 test paketi, sonraki partilerde tekrar seçilmemeli. SHA-256 ile karşılaştırılmalı.
- Durum: GitHub protected main ve immutable IBO kontrolü nedeniyle ana İBO'ya aktarım YAPILMADI; cihazda çalıştığı iddia edilmez.
- Önceki otomasyon PR: #266, engelli. İBO'ya otomatik yayın izni olmadan dokunulmaz.

## Kullanıcının açık yayımlama izni — 15 Kasım 2026
- Yalnızca mevcut MADSC55 TV V2 ana IBO playlistinin YEDEKLER grubuna, bulunan kaynaklardan **500 kanal** eklenmesine açık izin verilmiştir.
- Bundan sonraki paketler de yalnızca kullanıcı her paket için talimat verdiğinde, 500'er kanal halinde eklenebilir.
- Mevcut 876 kanal, FAVORİLER, diğer gruplar ve ana playlist bağlantısı aynen korunacaktır; yeni ana playlist oluşturulmayacaktır.
- YEDEKLER'den sonraki taşıma, silme, seçme ve üretim kararları yalnızca kullanıcının ayrıca verdiği talimatla yapılır.
- Bu izin, GitHub branch protection / required status check mekanizmalarını devre dışı bırakmaz; değişiklik koruma denetiminden geçmelidir.
