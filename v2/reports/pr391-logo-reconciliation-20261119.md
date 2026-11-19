# PR #391 — 19 Kasım 2026 güvenli logo mutabakatı

## Doğrulanmış durum
- Ana korumalı dal: `main` commit `43dcebdbad3014b7850ab3bbd93c257ebdcd77f0`.
- Güncel ana İBO playlist blob SHA: `25a015401dd09c082b0d766c18d54e54f4a4b44d`.
- Güncel playlist: 2.914 `#EXTINF` kaydı, bunların 2.076'sı `🗂️ YEDEKLER (2076)` kategorisinde.
- PR #391 playlist sürümü: 3.338 `#EXTINF` kaydı. Eski sürümle güncel sürüm arasında URL üzerinden karşılaştırmada eski PR'a özgü 419 kayıt bulundu; güncel listede boş logo alanına karşılık eski PR'da dolu logo alanı bulunan 217 kayıt saptandı. Bu 217 kayıt **doğrulanmış logo eşleşmesi değildir**; URL bazlı eşleşme tekrarları ve kanal kimliği ayrıca incelenmelidir.
- PR #391 yalnızca `MADSC55_TV_IBO_CALISANLAR_TEST.m3u8` dosyasını değiştiriyor; GitHub değişiklik yaması boyut nedeniyle sağlanmıyor.
- PR #391: merge conflict (`dirty`), Production Security Gate **FAILURE**, başarısız adım: `Fail closed on changes to production trigger/write policy`.

## Karar / güvenlik sınırı
- #391 eski playlistini `main` üzerine **asla komple kopyalama** veya zorla birleştirme. Mevcut 2.076 YEDEKLER kaydını ve diğer kategorileri koru.
- Ana playlist dışında yeni test playlisti, YEDEKLER_TEST kategorisi oluşturma; 48 engelli kanalı geri ekleme; kaldırılmış ilk-1003 kuralını uygulama.
- Logo işi için aynı kanalın **kimlik + yayın URL + ad** eşleşmesini doğrula; yalnızca eksik ve resmî/orijinal olduğu kanıtlanan logo bağlantılarını aday olarak belirle. Tekrarlanan URL'lerde farklı kanal kimlikleri olabileceğini dikkate al.
- Önce güncel main ile dar kapsamlı, kanal sayısını/sırasını/URL'lerini değiştirmeyen değişiklik önerisi hazırla. Production Security Gate SUCCESS olmadan merge etme.
- Sistem kurulumu tamamlanmadan yeni kanal araması, AV testi veya IBO Player testini başlatma.

## Önceki işler
- #421, #425, #443: merged ve ilgili Production Security Gate SUCCESS olarak doğrulandı.
- #427: closed, merged değil; eski başarılı test sonucu tek başına merge anlamına gelmez.
- #391: açık ve bloklu; bu rapor işi tamamlandı anlamına gelmez.
