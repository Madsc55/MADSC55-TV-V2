# Birleşik tarama #61 — sonuç ve yapılacaklar

Kaynak: GitHub Actions run 40758418496, commit 50a7a395; turkish-stream-review artifact 12851805839 (28 Ekim 2026). Bu belge yalnızca kanıtları özetler; otomatik kanal onayı değildir.

## Kesin sonuçlar
- Workflow başarılı; 42/42 kaynak erişilebilir; 27.047/27.047 benzersiz aday test edilmiş; tarama kapsamı tam.
- 11.808 VIDEO_DECODED, 15.239 görüntü doğrulanamayan/reddedilen; otomatik onaylanan kanal **0**.
- Triage: PLAYBACK_REJECTED 15.239; VIDEO_NO_AUDIO 1.810; VIDEO_METADATA_GAPS 1.364; VIDEO_IDENTITY_REVIEW 8.634.
- Kimlik tutarlılığı: 8.593 tek kaynak incelemesi, 41 çakışma incelemesi.
- Metadata: 11.749 EPG ID eksik; 5.699 logo eksik; 2.234 kategori eksik. Bu sayılar birbiriyle örtüşebilir.
- Mevcut IBO: 840 playlist girdisi, 13 kategori, iki özgün yedek (DHA CANLI 720P HD ve TRT 1 1440P QHD) korunmuş.
- NewlistTR: 154 kaynak girdisi, 153 test, 22 kısa video çözümleme; 0 test bekleyen.
- Kısa çözümleme sonucu 12 geçici inceleme girdisi; yayıncı kimliği ve uzun süreli çalışma doğrulanmış değil.
- Mevcut playlist URL çakışması: 2 çapraz kanal kimliği vakası. Yalnızca raporla; otomatik silme/birleştirme yapma.
- 139 mevcut kanal ölçüm adayı, 127 ölçülmüş; 32 yayın için üç kararlılık örneği. Bu 24 saat kesintisizlik kanıtı değildir.

## Bir sonraki tek birleşik iş akışına ilişkin kararlar
1. #61'in mevcut raporlarını yeniden taramadan kullan; #60, #2, #3 testlerini tekrar etme.
2. Önce 41 kimlik çakışmasını, 2 mevcut playlist URL çakışmasını ve 12 geçici inceleme girdisini gözden geçir. İsim veya URL benzerliğine bakarak otomatik kabul/ret yapma.
3. 1.810 ses eksikliği, 1.364 metadata eksikliği ve EPG/logo/kategori boşluklarını tek raporda takip et; kaynağı doğrulanmayan metadata uydurma.
4. Yayıncı kimliği, haklar, EPG/logo doğruluğu ve uzun süreli stabilite doğrulanmadan bulunan URL'leri canlı IBO'ya taşımama.
5. Tek birleşik workflow'u koru; güvenlik ve mevcut korumalar dışındaki gereksiz test çoğaltmalarını yapma.

## Dokunulmayacaklar
Canlı IBO playlist, FAVORİLER, 13 kategori ve iki özgün YEDEKLER. Bu rapor yalnızca yeni bir doküman olarak eklendi; canlı yayın dosyalarını değiştirmez.
