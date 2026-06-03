# Senaryo Bulgulari — Kavşak Trafik Işığı Simülasyonu

4 saatlik koşum × 5 seed × **4 kontrolcü**. Karşılaştırma tablosu
`results/comparison.csv`'de; grafikler `results/comparison_*.png` ve
`results/wait_time_distribution.png`.

## Ana cikarimlar — tek cumlede

- **Sabit Zamanlı** (referans baseline): yön yoğunluğuna duyarsız; her
  yöne eşit 30 sn yeşil. Ortalama bekleme **43.7 sn**, acil araç
  beklemesi **40.4 sn**. Boş yönü bile yeşil tutar — verimsiz.
  Fairness 0.996 (eşit ama hepsi kötü), CO2 **5737 g** (4x verimsizlik).

- **Adaptif**: en uzun kuyruga öncelik + queue × 3 sn yeşil süresi.
  Ortalama bekleme **9.7 sn** (sabit'e göre **%77.8 düşüş**), acil araç
  beklemesi **7.2 sn**. p95 = 29.2 sn. CO2 1271 g (-78%).

- **Tahmine Dayalı** (final eklemesi, hibrit): `score = current + 0.3 ×
  max(0, predicted - current)`. Saf trend mantığı adaptive'den her seed'de
  daha kötüydü (sweep doğruladı); hibrit mantık ile **eşdeğer ortalama**
  (9.71 vs 9.70 sn) AMA p95 %9 daha iyi (26.5 sn), acil %5 daha iyi (6.83 sn),
  **fairness %4.5 daha iyi** (0.891).

- **Acil Öncelikli**: adaptif üzerine acil araç preemption'i. Ortalama
  bekleme **10.1 sn** (adaptif ile neredeyse ayni), ama acil araç
  beklemesi **5.8 sn** — adaptif'e göre **%19.4 düşüş**, sabit'e
  göre **%85.7 düşüş**.

## Karşılaştırma tablosu (5 seed × 4 saat)

| Kontrolcü | Ort. | **p95** | Acil | Throughput | **Fairness** | **CO2 (g)** | Preempt |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sabit Zamanlı     | 43.72 sn | 101.52 sn | 40.43 sn | 85.2/sa | 0.996 | 5737 | 0   |
| Adaptif           |  9.70 sn |  29.24 sn |  7.20 sn | 85.2/sa | 0.852 | 1271 | 0   |
| **Tahmine Dayalı (hibrit)** | 9.71 sn | **26.51 sn** ↓ | **6.83 sn** ↓ | 85.2/sa | **0.891** ↑ | 1273 | 0 |
| Acil Öncelikli    | 10.11 sn |  29.91 sn | **5.78 sn** | 85.3/sa | 0.864 | 1328 | 7.0 |

## Sunum hikayesi (4 cumle)

1. **Sabit Zamanlı baseline'i goster** — 43.7 sn ortalama bekleme,
   acil araç 40 sn bekliyor. Fairness 0.996 görüntüsünde "adil" ama
   herkesi eşit ölçüde **kötü** bekletiyor; CO2 5737 g (4x verimsizlik).

2. **Adaptif'e geciste %78 düşüş** — sadece "en uzun kuyruga yeşil"
   kuralinin etkisi çok büyük; ortalama bekleme 9.7 sn, CO2 1271 g
   (sabit'in dörtte biri). Fairness 0.852 (biraz düştü) ama bu
   "performans için biraz adalet feda" — toplam refah çok daha yüksek.

3. **Tahmine Dayalı (hibrit) — trend-aware 4. mantık** — adaptifin "anlık"
   kararı + artan trend bonusu. Ortalama bekleme **adaptif ile eşdeğer**
   (9.71 vs 9.70 sn) AMA **p95 −%9, acil −%5, fairness +%4.5**. Trend
   bonusu ortalamayı kaybetmeden adalet ve kötü uç boyutlarında iyileşme
   sağlıyor. **Saf trend mantığı (eski tasarım) sweep ile elendi**:
   16 parametre kombinasyonu test edildi, hiçbiri adaptive'i geçemedi.

4. **Acil Öncelikli ile acil araç bekleme yarısı** — adaptif zaten
   iyiydi, ama bir ambulansa 8 sn bile çok. Preemption ile 5.8 sn'ye
   indirildi (sabit'e göre %86 düşüş). Normal araçlar bunun bedelini
   neredeyse hiç odemiyor (4 saatte sadece 7 kez tetikleniyor).

## Genişletilmiş metrik perspektifi (Faz Final)

### Percentile — "kötü uç" bakışı

Ortalamalar yanıltıcı. Adaptif kontrolde p50 = 6.17 sn (yarısı 6 saniyenin
altında) ama p95 = 24.21 sn, p99 = 45.74 sn — her 20 sürücüden 1'i 24
saniye bekliyor. Sunumda "ortalama optimize ettik" yetmez, "kötü uç
kullanıcıları da düşürdük" demek lazım — p95 adaptifte sabit'ten 4 kat
daha düşük (29 vs 101 sn).

### Fairness — "iyi sayı" değil, "doğru yorum lazım"

Jain's fairness index sadece **yönler arası dağılımın eşitliğini** ölçer.
Sabit kontrol F=0.996 ile "en adil" görünür ama bu, **eşit ölçüde kötü**
bekletmek anlamına gelir. Sunumda "fairness alone" tuzağına düşmeyin —
fairness × ortalama bekleme birlikte okunmalı. Adaptifin F=0.852'si
"kötü" değil; performans karşılığında küçük bir adalet feragati.

### Çevresel etki — sabitin gerçek bedeli

Idle yakıt formülü (0.6 L/saat × 2.31 kg CO2/L) ile:
- Sabit: **5737 g CO2 / 4 saat** (47.8 L benzinin idle eşdeğeri)
- Adaptif: 1271 g (%78 az)
- Tahmine Dayalı: 1673 g
- Acil Öncelikli: 1328 g

Sunum kozu: "Sezgisel sabit kontrolün maliyeti sadece zaman değil, **4
kat daha fazla CO2**". Bir otomobil 120 g/km CO2 üretir → sabit kontrolün
fazlasıyla **37 km'lik araba sürüşüne eşdeğer emisyon** üretiyor (4 saat,
1 kavşak için).

### Saatlik heatmap — homojenlik yok

Adaptif kontrolde:
- Kuzey: 3.8 / 7.7 / 2.3 / 1.4 sn — hep en hızlı (gelişim hızı düşük)
- Güney: 12.3 / 19.1 / 13.5 / 13.7 sn — en yoğun (peak saat 1'de)
- Doğu: 13.9 / 15.2 / 11.4 / 12.6 sn
- Batı: 16.1 / 14.9 / 14.6 / 16.4 sn

Saatlik throughput: 88 / 85 / 77 / 69 araç — talep yoğun saatten sonra
azalıyor. Heatmap, hocaya "sistem dinamik, statik analiz yetmez" mesajını
verir.

## Çıktı dosyalari

- `results/comparison.csv` — **4 kontrolcü** × tüm KPI'lar (p95, fairness,
  CO2 dahil), mean + std
- `results/comparison_avg_wait.png` — ortalama bekleme bar chart
- `results/comparison_emergency_wait.png` — **acil araç bekleme (sunum altin grafigi)**
- `results/comparison_throughput.png` — throughput karşılaştırma
- `results/wait_time_distribution.png` — bekleme süresi histogrami (4 alt-grafik)

## Notlar

- Preemption "fiyati": adaptif 9.70 → acil öncelikli 10.11 sn, yani
  normal araçlar için ortalama **+0.41 sn** ekstra bekleme. Bu, 4
  saatlik koşumda ortalama 7 tetiklenmenin (sn cinsinden ~35 sn ekstra
  yeşil-kapanma) etkisi.

- Adaptif/Predictive/Preemptive arasında **throughput farki yok** (~85/sa)
  — kontrolcünün islevi bekleme suresini optimize etmek, gelen aracı
  durdurmak degil.

- Tahmine Dayalı, adaptifin "anlık" yerine "yakın gelecek" mantığı.
  Sabit talepte adaptifle çok benzer; talep paterni hızlı değişen
  senaryolarda öne çıkar. 4 saatlik tek-pik koşumumuzda fark küçük
  (12.7 vs 9.7 sn) ama fairness'te küçük bir avantajı var (0.865 vs 0.852).
