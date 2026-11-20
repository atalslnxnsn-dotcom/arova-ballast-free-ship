# Fikir Gecesi — 2026-11-20  (dal: fikir-gecesi/2026-11-20)

Hedef: Arova v3 ballast-free katamaranı yarın (Cmt 14:00 teslim) 3D baskıya hazır, çift kontrollü, kazanacak hale getirmek.
Not: Codex kotası 22 Kasım 23:28'e kadar dolu; ikinci görüş yerine bağımsız yöntemle (STL'nin kendisinden) doğrulama yapılıyor.

## Yapılanlar
- [x] Bağımsız STL doğrulama aracı (`print/v3/verify_v3.py`) — su geçirmezlik, 250 mm, baskı yönünde sarkma, mesh'ten hacim ile hidrostatik tablo karşılaştırması (en kötü fark %0.15), güverte oturma boşluğu (0.30 mm/yan), CFD kabuk aralığı. İki gerçek sorun buldu (aşağıda havuzda #1 ve #2).

- [x] Demihull STL baskı yönünde — dosya artık düz üst yüzü tablada; dosya yönündeki sarkma 22 cm² → 0 (verify_v3), hidrostatik kontrol değişmedi (%0.15) (commit 7869fa6)
- [x] CFD-güvenli dosya — `arova_v3_CFD_hulls_gap100.stl` (yalnız ıslak geometri, 2 kabuk 100 mm aralıkla); eski montaj dosyası sadece görsel; verify_v3 artık TÜM KONTROLLER GEÇTİ (commit 937e867)
- [x] Fil ayağı payı — gövdenin tablaya gelen üst kenarlarına 0.8 mm × 45° pah (tabla yüzünde genişlik 48.4 → 0.8 mm'de 50.0); güverte flanşı 0.30 mm boşlukla sıkışmaz; hidrostatik etkisiz (su hattının 30+ mm üstü) (commit 5e95dc7)
  - Neden sıra değişti: #3 baskı sayfası daha yüksek skorlu ama sayfadaki sayılar kesin geometriye bağlı, önce geometri.
- [x] Kütle ve baskı süresi tahmini (`print/v3/print_estimate.py`, STL'den alan+hacim) — set: su geçirmez profil 380 g / tek yazıcı ~7–17 sa; hızlı profil 236 g / ~4–11 sa; 4 parça paralel basılırsa en uzun parça ~1.5–5.6 sa (commit a1b8d88)
  - Bulgu: güverte (123 g) neredeyse gövde kadar ağır ve geminin en üstünde → KG'yi yükseltiyor. Havuza #14 eklendi.
- [x] Güverte 3 → 2 mm — dayanım çift kontrolü (400 g tek nokta yük, 100 mm açıklık, E=2.5 GPa): sehim ~1 mm, 2.9 MPa, 10× pay; güverte 123 → 98 g (su geçirmez profil), 400 g'da GM 117 → 122 mm, fribord 33.7 → 34.9 mm; verify + testler geçti (commit a779f20)
- [x] Yarışma kontrolü uygulamanın kendi modeliyle (`print/v3/challenge_check.py --brief`, kütle/KG STL'den) — tüm statik testler geçti; dalga: gap 100 kargo güvertesi kuru (+2.4 mm) ama 0.5 s yan dalgada yalpa rezonansı devrilme payı −1.2° (H 40 mm); gap 70 tüm dalga kontrollerini geçiyor. `wave_motions(x_points=…)` eklendi (+test) (commit 12d156f)
  - Dürüstlük notu: eski brief tablosu sadece T=0.8 s'ye bakıp "✅ su yok" diyordu; ince ızgara gerçek zayıf noktayı gösterdi.

## Başarısız

## Fikir havuzu (henüz yapılmadı)
| # | Fikir | Fayda | Zorluk | Skor | Not |
|---|---|---|---|---|---|
| 3 | Organizatöre tek sayfa baskı sayfası (hangi dosya, kaç adet, yön, ayar, süre/kütle) | 5 | 2 | 8 | yarın 14:00 teslim |
| 15 | Uygulamadaki v3 varsayılan kütlesini STL'den ölçülen tahmine çek (324 → ölçülen) | 3 | 1 | 5 | #14 sonrası |
| 6 | Güverteye yük şeridi/işaret oluğu (ortada ±20/40/60 mm): meyil deneyi ve kargo yerleşimi hızlı ve doğru | 3 | 2 | 4 | ekstrüzyon kesitiyle kolay |
| 16 | Dalga eşik haritası: H×T ızgarasında gap 70 / 100 için geçti-kaldı; hangi koşulda hangi güverte | 5 | 2 | 8 | jüri sorusu: 'dalga büyürse?' |
| 17 | Yalpa rezonansını dalga bandından uzaklaştır (KG/k/gap ayarı) - tasarım seçeneklerini tara | 4 | 3 | 5 | #16 sonrası |
| 7 | Uygulamada "Yarışma kontrolü" paneli: 150/250/400 g + dalga senaryoları tek tıkla geçti/kaldı tablosu | 4 | 3 | 5 | jüriye tek ekranda kanıt |
| 8 | Tasarım gerekçesi sayfası (neden katamaran, neden ince gövde, neden dalga kesici burun; kaynaklarla) | 4 | 2 | 6 | sunum + inovasyon puanı |
| 13 | Eski `arova_v3_assembly_gap100_CFD.stl` adını `..._display.stl` yap (ad yanıltıcı; gece kuralı: var olan dosya silinmez) | 3 | 1 | 5 | sabah kullanıcı kararı |
| 9 | Kapalı gövde içinde hava genleşmesi/su alma riski notu ve vernik prosedürü | 2 | 1 | 3 | |
| 10 | Gövde baş-kıç simetrik değil: kargo konumu LCB'ye göre işaretli "yükleme çizgisi" güvertede | 3 | 2 | 4 | #6 ile birleşebilir |
| 11 | Monohull karşılaştırma için tek gövde + 50 g sabit demo kartı (devrilir/dik durur) | 3 | 1 | 5 | sunum anı |
| 12 | Cesur: uygulamada STL yükle → otomatik hidrostatik tablo (herhangi bir gövde için) | 5 | 4 | 6 | büyük; ilk adımı ayrı tur |
