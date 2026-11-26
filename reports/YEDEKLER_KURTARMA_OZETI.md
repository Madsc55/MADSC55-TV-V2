# YEDEKLER kurtarma özeti — 26 Kasım 2026

Salt-okunur çevrimdışı analiz. Yeni yayın testi, yayın URL'si, playlist değişikliği, logo/EPG ataması veya cihaz kabulü yok.

## Kaynak ve kapsam

- Main kanonik playlist SHA-256: `265f368758e75c5b18bc1b936a9792fef36528ba486288ddb35e4e7e23775ecf`; YEDEKLER iç parça blob: `5b1335c5cf01a5fcb8a623fb3b76539f5193f1ed`. 18.330 toplam kayıt, 1.562 YEDEKLER. Kategori içi sıra = genel 1-bazlı sıra - 825.
- 26 Kasım [run 45799091422](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/45799091422): erişilebilir 0–26 numaralı 27/32 paket, 1.322 benzersiz pozisyon; tüm indirilen paketler aynı playlist SHA-256 ve YEDEKLER kapsamını bildiriyor. 240 kayıt için bu anlık kesitte yeni sonuç yok. Nihai özet henüz yok.
- 25 Kasım [run 45515390523](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/45515390523), artifact 15007854439, fresh-summary.json: tam 2.390 yabancı arşiv dışı kayıt, 1.562 YEDEKLER, aynı playlist SHA-256. YEDEKLER: 197 AV_60S_VERIFIED, 255 AV_SHORT_VERIFIED, 8 kalite incelemesi, 3 video-only, 450 recheck, 434 access restricted, 108 invalid URL, 107 security policy blocked. 26 Kasımda mevcut olmayan paketler için yalnız tarihsel pozitif kayıtlar ayrıca gösterilir.
- 26 Kasım kapsamı bütün ülkeler: 121 AV_60S_VERIFIED, 4 AV_60S_LATE_START_VERIFIED, 212 AV_SHORT_VERIFIED, 36 tutarsızlık, 12 kalite incelemesi, 3 video-only, 462 recheck, 289 erişim engeli, 94 güvenlik engeli, 89 geçersiz URL (toplam 1.322).
- 26 Kasım Türkî aday etiketleri kaynak raporun turkic_metadata_hint alanından; gerçek konuşma/altyazı veya yayıncı kökeni kanıtı değildir. Tarihsel bölüm için aynı tür ad/TVG metadata ipuçları kullanılmıştır. Aynı kanal farklı URL'lerde tekrarlanabilir; sayılar kanal kayıt sayısıdır.
- Açılış süresi üç turda yerel decoder gözlemi (saniye), İBO cihaz süresi değildir. '-' ölçüm yok. Çözünürlük ve bitrate bu artifact'larda ölçülmemiştir; varsa görünen addaki kalite etiketi yalnız metadata. AV sınıfı gerçek ölçüm sonucudur. Hiçbir erişim engeli aşılmamıştır.

## 26 Kasım — mevcut paketlerde Türk/Türkî metadata adayları

| Bölge ipucu | 60 sn AV | Geç açılan 60 sn AV | Kısa AV |
|---|---:|---:|---:|
| Türkiye/Türkçe | 31 | 3 | 56 |
| KKTC | 0 | 0 | 1 |
| Azerbaycan | 0 | 0 | 0 |
| Diğer Türkî | 0 | 0 | 0 |
| Toplam | 31 | 3 | 57 |

| YEDEKLER sıra | Genel sıra | Kanal adı (varsa ilan edilen kalite) | TVG-ID | Bölge ipucu | AV sonucu | Açılış tur 1 / 2 / 3 (sn) |
|---:|---:|---|---|---|---|---|
| 3 | 828 | 09.KANAL 7 TÜRKNET | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 5.496 / 3.716 / 3.566 |
| 78 | 903 | AKSU TV 720P HD | AksuTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.846 / 4.318 / 4.522 |
| 88 | 913 | ARAS TV 576P SD | ArasTV.tr@SD | Türkiye/Türkçe | Kısa AV | 3.177 / 1.11 / 1.082 |
| 106 | 931 | ATV (BACKUP) | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 3.899 / 3.423 / 3.097 |
| 107 | 932 | ATV 1 1080P FHD | 2zkzbuscxwyjc4k | Türkiye/Türkçe | 60 sn AV (3 tur) | 5.492 / 11.34 / 2.938 |
| 110 | 935 | ATV 4 480P SD | 2zkzbuscxwyjc4k | Türkiye/Türkçe | 60 sn AV (3 tur) | 8.14 / 3.286 / 6.942 |
| 112 | 937 | ATV 6 360P SD | 2zkzbuscxwyjc4k | Türkiye/Türkçe | 60 sn AV — geç açılış (3 tur) | 4.067 / 33.95 / 82.771 |
| 113 | 938 | ATV 7 360P SD | 2zkzbuscxwyjc4k | Türkiye/Türkçe | 60 sn AV — geç açılış (3 tur) | 13.257 / 21.47 / 2.679 |
| 114 | 939 | ATV 1080P FHD | 2zkzbuscxwyjc4k | Türkiye/Türkçe | 60 sn AV — geç açılış (3 tur) | 105.457 / 7.803 / 22.442 |
| 116 | 941 | ATV ALANYA 1080P | ATVAlanya.tr@SD | Türkiye/Türkçe | Kısa AV | 3.9 / 2.063 / 4.066 |
| 180 | 1005 | BRTV 720P HD | BRTV.tr@SD | Türkiye/Türkçe | Kısa AV | 3.624 / 4.325 / 3.885 |
| 184 | 1009 | BRÜKSEL TÜRK | — | Türkiye/Türkçe | Kısa AV | 2.092 / 2.077 / 2.199 |
| 186 | 1011 | BRÜKSEL TÜRK | — | Türkiye/Türkçe | Kısa AV | 1.331 / 1.173 / 1.249 |
| 219 | 1044 | CNN TURK (1080P) | — | Türkiye/Türkçe | Kısa AV | 2.974 / 2.876 / 3.322 |
| 244 | 1069 | DENİZ POSTASI TV 720P HD | DenizPostasiTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.998 / 3.732 / 5.459 |
| 261 | 1086 | DİYANET TV 2 1080P FHD | DiyanetTV.tr@SD | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.83 / 2.134 / 2.574 |
| 262 | 1087 | DİYANET TV 1080P FHD | DiyanetTV.tr@SD | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.502 / 3.607 / 2.42 |
| 264 | 1089 | DİYAR TV 720P HD | DiyarTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.397 / 3.996 / 4.988 |
| 283 | 1108 | DOST TV 576P SD | DostTV.tr@SD | Türkiye/Türkçe | Kısa AV | 2.43 / 1.953 / 2.1 |
| 291 | 1116 | DREAM TÜRK 1 720P HD | ttlji9eholru11x | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.224 / 3.09 / 2.846 |
| 292 | 1117 | DREAM TÜRK 2 720P HD | ttlji9eholru11x | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.583 / 2.507 / 2.537 |
| 293 | 1118 | DREAM TÜRK 720P HD | ttlji9eholru11x | Türkiye/Türkçe | 60 sn AV (3 tur) | 3.443 / 3.089 / 3.497 |
| 294 | 1119 | EDESSA TV 1080P FHD | EdessaTV.tr@SD | Türkiye/Türkçe | Kısa AV | 2.8 / 2.805 / 2.669 |
| 308 | 1133 | ER TV 1080P FHD | ERTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.65 / 5.211 / 5.349 |
| 323 | 1148 | ETV KAYSERİ 720P HD | ETVKayseri.tr@SD | Türkiye/Türkçe | Kısa AV | 5.17 / 5.115 / 4.983 |
| 365 | 1190 | FORTUNA TV 1080P FHD | FortunaTV.tr@HD | Türkiye/Türkçe | Kısa AV | 2.521 / 2.459 / 2.573 |
| 368 | 1193 | FTV TÜRK 540P SD | madsc.candidate.69a8bb5fe41db0e9ed98 | Türkiye/Türkçe | 60 sn AV (3 tur) | 1.534 / 1.218 / 0.796 |
| 401 | 1226 | HABER TÜRK (BACKUP) | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 5.74 / 3.996 / 4.493 |
| 402 | 1227 | HABER TÜRK (BACKUP) | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.588 / 2.882 / 2.709 |
| 404 | 1229 | HABER61 TV 720P HD | Haber61TV.tr@SD | Türkiye/Türkçe | Kısa AV | 1.987 / 2.096 / 2.1 |
| 441 | 1266 | HUNAT TV 720P HD | HunatTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.957 / 4.968 / 5.646 |
| 469 | 1294 | KANAL 7 AVRUPA | — | Türkiye/Türkçe | Kısa AV | 1.811 / 1.984 / 3.094 |
| 472 | 1297 | KANAL 7 AVRUPA 720P HD | — | Türkiye/Türkçe | Kısa AV | 2.836 / 2.995 / 2.777 |
| 555 | 1380 | KANAL V 720P HD | KanalV.tr@SD | Türkiye/Türkçe | Kısa AV | 5.433 / 5.467 / 5.861 |
| 564 | 1389 | ❌ KAY TV 576P SD | KayTV.tr@SD | Türkiye/Türkçe | Kısa AV | 5.595 / 5.812 / 5.608 |
| 569 | 1394 | KENT TÜRK TV 1080P FHD | KentTurk.tr@SD | Türkiye/Türkçe | Kısa AV | 5.444 / 5.429 / 5.338 |
| 570 | 1395 | KENT TÜRK TV KAYSERİ | — | Türkiye/Türkçe | Kısa AV | 3.183 / 2.419 / 2.722 |
| 571 | 1396 | KIBRIS TV | — | KKTC | Kısa AV | 2.832 / 3.822 / 2.805 |
| 609 | 1434 | LİFE TV 720P HD | LifeTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.794 / 4.786 / 5.447 |
| 615 | 1440 | MAVİKARADENİZ 1080P FHD | MaviKaradenizTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.186 / 5.055 / 5.219 |
| 625 | 1450 | MERCAN TV 576P SD | MercanTV.tr@SD | Türkiye/Türkçe | Kısa AV | 6.604 / 5.843 / 5.798 |
| 696 | 1521 | NUMBER 1 ASK 720P HD | Number1Ask.tr@SD | Türkiye/Türkçe | Kısa AV | 2.682 / 2.686 / 2.89 |
| 698 | 1523 | NUMBER 1 DAMAR 720P HD | Number1Damar.tr@SD | Türkiye/Türkçe | Kısa AV | 1.975 / 1.946 / 1.953 |
| 706 | 1531 | NUMBER ONE TÜRK ASK | — | Türkiye/Türkçe | Kısa AV | 2.056 / 1.603 / 1.557 |
| 707 | 1532 | NUMBER ONE TÜRK DAMAR | — | Türkiye/Türkçe | Kısa AV | 3.024 / 3.022 / 2.284 |
| 708 | 1533 | NUMBER ONE TÜRK DANCE | — | Türkiye/Türkçe | Kısa AV | 3.542 / 3.131 / 3.392 |
| 709 | 1534 | NUMBER1 TV 1 720P HD | Number1TV.tr@SD | Türkiye/Türkçe | Kısa AV | 3.471 / 2.724 / 3.49 |
| 710 | 1535 | NUMBER1 TV 2 720P HD | Number1TV.tr@SD | Türkiye/Türkçe | Kısa AV | 3.32 / 3.063 / 2.809 |
| 711 | 1536 | NUMBER1 TV 720P HD | Number1TV.tr@SD | Türkiye/Türkçe | Kısa AV | 2.291 / 1.99 / 1.842 |
| 713 | 1538 | OLAY TÜRK KAYSERİ TV KAYSERİ | — | Türkiye/Türkçe | Kısa AV | 3.933 / 4.418 / 4.936 |
| 714 | 1539 | OLAY TÜRK TV KAYSERİ 720P HD | OlayTurkTV.tr@SD | Türkiye/Türkçe | Kısa AV | 6.247 / 6.462 / 6.399 |
| 740 | 1565 | POWER TURK HD | — | Türkiye/Türkçe | Kısa AV | 6.582 / 4.136 / 5.825 |
| 743 | 1568 | POWER TURK TAPTAZE | — | Türkiye/Türkçe | Kısa AV | 3.586 / 5.517 / 2.836 |
| 744 | 1569 | POWER TÜRK | — | Türkiye/Türkçe | Kısa AV | 2.457 / 2.562 / 2.324 |
| 746 | 1571 | POWER TÜRK AKUSTİK | — | Türkiye/Türkçe | Kısa AV | 4.775 / 4.397 / 3.41 |
| 747 | 1572 | POWER TÜRK SLOW | — | Türkiye/Türkçe | Kısa AV | 4.091 / 4.57 / 4.013 |
| 748 | 1573 | POWER TÜRK TV 1 1080P FHD | 82e4q3ribmz2mt1 | Türkiye/Türkçe | Kısa AV | 6.74 / 5.194 / 4.795 |
| 749 | 1574 | POWER TÜRK TV 2 1080P FHD | 82e4q3ribmz2mt1 | Türkiye/Türkçe | Kısa AV | 4.375 / 4.564 / 4.362 |
| 750 | 1575 | POWER TÜRK TV 1080P FHD | 82e4q3ribmz2mt1 | Türkiye/Türkçe | Kısa AV | 5.351 / 4.992 / 5.079 |
| 795 | 1620 | SAT 7 TÜRK 1 720P HD | — | Türkiye/Türkçe | Kısa AV | 5.475 / 5.334 / 5.758 |
| 803 | 1628 | SEMERKAND TV 1 1080P FHD | SemerkandTV.tr | Türkiye/Türkçe | 60 sn AV (3 tur) | 3.117 / 2.92 / 2.892 |
| 804 | 1629 | SEMERKAND TV 2 1080P FHD | SemerkandTV.tr | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.04 / 1.918 / 2.135 |
| 808 | 1633 | SERCEM TV 1080P FHD | SercemTV.tr@HD | Türkiye/Türkçe | Kısa AV | 1.724 / 1.575 / 1.67 |
| 821 | 1646 | SHOW TV | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 4.055 / 3.044 / 3.14 |
| 822 | 1647 | SHOW TV | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.176 / 1.778 / 2.406 |
| 823 | 1648 | SHOW TV | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 4.311 / 3.423 / 3.396 |
| 834 | 1659 | SHOW TV 1080P FHD | pvr08e5grfsebfw | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.69 / 2.293 / 2.094 |
| 871 | 1696 | STAR TV 2 720P HD | 75tz02ooforewap | Türkiye/Türkçe | 60 sn AV (3 tur) | 3.535 / 3.023 / 3.082 |
| 873 | 1698 | STAR TV 4 720P HD | 75tz02ooforewap | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.848 / 2.556 / 2.539 |
| 874 | 1699 | STAR TV 1080P FHD | — | Türkiye/Türkçe | Kısa AV | 1.35 / 1.753 / 1.487 |
| 878 | 1703 | SUN RTV 720P HD | SunRTV.tr@SD | Türkiye/Türkçe | Kısa AV | 4.696 / 4.305 / 4.644 |
| 979 | 1804 | TON TV 720P HD | TonTV.tr@SD | Türkiye/Türkçe | Kısa AV | 6.969 / 6.044 / 5.587 |
| 1331 | 2156 | TRT 1 | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 3.317 / 2.76 / 2.889 |
| 1333 | 2158 | TRT 1 (BACKUP) | — | Türkiye/Türkçe | Kısa AV | 2.447 / 1.966 / 1.043 |
| 1334 | 2159 | 🟠 TRT 1 (BACKUP) | — | Türkiye/Türkçe | Kısa AV | 1.836 / 1.888 / 1.78 |
| 1335 | 2160 | TRT 1 (BACKUP) | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.594 / 1.438 / 1.399 |
| 1368 | 2193 | TRT COCUK 1440P QHD | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 1.652 / 3.414 / 1.854 |
| 1391 | 2216 | TRT GENÇ 1440P QHD | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 1.195 / 3.197 / 2.844 |
| 1397 | 2222 | TRT HABER (BACKUP) | — | Türkiye/Türkçe | 60 sn AV (3 tur) | 1.588 / 1.478 / 1.529 |
| 1400 | 2225 | TRT HABER 4 720P HD | in3p7jng04mr97m | Türkiye/Türkçe | 60 sn AV (3 tur) | 2.33 / 1.9 / 1.87 |
| 1401 | 2226 | TRT HABER 4 720P HD | in3p7jng04mr97m | Türkiye/Türkçe | 60 sn AV (3 tur) | 0.453 / 0.396 / 0.618 |
| 1402 | 2227 | TRT HABER 1440P QHD | in3p7jng04mr97m | Türkiye/Türkçe | 60 sn AV (3 tur) | 0.72 / 0.628 / 0.586 |
| 1409 | 2234 | TRT MUZIK | — | Türkiye/Türkçe | Kısa AV | 3.783 / 3.399 / 3.751 |
| 1416 | 2241 | TRT MÜZİK 1 1440P QHD | 18ws4yk42js588h | Türkiye/Türkçe | Kısa AV | - / 1.794 / 1.001 |
| 1418 | 2243 | TRT MÜZİK 1440P QHD | 18ws4yk42js588h | Türkiye/Türkçe | 60 sn AV (3 tur) | 0.962 / 0.897 / 1.942 |
| 1442 | 2267 | TRT TÜRK 2 720P HD | xe24vekaidpsql3 | Türkiye/Türkçe | 60 sn AV (3 tur) | 0.517 / 0.27 / 0.28 |
| 1444 | 2269 | TRT TÜRK 1440P QHD | xe24vekaidpsql3 | Türkiye/Türkçe | 60 sn AV (3 tur) | 1.763 / 0.951 / 1.292 |
| 1446 | 2271 | TRT WORLD 1 1440P QHD | j1x67766q1lr7r6 | Türkiye/Türkçe | Kısa AV | 5.29 / - / 4.984 |
| 1464 | 2289 | TV 41 720P HD | TV41.tr@SD | Türkiye/Türkçe | Kısa AV | 5.948 / 4.598 / 4.326 |
| 1539 | 2364 | URFA NATİK TV 720P HD | UrfaNatikTV.tr@SD | Türkiye/Türkçe | Kısa AV | 5.856 / 5.479 / 5.097 |
| 1552 | 2377 | VAN 65 TV | Van65TV.tr@SD | Türkiye/Türkçe | Kısa AV | 3.294 / 4.127 / 4.262 |

## 25 Kasım — yeni paketi henüz olmayan tarihsel pozitif adaylar

Yalnız yeni 27 paketin kapsamadığı pozisyonlardan; açılış ölçülmemiştir. 25 Kasımda 60 sn AV sınıfı üç sağlıklı turun tamamlandığını ispatlamaz.

| YEDEKLER sıra | Genel sıra | Kanal adı | TVG-ID | Bölge ipucu | Tarihsel AV sonucu | Açılış |
|---:|---:|---|---|---|---|---|
| 124 | 949 | AZ STAR TV 1080P FHD | — | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 125 | 950 | AZ STAR TV 1080P FHD | — | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 126 | 951 | BALKAN TÜRK | — | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 188 | 1013 | BURSA AS TV 900P UHD | ASTV.tr@SD | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 287 | 1112 | DREAM TÜRK | — | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 351 | 1176 | FİNANS TURK TV 720P HD | FinansTurkTV.tr@SD | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 352 | 1177 | FİNANS TÜRK TV | — | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 412 | 1237 | HABERTÜRK 2 1080P FHD | gil1w2erz9l7imc | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 413 | 1238 | HABERTÜRK 2 1080P FHD | gil1w2erz9l7imc | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 414 | 1239 | HABERTÜRK 3 1080P FHD | gil1w2erz9l7imc | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 415 | 1240 | HABERTÜRK 4 1080P FHD | gil1w2erz9l7imc | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 544 | 1369 | KANAL FİRAT 720P HD | KanalFirat.tr@SD | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 575 | 1400 | KOCAELİ TV 1080P FHD | KocaeliTV.tr@SD | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 604 | 1429 | LALEGÜL TV 720P HD | LalegulTV.tr@SD | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 700 | 1525 | NUMBER 1 DANCE 720P HD | Number1Dance.tr@SD | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 796 | 1621 | SAT 7 TÜRK 360P SD | — | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 797 | 1622 | SAT 7 TÜRK 1080P FHD | — | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 830 | 1655 | SHOW TV 1 1080P FHD | pvr08e5grfsebfw | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 831 | 1656 | SHOW TV 2 1080P FHD | pvr08e5grfsebfw | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 863 | 1688 | STAR TV | — | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 895 | 1720 | TBMM TV 720P HD | TBMMTV.tr@SD | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 956 | 1781 | TİVİ 6 720P HD | Tivi6.tr@SD | Türkiye/Türkçe | Kısa AV | Ölçülmedi |
| 1341 | 2166 | TRT 1 720P HD | — | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 1372 | 2197 | TRT ÇOCUK 1 1440P QHD | ybv52n8pldp0lfq | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 1373 | 2198 | TRT ÇOCUK 2 1080P FHD | ybv52n8pldp0lfq | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 1404 | 2229 | TRT KURDÎ | — | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 1408 | 2233 | TRT KURDİ ULUSAL | — | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |
| 1437 | 2262 | TRT TÜRK | — | Türkiye/Türkçe | 60 sn AV | Ölçülmedi |

## Logo ve EPG — kesin metadata eşleşmesi ile resmî doğrulamayı ayır

- Güncel YEDEKLER parçasında boş/olmayan logo: 697; boş/olmayan TVG-ID: 1187. Boş TVG-ID tek başına EPG'nin eksik olduğunu kanıtlamaz.
- Kesin resmî logo ataması için yeterli mevcut kanıt: 0 doğrulanmış kayıt. Aşağıdaki eşleşmeler aynı tam TVG-ID + aynı görünen ad + tek mevcut logo URL'si koşulunu sağlıyor; logo görseli ve yayıncı resmiyeti teyit edilmediği için yalnız inceleme adayıdır.
- Tarihsel 19 Kasım [logo inceleme raporu](../v2/reports/logo-current-exact-name-review-20261119.json) resmî logo kanıtı değildir.
- [19 Kasım XMLTV raporu](../v2/reports/task19-current-xmltv-20261119.json) 7 tam ID, bunların ATV.tr, CNBC-E.tr ve DMAX.tr için yayıncı program zamanına ilişkin tarihsel tanık içerir; yayıncı XMLTV ID beyanı doğrulanmış değildir. Güncel madsc-epg.xml içeriği bağlantı boyut sınırı nedeniyle okunamadı; yeni EPG eksikliği veya güncel program ataması kesinleştirilemez. Aşağıda güncel YEDEKLER TVG-ID ile tarihsel XMLTV raporunun tam, büyük/küçük harfe duyarlı eşleşmeleri gösterilir. Resmî EPG tamamlandı: 0.

### Aynı tam TVG-ID + aynı ad ile tek mevcut logo (resmîliği doğrulanmamış)

| YEDEKLER sıra | Ad | TVG-ID | Logo dolu eş kayıt sıraları |
|---:|---|---|---|
| 201 | CEKMEKÖY TV (1080P) | CekmekoyTV.tr@SD | 202 |
| 535 | KANAL D DRAMA (1080P) | KanalDDrama.tr@SD | 537 |
| 536 | KANAL D DRAMA (1080P) | KanalDDrama.tr@SD | 537 |

### Tarihsel tam XMLTV-ID eşleşmeleri

| YEDEKLER sıra | Ad | TVG-ID | 19 Kasım kanıtı |
|---:|---|---|---|
| 98 | ATV | ATV.tr | Yayıncı programı tarihsel tanığı |
| 213 | ❌ CNBC-E | CNBC-E.tr | Yayıncı programı tarihsel tanığı |
| 267 | DMAX | DMAX.tr | Yayıncı programı tarihsel tanığı |
| 385 | GZT (1080P) | GZT.tr | XMLTV ID; yayıncı teyidi bekliyor |
| 591 | KRT | KRT.tr | XMLTV ID; yayıncı teyidi bekliyor |

## Kapanış sınırı

Bu bir mevcut-kanıt raporudur, yeni çalışma veya canlı dil doğrulaması değildir. 26 Kasım 5 paket eksik olduğundan 27 paket üzerinden nihai karar alınmaz. Playlist, parçaları, state.json, güvenlik altyapısı ve kanal kayıtlarına dokunulmaz. Yalnız bu Markdown dosyası eklenir.
