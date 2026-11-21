# Arova — son karar (21 Kasım, 12:40)

Bu dosya üç kaynağı birleştiriyor: üç tasarım (bizim v3/v4, "Electrical Layout", "Print Assembly"), üç araştırma raporu ve kendi ölçümlerimiz (`verify_v3.py`, `challenge_check.py`, `wave_map.py`, parametre taraması). Tüm sayılar 4 duvar baskı, gap 100, 400 g yük ve 40 g elektronik içindir; aksi yazılıysa belirtildi.

## SEÇİLEN: v4 + gövde cepleri
| Karar | Değer | Neden |
|---|---|---|
| Gövde | 2 × 235 × 60 × **80** mm, kapalı, sivri ve kıvrık burun (16 mm) | Parametre taramasında yük ve dalga açısından en iyisi 60 mm genişlik çıktı: yük limiti 786 → 918 g, kayık yükte yatma 5.6° → 3.7° (3 duvar bazında) |
| Gövde arası | 100 mm (toplam 225 mm) | Kayık yükte en az yatma (gap 70'te 6.5°). 250 mm sınırının içinde |
| Güverte | 2 mm takılır plaka | Dayanım payı 10 kat; 3 mm'ye göre 25 g hafif ve ağırlık merkezi daha alçak |
| Elektronik | **Gövdelerin üst yüzündeki ceplere gömülü** (64 × 40 × 22, güvertenin altında) | En alçak konum (KG 45.4 mm). Sıçrayan sudan tam korunuyor. Gövdenin kapalı hava hacmine açılmıyor, yani sızıntı yolu yok |
| Baskı | 4 duvar, akış +%5, 6 üst katman, destek yok | 3 duvar su geçirmezlik için alt sınır (Prusa; 2025 PLA çalışması) |
| Yedek | gap 70 güvertesi | Çok kısa dik yan dalga varsa ya da yazıcı tablası 220 mm ise |

**Sonuçlar:**
- 400 g'da su çekimi 39.0 mm, serbest borda 40.5 mm, GM 122 mm.
- Yük limiti 911 g. Kargo 20 mm kaydırılınca yatma 4.0°.
- En dik dalgada (H 40 mm) güverte kuru (+15 mm pay) ve gemi devrilmiyor (+3.1°).
- **Derinlik 70 → 80 mm (12:37):** yük limiti +%13; en dik dalgada güverte uçlarına gelen su payı −2.2 → +15.3 mm. Bedeli gövde başına +18 g ve 20–50 dk fazla baskı.
- Dalgada her periyotta 30 mm'ye kadar güvenli; yalpa sönümü 0.20 ise 35 mm.
- Dosyaların hepsi su geçirmez, 250 mm içinde ve desteksiz yüzeyi yok.
- Hidrostatik değerler mesh ile %0.35 içinde uyuşuyor.

## ALINMAYANLAR — ve neden
| Fikir | Nereden | Neden alınmadı (ölçüm) |
|---|---|---|
| 270 mm gövde boyu | Electrical Layout | 250 × 250 × 250 kuralını aşıyor, organizatör basmaz |
| Kıçta motor, pervane şaftı, servo | Electrical Layout / Print Assembly | Yarışma itme sistemini test etmiyor. Her şaft deliği bir sızıntı yolu. Puanlamada servoya ek puan yok |
| Üstü açık gövde + vidalı güverte | Print Assembly | Güverte birleşim yeri su hattındaki tek sızdırmazlık noktası olur. Bizim gövdeler kapalı katı |
| Güvertenin altına sarkan pil bölmesi | Electrical Layout | GM'i sadece ~1.7 mm artırıyor, buna karşılık bölmenin dibi su hattına ~8 mm kalıyor ve dalga çarpar |
| Platformu komple kalınlaştırıp içine gömmek (24 mm) | takım fikri | +97 g en tepede: KG 45 → 55 mm, GM 135 → 107, yük limiti 803 → 669 g (−%17). İçi boş 220 mm'lik bir tavan desteksiz basılamaz |
| Güvertede kapaklı kutu | takım fikri | Çalışıyor ve doğrulandı (dosyaları repoda), ama +46 g yukarıda: GM 135 → 125, yük limiti 803 → 759 g. Ceplere göre koruma avantajı yok. **Yedek olarak bekletiliyor** |
| Burun kıvrımını 16 → 8 mm'ye indirmek | direnç araştırması | Test edildi. Su hattı boyu değişmedi (kıvrımın tamamı zaten su altında). Yük limiti 918 → 895 g, güvenli dalga 35 → 30 mm. Geri alındı |
| Gövdeyi 245–248 mm'ye uzatmak | direnç araştırması | Güverte ve kaldırma merkezini kaydırıyor. 250 × 210 tablaya brim ile sığmayabilir. Bugün yetişmez; test sonrasına |
| Kıçı yumuşak daraltmak (25 → 60 mm) | direnç araştırması | Dirence en net kazanç bu. Yeni kod ve tam yeniden doğrulama gerekiyor; bugün yetişmez, CFD sonucuna göre bir sonraki sürüme |
| Yan yüzgeç (bilge keel) | yalpa araştırması | Direnci ~%3–15 artırır (tahmin). Katamaran sönümü muhtemelen zaten 0.15–0.25. Yalnızca yalpa testi ζ < 0.15 çıkarsa |
| Gövde arası 120 mm | parametre taraması | Dalgada kazanç yok (30 mm), toplam genişlik 245 mm, tablaya sığması zor |
| 50 mm gövde (v3) | eski sürüm | Yük limiti ve kayık yükte yatma daha kötü. v4 her ölçütte daha iyi, CFD direnci hariç |
| 3 duvar baskı | eski ayar | Su geçirmezlik için alt sınır. Sızan gövde gemiyi batırır |
| Montaj dosyasını CFD'ye vermek | eski dosya | Parçalar arası 0.1–0.3 mm boşluk CFD ağını bozar. CFD için `arova_v3_CFD_hulls_gap100.stl` kullanılacak |

## Test günü (Pazar sabahı) yapılacaklar
1. **Sızdırmazlık testi:** Her gövdeyi tart, 5–10 dk suda tut, tekrar tart. 0.5 g'dan fazla artış sızıntı demek. Testten önce gövdeler su sıcaklığına gelsin.
2. **Hava deliği:** Gövde üstünde, güvertenin altında 0.8–1 mm. Testlerde bantla kapat.
3. **Güverte:** 4 lastik bant + birleşim yerine bant. Dalga testinden önce salla ve bük.
4. **Yalpa sönümü testi:** 10–15° yatır, bırak, MPU6050 ile kaydet. Uygulamanın 4. sekmesi sönümü (ζ) hesaplıyor. ζ ≥ 0.15 ise dalga riski haritadakinden de küçük.
5. **Meyil deneyi:** Uygulamanın 5. sekmesi gerçek ağırlık merkezini hesaplıyor.
6. **Kablo:** Güverte plakasında cep 1'in üstüne 5–6 mm delik aç; USB-C kablo buradan çıkar (ayrıntı aşağıda).

## Elektrik bağlantısı (Discord malzeme listesine göre, 21 Kasım 12:50)
Etkinlikte verilen parçalar: Arduino Nano, MPU6050, AA pil + pil yuvası, **USB-C test kablosu**, jumper kablolar, bant, sıcak silikon, hortum. Listede SD kart, Bluetooth ya da kablosuz modül **yok**.

**Sonuç: pil kullanmıyoruz, iki cep arasında kablo da yok.**
- MPU6050 verisini kaydetmenin tek yolu Nano'yu USB ile dizüstüne bağlamak (`tools/log_serial.py`). Bu kablo Nano'ya gücü de veriyor. Pil eklemek veri kazandırmıyor, yalnızca ağırlık ve kablo ekliyor.
- **Cep 1:** Nano + MPU6050. MPU'yu Nano'ya 4 dişi-dişi jumper ile bağlayın: VCC → 5V, GND → GND, SDA → A4, SCL → A5. **Breadboard kullanmayın**, cebe (64 × 40 mm) sığmaz. MPU'yu cebin tabanına sıcak silikonla, oku geminin boyuna doğru yapıştırın.
- **Cep 2:** boş ya da ≈15 g denge yükü (örneğin pul/vida bantlanmış). Konmazsa yatma < 0.2°.
- **USB-C kablo:** Cep 1'in üstündeki 5–6 mm güverte deliğinden çıkar. Deliğin etrafı bant ya da sıcak silikonla kapatılır. Kablo havada, gevşek asılı durmalı ki gemiyi çekmesin; istenirse listedeki hortum kılıf olarak geçirilir.
- **Önce kontrol:** Nano'nun soketi USB-C mi? (Verilen kablolar USB-C, yani büyük ihtimalle evet. Mini-B ise görevliden uygun kablo isteyin.)

**Yalnızca jüri kablosuz çalışma isterse (yedek plan):**
- 2×AA (3 V) Nano'yu çalıştırmaz.
- 4×AA (iki 2'li yuva seri ya da bir 4'lü yuva) → **VIN** pinine. 3×AA → **5V** pinine. 4×AA'yı asla 5V pinine bağlamayın (≈6.4 V, Nano'yu bozar).
- Pil cep 2'de durur. İki kablo (kırmızı → VIN/5V, siyah → GND) güverte deliklerinden geçer, güverte üstünde bantlanır. Bağlamadan önce multimetreyle voltajı ölçün.
- Bu durumda veri kaydı olmaz (kaydedecek yer yok); sadece gemi elektronikle çalışmış olur.
