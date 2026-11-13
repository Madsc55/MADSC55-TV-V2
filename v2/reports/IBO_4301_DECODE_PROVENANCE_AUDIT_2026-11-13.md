# İBO 4.301 aday — artifact bütünlüğü ve decode kanıtı ayrımı (13 Kasım 2026)

**Sonuç:** Gerçek Actions artifact'inin M3U parçaları **yapısal olarak doğrulandı**. Eski tarama koşusunun `AV_VERIFIED` alanı **FFprobe akış metadatası** anlamına geldiğinden gerçek video ve ses karelerinin çözüldüğü **bu artifact ile kanıtlanmadı**. Gerçek IBO cihaz testi ve bağımsız harici şifreli restore da açık.

## Bağımsız, salt okunur inceleme

- Kaynak: [Actions #43412576224](https://github.com/Madsc55/MADSC55-TV-V2/actions/runs/43412576224), commit `e4917753174d16b7c2e1f1abe38ad804f069e58a`, artifact `14033805492` (`v2-real-scan-evidence`).
- Artifact ZIP SHA-256: `139c8a0868f35d4b64cd55a17bcbd56325d8e3c87b5d07295028bb4d56e832a6`. Bu değer GitHub artifact digest'i ve indirilen ZIP baytlarından ayrıca hesaplanan digest ile eşleşti.
- `IBO_AV_VERIFIED_1000_PART*.m3u8`: **1000, 1000, 1000, 1000, 301** kayıt. `IBO_AV_VERIFIED_2000_PART*.m3u8`: **2000, 2000, 301** kayıt.
- Her grupta **4301** HTTP(S) URL, **4301** farklı URL; URL tekrarı, eksik `#EXTINF` eşlemesi, hatalı `#EXTM3U` başlığı bulunmadı. Her iki gruptaki URL'ler **aynı sırada**.
- URL sırasının SHA-256 özeti (gizli akış URL'leri yayımlanmadan): `95eb88d14c4f5a0ee8aaaac2017a63d037b9ebef982ebb2b7d9518dc63a62064`.
- Artifact raporu: `unique_new_candidates=13735`, `av_verified=4301`, `unverified_or_failed_candidates=9434`, `mock_data_used=false`, `archive_restore_test_passed=true`, `playback_verified_on_device=false`. Archive restore alanı aynı koşudaki testtir, bağımsız bulut geri yükleme değildir.

## Kritik decode-provenance ayrımı

Taramayı gerçekten çalıştıran eski commit `e491775...` içindeki `v2/stream_probe.py`, `ffprobe` çıktısında bir video ve bir ses codec akışı görürse `AV_VERIFIED` döndürüyordu. `v2/real_ibo_scan.py` bu etiketi paketlemeye taşıdı. O sürüm **FFmpeg video/audio frame decode işlemi yapmadı**. Dolayısıyla ZIP'deki 4301 kayıt, gerçek yayın AV decode veya yayıncı kimliği kabulü değildir; yalnızca eski koşulun medya akışı metadatası tespiti ve M3U yapı bütünlüğüdür. Kanalların fiilen oynatılamadığı da iddia edilmez: bu henüz ölçülmemiştir.

PR [#197](https://github.com/Madsc55/MADSC55-TV-V2/pull/197), merge `e06065aa2ffd7b897e3f715a513b8efef3cb5978` ve Actions `43483524794` SUCCESS ile güncel scanner gerçek video/ses decode sonucunu `decoded_av_verified=true` ve `decode_status=DECODED_AV` olarak şifreli envantere yazar. `export_ibo_batches.py` yalnızca bu **güncel, açık decode kanıtlı** kayıtları AV-doğrulanmış pakete alır; eski salt `AV_VERIFIED` etiketini kabul etmez. Bu yeni kural eski ZIP'ye geriye dönük gerçek decode kanıtı kazandırmaz.

**Kabul durumu:** #28–#30 için paket oluşturma ve M3U yapı bütünlüğü **kanıtlı ara aşama**; gerçek decoded AV, yayıncı atfı, IBO cihazı ve bağımsız harici restore henüz **açık**. #31–#33 nihai kabul **açık**. Ana İBO, YEDEKLER, YENİLER, FAVORİLER değiştirilmedi; bu denetimde yeni internet kanal taraması yapılmadı.
