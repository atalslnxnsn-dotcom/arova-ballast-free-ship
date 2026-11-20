# Fikir Gecesi — 2026-11-20  (dal: fikir-gecesi/2026-11-20)

Hedef: Arova v3 ballast-free katamaranı yarın (Cmt 14:00 teslim) 3D baskıya hazır, çift kontrollü, kazanacak hale getirmek.
Not: Codex kotası 22 Kasım 23:28'e kadar dolu; ikinci görüş yerine bağımsız yöntemle (STL'nin kendisinden) doğrulama yapılıyor.

## Yapılanlar
- [x] Bağımsız STL doğrulama aracı (`print/v3/verify_v3.py`) — su geçirmezlik, 250 mm, baskı yönünde sarkma, mesh'ten hacim ile hidrostatik tablo karşılaştırması (en kötü fark %0.15), güverte oturma boşluğu (0.30 mm/yan), CFD kabuk aralığı. İki gerçek sorun buldu (aşağıda havuzda #1 ve #2).

## Başarısız

## Fikir havuzu (henüz yapılmadı)
| # | Fikir | Fayda | Zorluk | Skor | Not |
|---|---|---|---|---|---|
| 1 | Demihull STL'sini baskı yönünde (güverte yüzü tablada) dışa aktar; yelken yönündeki kopya sadece CFD/montaj için | 5 | 1 | 9 | verify: 22 cm² sarkma (burun rocker) dosya yönünde |
| 2 | CFD dosyasını CFD-güvenli yap: tek parça su altı geometrisi (iki gövde) + ayrı tam montaj; 0.1–0.3 mm kabuk aralığı yok | 5 | 2 | 8 | organizatör yazılımı ağ oluştururken patlamasın |
| 3 | Organizatöre tek sayfa baskı sayfası (hangi dosya, kaç adet, yön, ayar, süre/kütle) | 5 | 2 | 8 | yarın 14:00 teslim |
| 4 | Fil ayağı payı: gövde güverte yüzü tablada basılınca üst kenar genişler; flanş girişine pah + boşluk 0.3→0.4 | 4 | 2 | 6 | oturma riski |
| 5 | Hızlı baskı profili ve gerçekçi süre/kütle tablosu (2 duvar / 3 duvar) | 4 | 2 | 6 | 330 g PLA tek yazıcıda çok uzun sürebilir |
| 6 | Güverteye yük şeridi/işaret oluğu (ortada ±20/40/60 mm): meyil deneyi ve kargo yerleşimi hızlı ve doğru | 3 | 2 | 4 | ekstrüzyon kesitiyle kolay |
| 7 | Uygulamada "Yarışma kontrolü" paneli: 150/250/400 g + dalga senaryoları tek tıkla geçti/kaldı tablosu | 4 | 3 | 5 | jüriye tek ekranda kanıt |
| 8 | Tasarım gerekçesi sayfası (neden katamaran, neden ince gövde, neden dalga kesici burun; kaynaklarla) | 4 | 2 | 6 | sunum + inovasyon puanı |
| 9 | Kapalı gövde içinde hava genleşmesi/su alma riski notu ve vernik prosedürü | 2 | 1 | 3 | |
| 10 | Gövde baş-kıç simetrik değil: kargo konumu LCB'ye göre işaretli "yükleme çizgisi" güvertede | 3 | 2 | 4 | #6 ile birleşebilir |
| 11 | Monohull karşılaştırma için tek gövde + 50 g sabit demo kartı (devrilir/dik durur) | 3 | 1 | 5 | sunum anı |
| 12 | Cesur: uygulamada STL yükle → otomatik hidrostatik tablo (herhangi bir gövde için) | 5 | 4 | 6 | büyük; ilk adımı ayrı tur |
