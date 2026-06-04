# Akıllı Kavşak Trafik Işığı Simülasyonu

Dört yollu bir kavşağı, **dört farklı trafik ışığı kontrol yöntemiyle**
benzetir ve karşılaştırır: sabit zamanlı, uyarlanır (kuyruk uzunluğuna
göre yeşil süresi), **tahmine dayalı** (son bir dakikalık eğilimden
yakın geleceği tahmin) ve acil öncelikli (ambulans görülürse mevcut
yeşili kapatıp acil yöne öncelik).

> **Özet bulgu**
>
> Sabit yöntemde **ambulans 40 saniye bekliyor**. Uyarlanır yöntem bunu
> **7 saniyeye** düşürüyor. Acil öncelikli yöntem **6 saniyeye** —
> sabit yönteme göre **yedi kat fark**. Aynı kavşak, dört farklı mantık;
> doğru kararı sezgi değil benzetim verisi gösterdi.
>
> **Final genişletmesi:** 4. yöntem (tahmine dayalı) + dört yeni ölçüt
> (bekleme dilimleri %50–%99, yön adaleti, CO2 / yakıt tahmini, saatlik
> bekleme haritası) eklendi. Sabit yöntem adil görünüyor (adalet 0.996)
> ama herkesi eşit ölçüde bekletmenin **4 katı CO2** maliyeti var.
> Tahmine dayalı yöntem: aynı ortalama, en kötü %5 −%9, acil −%5,
> adalet +%4.5 — eğilim bonusu ortalamayı kaybettirmeden adaleti
> iyileştiriyor.

## Özellikler

- **4 yönlü kavşak modeli** (Kuzey / Güney / Doğu / Batı) ayrı kuyruklarla
- **4 yöntem** — sabit zamanlı, uyarlanır, tahmine dayalı, acil öncelikli
- **Saatlik değişken trafik** (07-09 ve 17-19 yoğun saatler)
- **Acil araç modeli** (%5 olasılık, ayrı ölçüm)
- **Genişletilmiş ölçütler** — bekleme dilimleri (%50–%99), yön adaleti,
  CO2 / yakıt tahmini, saatlik bekleme haritası, yön bazlı en uzun kuyruk
- **Çoklu tekrar** — istatistiksel güven için
- **Etkileşimli panel** — 7 sekme (sonuçlar / karşılaştırma / dağılım /
  saatlik bekleme / ani talep / katsayı denemesi / kavşak görseli)
- **Ani talep senaryosu** — bir yöne ani yığılma; sabit yöntem 67 kat
  performans çöküşü yaşar, tahmine dayalı yöntem eğilim avantajı gösterir
- **İstatistiksel güvenilirlik** — Mann-Whitney U testi:
  en kötü %5 (p=0.013), yön adaleti (p=0.0018)
- **92 birim test** — tip denetimi ve biçim denetiminden temiz geçer

## Mimari

```
                    +----- Kuzey kuyruğu -----+
                    |                          |
                    |   simpy.Store (FIFO)     |
                    |                          |
                    +----- (4 yön için ayrı) --+
                              |
                              v
                     +---- KAVSAK ----+
                     | 4 sinyal      |       Sabit / Adaptif /
                     | (LightState)  | <---- Acil Öncelikli kontrolcü
                     +---- 1 çevrim -+        (controllers/*.py)
                              |
                              v
                     +---- Çıkış ----+
                     |  Throughput   |   Metrik logger
                     |  KPI'lara yaz |  (metrics/metrics_collector.py)
                     +---------------+
```

Her aşama bir SimPy süreci. Polling pattern (her 0.5 sn kuyruga bak) —
kasitli sade, debug'i kolay.

## Kurulum

```bash
pip install simpy pydantic pandas numpy matplotlib streamlit pytest mypy ruff
pip install pandas-stubs   # mypy tip stub'lari
```

Python 3.9+ ile çalışır.

## Çalıştırma

```bash
# Birim testler
pytest

# Statik analiz
ruff check .
mypy

# Tek kontrolcü kosumu (CSV + JSON çıktı)
python -m intersection_sim.run --controller adaptive --seed 42 --duration-hours 4

# 4 kontrolcü × 5 seed karşılaştırma (CSV + 4 PNG)
python -m intersection_sim.scenarios.compare --seeds 5 --duration-hours 4

# BURST senaryosu — ani yön talebi altında 4 kontrolcü
python -m intersection_sim.scenarios.burst --seeds 5 --duration-hours 4

# Etkileşimli Streamlit dashboard (7 sekme)
streamlit run dashboard.py
```

## Etkileşimli Panel — 7 sekme

`streamlit run dashboard.py` ile başlar. 7 sekme:

1. **Senaryo Çalıştır** — sol panelden yöntem, süre ve tekrar seç,
   **Çalıştır**. Ana panelde 8 göstergeli kart (2 satır × 4): ortalama
   bekleme, acil araç beklemesi, saatte geçen araç, acil müdahale sayısı
   + en kötü %5 bekleme, yön adaleti, tahmini CO2, toplam bekleme süresi.
   Altta: kuyruk zaman serisi, yön bazlı bekleme grafiği, araç tipi pastası.

2. **Yöntem Karşılaştırma** — dört yöntemin tablosu ve altta karşılaştırma
   grafikleri (ortalama bekleme, acil araç, saatte geçen araç).

3. **Dağılım ve Çevre** — bekleme süresi dilimleri tablosu, dağılım ve
   kutu grafikleri, çevresel etki (yakıt, CO2) blokları + "kaç km'ye
   eşdeğer" karşılığı.

4. **Saatlik Bekleme Isısı** — yön × saat ortalama bekleme ısı haritası,
   yanında saatlik geçen araç sayısı. Yoğun saatlerde artış görünür.

5. **Ani Talep Senaryosu** — ani yığılma altında dört yöntemin tablosu
   ve grafiği. Sabit yöntemin 67 kat çöküşü, tahmine dayalı yöntemin
   eğilim avantajı.

6. **Trend Katsayısı Denemesi** — tahmine dayalı yöntemin eğilim
   katsayısının (0–1 arası) sonuca etkisini gösteren deneme grafikleri.

7. **Kavşak Görseli** — kavşağın yukarıdan görünümü. Kaydırma çubuğuyla
   koşumun herhangi bir anındaki durum (yeşil yön + her yöndeki kuyruk).

## KPI tanimlari

| KPI | Anlam |
|---|---|
| `mean_wait_time_s` | Variştan gecise baslayana kadar gecen süre (sn) |
| `wait_percentiles_s["p95"]` | En kötü %5'lik dilimin bekleme süresi |
| `mean_wait_by_type["emergency"]` | Sadece acil araçlar için ortalama bekleme |
| `throughput_per_hour` | Saatte kavsagi gecen araç sayısı |
| `full_cycle_count` | 4 yeşil faz = 1 tam çevrim sayaci |
| `preemption_count` | Acil araç preempt'i kac kez tetiklendi |
| `mean_queue_length` | Snapshot ortalaması (10 sn araliklarla) |
| `fairness_index` | Jain's index — yönler arası eşit dağılım (1.0 mükemmel) |
| `co2_grams_proxy` | Idle motor CO2 emisyon proxy (gram) |
| `fuel_liters_proxy` | Idle motor yakıt tahmini (litre) |
| `total_idle_seconds` | Tüm araçların kumulatif bekleme süresi |
| `hourly_throughput[h]` | Saat h'de geçen araç sayısı |
| `hourly_mean_wait_by_direction_s[d][h]` | Saat h, yön d ortalama bekleme |

## 4 Kontrolcü Karşılaştırma (5 seed × 4 saat)

| Kontrolcü | Ort. | **p95** | Acil | Throughput | **Fairness** | **CO2 (g)** |
|---|---:|---:|---:|---:|---:|---:|
| Sabit Zamanlı | 43.72 sn | 101.52 sn | 40.43 sn | 85.2/sa | 0.996 | 5737 |
| Adaptif | 9.70 sn | 29.24 sn | 7.20 sn | 85.2/sa | 0.852 | 1271 |
| **Tahmine Dayalı (hibrit)** | 9.71 sn | **26.51 sn** ↓ | **6.83 sn** ↓ | 85.2/sa | **0.891** ↑ | 1273 |
| Acil Öncelikli | 10.11 sn | 29.91 sn | **5.78 sn** | 85.3/sa | 0.864 | 1328 |

**Kontroller arası farklar:**
- Sabit → Adaptif ortalama bekleme: **%77.8 düşüş** (43.7 → 9.7)
- Sabit → Adaptif CO2: **%78 düşüş** (5737 g → 1271 g)
- Sabit → Acil Öncelikli acil bekleme: **%85.7 düşüş** (40.4 → 5.8)
- Throughput dört kontrolcüyle de **~85/sa** (kontrolcüden bağımsız)
- **Fairness paradoksu:** Sabit yüksek fairness (0.996) ama herkesi
  eşit ölçüde **kötü** bekletiyor — F=1 mutlaka "iyi" değil.
- **Hibrit predictive (4. kontrolcü) — bonus bulgu:** ortalama bekleme
  adaptif ile **eşdeğer** (9.71 vs 9.70, gürültü içinde) ama p95 kötü uç
  **%9.3 düştü** (29.2 → 26.5 sn), acil bekleme **%5 düştü** (7.2 → 6.8),
  **fairness +%4.5** (0.852 → 0.891). Trend bonusu ortalamayı kaybettirmeden
  adalet ve kötü uçta net iyileşme sağlıyor.

Detayli yorumlar: [docs/scenario-findings.md](docs/scenario-findings.md).
Hocanın olası sorulari: [docs/faq.md](docs/faq.md).
Sunum konusma notlari: [docs/sunum-notlari.md](docs/sunum-notlari.md).
Sunum PDF: [docs/presentation.pdf](docs/presentation.pdf) (10 slayt).

## Ekran Goruntuleri

- [01 KPI Ozeti](results/screenshots/01_kpi_summary.png) — 8 KPI kart + grafikler
- [02 Karşılaştırma](results/screenshots/02_comparison.png) — 4 kontrolcü
- [03 Dağılım & Çevresel](results/screenshots/03_distribution.png) — percentile + histogram + CO2
- [04 Saatlik Heatmap](results/screenshots/04_heatmap.png) — yön × saat matrix
- [05 Kavşak Görseli](results/screenshots/05_intersection_view.png) — diyagram

## Test ve QA

- **92 birim/entegrasyon testi** — pytest ile koşar
- **mypy --strict temiz** — 27 src dosya
- **ruff temiz**
- Test gruplari:
  - **Domain** (test_domain.py, test_arrivals.py): yön enum, Vehicle
    hesapları, ArrivalProfile peak/normal, Poisson hızı.
  - **Sabit kontrolcü** (test_fixed_controller.py): yön sırası, 136 sn
    çevrim, sinyal değişim sayaci.
  - **Adaptif** (test_adaptive_switching.py, test_adaptive_better_than_fixed.py):
    longest-queue seçimi, min/max yeşil siniri, %20 düşüş dogrulamasi.
  - **Preemption** (test_preemption_trigger.py, test_emergency_wait_drops.py,
    test_preemption_no_starvation.py): tetikleme dogrulamasi, acil bekleme
    düşüş hipotezi, hiçbir yönün ac kalmaması.
  - **Metric** (test_metrics_collector.py): KPI aritmetiği, sentetik veri.
  - **Senaryolar** (test_scenario_runner_reproducibility.py, test_throughput_similar_across.py,
    test_preemptive_better_than_adaptive_emergency.py): reproducibility,
    throughput tutarliligi, ana hipotezler.
  - **Dashboard** (test_dashboard_helpers.py): saf veri katmani.
  - **Faz Final** (test_metrics_final.py, test_predictive_controller.py):
    percentile correctness (overall + per-type), Jain's fairness sınırları
    [0.25, 1.0], CO2 / yakıt formul testi, saatlik bucket sums, predictive
    trend ekstrapolasyon doğrulaması.
  - **Faz Final v2** (test_burst_scenario.py, test_statistical_significance.py):
    BurstEvent yarı-açık zaman penceresi, multi-burst toplama, fixed
    burst'te ciddi performans çöküşü, Mann-Whitney U ile p95 (p=0.013) ve
    fairness (p=0.0018) anlamlılık testleri.

## Teknik notlar

### Polling pattern tercihi
Kontrolcüler her **0.5 sn**'de kuyruga bakar (`yield env.timeout(0.5)`).
SimPy'nin daha "idiomatic" yöntemleri (Store.get + Interrupt) daha
karmaşık ve hata ayiklamasi zor. Polling: bes kelime ile aciklanabilir
("Her yarım saniyede kuyruga bakar"), debug'i kolay, savunulmasi kolay.

### Adaptif yeşil süresi formulu
```python
green = clamp(queue_length * 3, min_green, max_green)
# default: min=15, max=60
```
Her araç için 3 sn (gecis 2 sn + tepki 1 sn). Min 15 ki çok kısa çevrim
olmasin, max 60 ki bir yön digerleri ac birakmasin.

### Preemption mekanizmasi
1. Yeşil sırasında her tick'te (0.5 sn) kuyrukları tara
2. Başka bir yönde acil araç bekleyen var mi?
3. Varsa mevcut yesili **5 sn'ye** sıkıştır → sarı + buffer → acil yöne
   **15 sn sabit yeşil**
4. Sonra normal adaptif moda don

### Tahmine Dayalı (Predictive) controller — hibrit final genişletmesi
Adaptifin trend-aware varyantı. **Saf trend** mantığı (eski tasarım)
adaptive'i her seed'de geride bırakıyordu (16 parametre kombinasyonu
sweep ile doğrulandı) çünkü anlık kuyruğu görmezden geliyordu. Doğru
çözüm: **hibrit score**.

Algoritma:
1. Son K=6 snapshot'taki (60 sn) kuyruk uzunlukları okunur
2. Lineer regresyon ile slope hesaplanır; `predicted = current + slope × 30 sn`
3. **Hibrit skor:** `score(d) = current(d) + α × max(0, predicted(d) − current(d))`
   - `α = 0.3` (sweep ile seçildi)
   - Trend yokken score = current → adaptive ile eşdeğer
   - Trend artıyorsa bonus (max(0,...) ile azalan trend cezası yok)
4. En yüksek skora sahip yöne yeşil, süre = `clamp(score × 3, 15, 60)`

Sonuç: ortalama bekleme adaptive ile eşdeğer (9.71 vs 9.70 sn, gürültü
içinde), AMA p95 −%9, acil −%5, fairness +%4.5 — trend bonusu ortalamayı
kaybettirmeden kötü uç ve adaleti iyileştiriyor.

### Çevresel proxy formülü
```python
total_idle = sum(v.wait_time for v in served)   # toplam motor-açık bekleme (sn)
fuel_L     = total_idle * 0.000167               # 0.6 L/saat idle (EPA literatür)
co2_g      = fuel_L * 2310                       # 2.31 kg CO2 / L benzin (EPA)
```
Bu **gerçek ölçüm değil** — kontrolcüler arası göreceli karşılaştırma için
literatür sabitleriyle proxy. "Sabit kontrol 4× CO2 üretir" demek için yeterli.

### Jain's fairness index
```python
F = (Σ x_i)² / (n × Σ x_i²)    # x_i = yön i'nin ortalama beklemesi
```
F=1 → tüm yönler eşit bekliyor (mükemmel adil); F=1/n → tek yön avantajlı.
Sabit kontrolcü F=0.996 (çok adil ama hepsini eşit ölçüde **kötü** bekletir),
adaptif/predictive ~0.85 (performans için biraz adaleti feda eder).

## Proje yapisi

```
intersection-sim/
├── dashboard.py                    # Streamlit entry point
├── pyproject.toml
├── README.md
├── docs/
│   ├── presentation.pdf            # 9 slayt sunum
│   ├── sunum-notlari.md            # Nihal için tam konusma metni
│   ├── faq.md                      # soru + cevap
│   └── scenario-findings.md
├── results/
│   ├── *.csv                       # per-vehicle, snapshots, comparison
│   ├── *.json                      # KPI raporları
│   ├── comparison_*.png            # 4 karşılaştırma grafigi
│   ├── wait_time_distribution.png  # bonus histogram
│   └── screenshots/                # 5 dashboard PNG (Playwright)
├── scripts/
│   ├── capture_screenshots.py      # Playwright driver
│   └── build_presentation_pdf.py   # matplotlib PDF builder
├── src/intersection_sim/
│   ├── domain/                     # Direction, Vehicle, SignalConfig, SimConfig
│   ├── controllers/                # fixed, adaptive, predictive, preemptive
│   ├── simulation/                 # Intersection, arrivals, crossing, runner
│   ├── metrics/                    # MetricsCollector + Report (percentile/fairness/CO2)
│   ├── scenarios/                  # 4 senaryo + runner + compare CLI
│   ├── plots/                      # matplotlib karşılaştırma grafikleri
│   ├── dashboard_helpers.py        # Streamlit-bağımsız veri katmani
│   └── run.py                      # CLI: python -m intersection_sim.run
└── tests/                          # 75 test
```

## Lisans

MIT — okul odevi olarak yazıldı, kisisel kullanimda serbest.
