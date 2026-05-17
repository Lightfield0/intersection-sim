# Intersection Sim — Akilli Kavsak Trafik Isigi Simulasyonu

SimPy ile dort yollu bir kavsagi, **uc farkli trafik isigi kontrolcusu**
ile kosturup karsilastirir: sabit zamanli, adaptif (kuyruk uzunluguna
gore yesil suresi) ve acil oncelikli (ambulans gorulurse mevcut yesili
kapatip acil yone oncelik).

> **Sunum hikayesi**
>
> Sabit kontrolde **ambulans 40 saniye bekliyor**. Adaptif kontrol bunu
> **7 saniyeye** dusurdu. Acil oncelikli kontrol **6 saniyeye** —
> sabit zamanliya gore **yedi kat fark**. Ayni kavsak, uc farkli mantik,
> dogru karari sezgi degil simulasyon verisi gosterdi.

## Cita: Otobus Duragi vs Bu Proje

| Ozellik | Otobus Duragi (referans) | Bu Proje (kavsak) |
|---|---|---|
| Oncelik seviyesi | 2 | 4 yon + acil arac |
| Asama | Tek (kuyruk → otobus) | Cok (kuyruk → sinyal → cikis) |
| Kaynak | 1 otobus | 4 yon sinyali + kontrolcu |
| Mekansal model | Yok | Var (N / S / E / W) |
| Preemption | Yok | Var (acil arac preempt) |
| Kontrol stratejisi | Tek | 3 (sabit / adaptif / preemptive) |
| Senaryo | Tek | 3 kontrolcu × 5 seed |
| Gorselleştirme | Statik | Streamlit dashboard + kavsak diyagrami |

## Ozellikler

- **4 yonlu kavsak modeli** (Kuzey / Guney / Dogu / Bati) ayri kuyruklarla
- **3 kontrolcu** — sabit zamanli (sirayla yesil), adaptif (queue × 3 sn),
  acil oncelikli (preemption + adaptif)
- **Saatlik degisken trafik** (Poisson, 07-09 + 17-19 yogun saatler)
- **Acil arac modeli** (%5 olasilik, ozel KPI)
- **Coklu seed runner** — istatistiksel guven icin
- **Streamlit dashboard** — 3 sekme, etkilesimli kavsak gorseli
- **55 birim test** — mypy strict, ruff temiz

## Mimari

```
                    +----- Kuzey kuyrugu -----+
                    |                          |
                    |   simpy.Store (FIFO)     |
                    |                          |
                    +----- (4 yon icin ayri) --+
                              |
                              v
                     +---- KAVSAK ----+
                     | 4 sinyal      |       Sabit / Adaptif /
                     | (LightState)  | <---- Acil Oncelikli kontrolcu
                     +---- 1 cevrim -+        (controllers/*.py)
                              |
                              v
                     +---- Cikis ----+
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

Python 3.9+ ile calisir.

## Calistirma

```bash
# Birim testler
pytest

# Statik analiz
ruff check .
mypy

# Tek kontrolcu kosumu (CSV + JSON cikti)
python -m intersection_sim.run --controller adaptive --seed 42 --duration-hours 4

# 3 kontrolcu × 5 seed karsilastirma (CSV + 4 PNG)
python -m intersection_sim.scenarios.compare --seeds 5 --duration-hours 4

# Etkilesimli Streamlit dashboard
streamlit run dashboard.py
```

## Dashboard — 3 sekme

`streamlit run dashboard.py` ile baslar. 3 sekme:

1. **📊 Senaryo Calistir** — sidebar'dan kontrolcu/sure/seed sec, **Calistir**.
   Ana panelde 4 KPI metric karti (ortalama bekleme, acil bekleme,
   throughput, preemption sayisi), kuyruk uzunlugu zaman serisi, yon
   bazli ortalama bekleme bar chart, arac tipi pie chart.

2. **📈 3 Kontrolcu Karsilastirma** — `results/comparison.csv` tablosu,
   3 Faz 4 PNG'si (avg_wait, **emergency_wait — altin grafigimiz**,
   throughput), `docs/scenario-findings.md` markdown.

3. **🚦 Kavsak Gorseli** — yukaridan goren statik matplotlib diyagrami.
   Snapshot zaman slider'i ile zamanin herhangi bir aninda kavsagin
   durumu (yesil yon + her yondeki kuyruk uzunlugu).

## KPI tanimlari

| KPI | Anlam |
|---|---|
| `mean_wait_time_s` | Variştan gecise baslayana kadar gecen sure (sn) |
| `mean_wait_by_type["emergency"]` | Sadece acil araclar icin ortalama bekleme |
| `throughput_per_hour` | Saatte kavsagi gecen arac sayisi |
| `full_cycle_count` | 4 yesil faz = 1 tam cevrim sayaci |
| `preemption_count` | Acil arac preempt'i kac kez tetiklendi |
| `mean_queue_length` | Snapshot ortalamasi (10 sn araliklarla) |

## 3 Kontrolcu Karsilastirma (5 seed × 4 saat)

| Kontrolcu | Ort. bekleme | Normal | **Acil** | Throughput | Preempt |
|---|---:|---:|---:|---:|---:|
| Sabit Zamanli | 43.7 sn | 43.9 sn | 40.4 sn | 85.2/sa | 0 |
| Adaptif | 9.7 sn | 9.8 sn | 7.2 sn | 85.2/sa | 0 |
| **Acil Oncelikli** | 10.1 sn | 10.3 sn | **5.8 sn** | 85.3/sa | 7.0 |

**Kontroller arası farklar:**
- Sabit → Adaptif ortalama bekleme: **%77.8 dusus** (43.7 → 9.7)
- Adaptif → Acil Oncelikli acil bekleme: **%19.7 dusus** (7.2 → 5.8)
- Sabit → Acil Oncelikli acil bekleme: **%85.7 dusus** (40.4 → 5.8)
- Throughput uc kontrolcuyle de **~85/sa** (kontrolcuden bagimsiz)

Detayli yorumlar: [docs/scenario-findings.md](docs/scenario-findings.md).
Hocanin olasi sorulari: [docs/faq.md](docs/faq.md).
Sunum konusma notlari: [docs/sunum-notlari.md](docs/sunum-notlari.md).
Sunum PDF: [docs/presentation.pdf](docs/presentation.pdf) (10 slayt).

## Ekran Goruntuleri

- [01 KPI Ozeti](results/screenshots/01_kpi_summary.png) — Adaptif senaryo
- [02 Karsilastirma](results/screenshots/02_comparison.png) — 3 kontrolcu
- [03 Kavsak Gorseli](results/screenshots/03_intersection_view.png) — diyagram
- [04 Acil Bekleme Grafigi](results/screenshots/04_emergency_grafik.png) — altin

## Test ve QA

- **55 birim/entegrasyon testi** — pytest ile kosar
- **mypy --strict temiz** — 25 src dosya
- **ruff temiz**
- Test gruplari:
  - **Domain** (test_domain.py, test_arrivals.py): yon enum, Vehicle
    hesaplari, ArrivalProfile peak/normal, Poisson hizi.
  - **Sabit kontrolcu** (test_fixed_controller.py): yon sirasi, 136 sn
    cevrim, sinyal degisim sayaci.
  - **Adaptif** (test_adaptive_switching.py, test_adaptive_better_than_fixed.py):
    longest-queue secimi, min/max yesil siniri, %20 dusus dogrulamasi.
  - **Preemption** (test_preemption_trigger.py, test_emergency_wait_drops.py,
    test_preemption_no_starvation.py): tetikleme dogrulamasi, acil bekleme
    dusus hipotezi, hicbir yonun ac kalmamasi.
  - **Metric** (test_metrics_collector.py): KPI aritmetiği, sentetik veri.
  - **Senaryolar** (test_scenario_runner_reproducibility.py, test_throughput_similar_across.py,
    test_preemptive_better_than_adaptive_emergency.py): reproducibility,
    throughput tutarliligi, ana hipotezler.
  - **Dashboard** (test_dashboard_helpers.py): saf veri katmani.

## Teknik notlar

### Polling pattern tercihi
Kontrolculer her **0.5 sn**'de kuyruga bakar (`yield env.timeout(0.5)`).
SimPy'nin daha "idiomatic" yontemleri (Store.get + Interrupt) daha
karmaşık ve hata ayiklamasi zor. Polling: bes kelime ile aciklanabilir
("Her yarim saniyede kuyruga bakar"), debug'i kolay, savunulmasi kolay.

### Adaptif yesil suresi formulu
```python
green = clamp(queue_length * 3, min_green, max_green)
# default: min=15, max=60
```
Her arac icin 3 sn (gecis 2 sn + tepki 1 sn). Min 15 ki cok kisa cevrim
olmasin, max 60 ki bir yon digerleri ac birakmasin.

### Preemption mekanizmasi
1. Yesil sirasinda her tick'te (0.5 sn) kuyrukları tara
2. Baska bir yonde acil arac bekleyen var mi?
3. Varsa mevcut yesili **5 sn'ye** sikistir → sari + buffer → acil yone
   **15 sn sabit yesil**
4. Sonra normal adaptif moda don

## Proje yapisi

```
intersection-sim/
├── dashboard.py                    # Streamlit entry point
├── pyproject.toml
├── README.md
├── docs/
│   ├── presentation.pdf            # 10 slayt sunum
│   ├── sunum-notlari.md            # Nihal icin tam konusma metni
│   ├── faq.md                      # 15 soru + cevap
│   └── scenario-findings.md
├── results/
│   ├── *.csv                       # per-vehicle, snapshots, comparison
│   ├── *.json                      # KPI raporlari
│   ├── comparison_*.png            # 3 karsilastirma grafigi
│   ├── wait_time_distribution.png  # bonus histogram
│   └── screenshots/                # 4 dashboard PNG (Playwright)
├── scripts/
│   ├── capture_screenshots.py      # Playwright driver
│   └── build_presentation_pdf.py   # matplotlib PDF builder
├── src/intersection_sim/
│   ├── domain/                     # Direction, Vehicle, SignalConfig, SimConfig
│   ├── controllers/                # fixed, adaptive, preemptive
│   ├── simulation/                 # Intersection, arrivals, crossing, runner
│   ├── metrics/                    # MetricsCollector + Report
│   ├── scenarios/                  # 3 senaryo + runner + compare CLI
│   ├── plots/                      # matplotlib karsilastirma grafikleri
│   ├── dashboard_helpers.py        # Streamlit-bagimsiz veri katmani
│   └── run.py                      # CLI: python -m intersection_sim.run
└── tests/                          # 55 test
```

## Lisans

MIT — okul odevi olarak yazildi, kisisel kullanimda serbest.
