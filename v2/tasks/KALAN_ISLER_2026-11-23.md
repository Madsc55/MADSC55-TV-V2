# MADSC55 TV V2 — Kalan İşler ve Kabul Planı
Tarih: 2026-11-23
Durum: TAKİPTE — kullanıcı talimatıyla kayıt altına alındı.

## Genel durum
- Planlama amaçlı tahmini ilerleme: %75 tamamlandı / %25 kaldı.
- Bu yüzdeler CI veya üretim ortamı tarafından ölçülmüş kesin oranlar değildir.
- 34/34 idari görev kapanışı, teknik kabulün %100 olduğu anlamına gelmez.
- Nihai %100 yalnızca aşağıdaki kabul kanıtlarıyla ilan edilir.

## Değişmez kurallar
1. Tek ana playlist: MADSC55_TV_IBO_CALISANLAR_TEST.m3u8. Yeni test/yan playlist oluşturma.
2. YEDEKLER dışındaki ana kategorileri ve kanal kimliklerini koru; 2.500'lük test döngüsü düzenini bozma.
3. Türk/Yabancı arşivlerine taşınan kayıtlar YEDEKLER'den düşmeli; işlemler tekil kimlik ve sayım denetimli olmalı.
4. 685 SECURITY HOLD kayıt, açık yetkilendirme ve güvenli doğrulama olmadan canlı teste veya serbest dolaşıma çıkarılmaz.
5. Daha önce çıkarılmış 48 engelli kanal geri eklenmez; orijinal olmayan logo kullanılmaz.
6. Gerçek ses/görüntü ve İBO Player kabul testleri son aşamada yapılır.

## Öncelikli takip tablosu
| No | İş | Kabul kanıtı | Durum |
|---|---|---|---|
| 01 | main playlist güncel envanter ve kategori sayımlarını doğrula | EXTINF ve kategori sayımı, önce/sonra fark raporu | BEKLİYOR |
| 02 | 685 kayıt için salt-okunur önizleme ve yetkili arşiv taşıma akışını tamamla | PR #654 testleri, workflow çıktısı, kimlik/özet kontrolü | BEKLİYOR |
| 03 | HTTP sağlık taramasını tüm kapsamda hatasız bitir | Tamamlanan Actions run, rapor ve hata ayrımı | BEKLİYOR |
| 04 | Tek playlist üzerinde PR tabanlı uçtan uca otomasyonu doğrula | İkinci çalıştırmada tekrar eklemeyen/idempotent test ve PR diff | BEKLİYOR |
| 05 | Kaynak keşfi ve 404/429/503 yeniden değerlendirmesini tamamla | Kaynak bazlı sonuç, yanlış pozitif kontrolü | BEKLİYOR |
| 06 | TÜRK/YABANCI ayrımı ve arşiv geçişlerini doğrula | Ses/altyazı/ülke kanıtı, kimlik ve kategori sayım testleri | BEKLİYOR |
| 07 | EPG eşleşme ve kapsama eksiklerini kapat | XMLTV ID eşleşme raporu | BEKLİYOR |
| 08 | Eksik gerçek kanal logolarını tamamla | Doğrulanmış kaynak URL, yanlış eşleşme yok | BEKLİYOR |
| 09 | Aynı URL, tarihsel kuyruk ve liste tutarsızlıklarını temizle | Deduplikasyon ve kimlik mutabakat raporu | BEKLİYOR |
| 10 | Bağımsız şifreli yedek ve geri yükleme kanıtı üret | Ayrı ortamda restore denemesi ve bütünlük sonucu | BEKLİYOR |
| 11 | FFmpeg/HLS ağ erişim sınırları ve CI güvenliğini kabul et | Fail-closed güvenlik kapıları ve regresyon testleri PASS | BEKLİYOR |
| 12 | Son aşamada canlı AV, kanal sürekliliği ve gerçek İBO Player testleri | Gerçek cihazda doğrulanmış test raporu | EN SON |

## Sıra
Aşama 1: #01, #02, #03, #09, #11 — temel doğruluk ve güvenlik.
Aşama 2: #04, #05 — otomasyon ve kaynak keşfi.
Aşama 3: #06, #07, #08, #10 — içerik kalitesi ve kurtarma.
Aşama 4: #12 — en son gerçek yayın ve İBO Player kabulü.

## Referanslar ve açık kararlar
- PR #654: 685 kayıt arşiv önizlemesi; CI/merge sonucu ayrıca doğrulanacak.
- PR #651: ekran görüntülerinden çıkarılmış eksik işler.
- PR #650: keşif ve sağlık taraması planı.
- PR #641: 404 sonrası envanter/güvenlik kapısı.
- Tarihsel sayılar güncel main üzerinden yeniden hesaplanmadan kesin kabul edilmez.
- Her tamamlanan madde için commit/PR, CI run, çıktı ve kabul tarihi eklenir.
- Yeni iş çıktığında bu tek planda güncellenir; biten işler tekrarlanmaz.
