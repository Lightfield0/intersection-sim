"""Olay-damgalarini toplayan ve KPI'a ceviren modul.

Uc temel sinif var:

* ``MetricsSnapshot`` — belirli bir anin gozlemi (kuyruk uzunluklari +
  aktif yesil yon). Snapshot loop her 10 sn'de bir cagrilir.
* ``MetricsCollector`` — kosum suresince olay damgalarini biriktirir
  (gecmis araclar, snapshot listesi, yesil faz sayisi, sinyal degisim
  sayisi). Tum durum saf python — SimPy degil.
* ``MetricsReport`` — kosum bitince Collector'dan turetilen ozet
  KPI nesnesi. Sunumda kullanilan butun sayilar buradan okunur.

Triage projesindeki ``KPIReport`` pattern'inden farkli isim ve farkli
alan adlari kullanildi: ``mean_wait_time_s``, ``vehicles_served`` gibi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from intersection_sim.domain.direction import Direction
from intersection_sim.domain.vehicle import Vehicle, VehicleType

# Adaptif kontrolcunun bir cevrim olarak saydigi yesil faz sayisi.
# Sabit-zamanli kontrolcu de ayni mantikla 4 yesil = 1 cycle yapar.
GREEN_PHASES_PER_CYCLE = 4


# Snapshot orneklem araligi (saniye). Spec gerekliligi: her 10 sn.
SNAPSHOT_INTERVAL_S: float = 10.0


# ---------- Faz Final: Genisletilmis metrik sabitleri ----------------------
# Idle (motor calisirken bekleme) yakit tuketimi — gasoline passenger car
# literatur ortalamasi: ~0.6 L/saat = 0.000167 L/s (EPA, CARB).
IDLE_FUEL_RATE_L_PER_S: float = 0.6 / 3600.0

# Benzin yanmasindan acigi cikan CO2 — EPA 2.31 kg / L gasoline.
CO2_GRAMS_PER_LITER_GASOLINE: float = 2310.0

# Rapor edilen percentile basamaklari. p50 medyan, p95 "kotu uc".
WAIT_PERCENTILES: tuple[int, ...] = (50, 75, 90, 95, 99)

# Saatlik aggregation icin bucket buyuklugu (saniye).
HOURLY_BUCKET_S: float = 3600.0


@dataclass
class MetricsSnapshot:
    """Belirli bir simulasyon aninin durum fotografi.

    - sim_time_s: cekildigi sim-saati (saniye).
    - queue_lengths: her yonun o andaki bekleyen arac sayisi.
    - active_green: o anda yesil olan yon (yoksa None — buffer / sari).
    """

    sim_time_s: float
    queue_lengths: dict[Direction, int]
    active_green: Direction | None

    @property
    def total_queue(self) -> int:
        """Tum yonlerdeki bekleyen araclarin toplami."""
        return sum(self.queue_lengths.values())


@dataclass
class MetricsCollector:
    """Olay damgalarini biriktiren ana sayac.

    Intersection nesnesi bunu kendi attribute'u olarak tasir; sinyal
    degisimleri ve gecmis araclar bu collector'a yazilir.
    """

    vehicles_served: list[Vehicle] = field(default_factory=list)
    snapshots: list[MetricsSnapshot] = field(default_factory=list)
    green_phase_count: int = 0
    signal_change_count: int = 0
    # Acil arac preemption tetiklenme sayisi (preemptive kontrolcu kullanir).
    # Sabit ve adaptif kontrolculerde her zaman 0 kalir.
    preemption_count: int = 0

    # ---- olay kayit metotlari --------------------------------------------

    def record_vehicle_served(self, vehicle: Vehicle) -> None:
        """Bir arac kavsagi gecip cikti — listeye ekle."""
        self.vehicles_served.append(vehicle)

    def record_snapshot(self, snap: MetricsSnapshot) -> None:
        """Periyodik kuyruk gozlemini ekle."""
        self.snapshots.append(snap)

    def record_green_phase(self) -> None:
        """Bir yone yesil verildi — cycle sayacinda kullanilir."""
        self.green_phase_count += 1

    def record_signal_change(self) -> None:
        """Bir yonun renk degisimi olustu (RED->GREEN gibi). Sayac +1."""
        self.signal_change_count += 1

    def record_preemption(self) -> None:
        """Acil arac tetigi devreye girdi — mevcut yesil kisaltildi."""
        self.preemption_count += 1

    # ---- turetilmis ozellikler -------------------------------------------

    @property
    def full_cycle_count(self) -> int:
        """4 yesil faz = 1 tam cevrim (spec'in sunumda kullandigi metrik).

        Sabit-zamanli kontrolcu bunu 4 yon sirasiyla yapar; adaptif
        kontrolcu sirayi atlayabilir ama yine de 4 yesil faz 1 cevrim
        olarak sayilir. Boylece iki kontrolcuyu ayni metrik uzerinde
        karsilastirabiliyoruz.
        """
        return self.green_phase_count // GREEN_PHASES_PER_CYCLE

    # ---- DataFrame export helper'lari ------------------------------------

    def vehicles_dataframe(self) -> pd.DataFrame:
        """Her arac bir satir; CSV ciktisi icin kullanilir."""
        rows: list[dict[str, object]] = []
        for v in self.vehicles_served:
            rows.append(
                {
                    "vehicle_id": v.vehicle_id,
                    "direction": v.direction.value,
                    "vehicle_type": v.vehicle_type.value,
                    "arrival_time_s": v.arrival_time,
                    "cross_start_time_s": v.cross_start_time,
                    "cross_end_time_s": v.cross_end_time,
                    "wait_time_s": v.wait_time,
                    "total_time_s": v.total_time_in_system,
                }
            )
        return pd.DataFrame(rows)

    def snapshots_dataframe(self) -> pd.DataFrame:
        """Her snapshot bir satir; zaman serisi grafikleri icin."""
        rows: list[dict[str, object]] = []
        for s in self.snapshots:
            row: dict[str, object] = {
                "sim_time_s": s.sim_time_s,
                "active_green": s.active_green.value if s.active_green else None,
                "total_queue": s.total_queue,
            }
            for d in Direction:
                row[f"queue_{d.value}"] = s.queue_lengths.get(d, 0)
            rows.append(row)
        return pd.DataFrame(rows)

    def build_report(self, horizon_seconds: float) -> MetricsReport:
        """Toplanan veriden ozet rapor cikar."""
        return MetricsReport.from_collector(self, horizon_seconds)


@dataclass
class MetricsReport:
    """Bir kosumun ozet KPI'lari.

    Sunumda gosterilen tum sayilar bu nesneden okunur. Kontrolcuyu
    karsilastirmak: her kontrolcu icin bir rapor, sayilari yan yana
    koy.
    """

    horizon_seconds: float
    vehicles_served: int
    mean_wait_time_s: float | None
    max_wait_time_s: float | None
    mean_wait_by_direction_s: dict[str, float | None]
    mean_wait_by_type_s: dict[str, float | None]
    throughput_per_hour: float
    mean_queue_length: float
    max_queue_length: int
    full_cycle_count: int
    signal_change_count: int
    green_phase_count: int
    preemption_count: int

    # ---- Faz Final: percentile + extremum --------------------------------
    # Bekleme suresinin p50/p75/p90/p95/p99 dilimleri. "Ortalama 10 sn ama
    # p95 = 45 sn" yorumu kuyruktaki kotu uctaki kisiyi gosterir.
    wait_percentiles_s: dict[str, float | None] = field(default_factory=dict)
    wait_percentiles_normal_s: dict[str, float | None] = field(default_factory=dict)
    wait_percentiles_emergency_s: dict[str, float | None] = field(default_factory=dict)
    max_wait_by_direction_s: dict[str, float | None] = field(default_factory=dict)

    # ---- Faz Final: cevresel etki (idle proxy) ---------------------------
    # Toplam motor-acik bekleme suresi (sn). idle yakit hesabinin temeli.
    total_idle_seconds: float = 0.0
    # Tahmini ek yakit (L). gercek olcum degil; literatur sabitiyle proxy.
    fuel_liters_proxy: float = 0.0
    # Tahmini CO2 (gram). yakit_L * 2310 g/L formulu.
    co2_grams_proxy: float = 0.0

    # ---- Faz Final: fairness (Jain's index) ------------------------------
    # Yon bazli ortalama beklemenin esitligini olcer. F=1 mukemmel adil,
    # F=1/n tek yon avantajli. Beklemenin dusuk olmasi degil, "yonler
    # arasinda esit dagilim" olcusu.
    fairness_index: float | None = None

    # ---- Faz Final: saatlik aggregation ----------------------------------
    # Her saatlik bucket icin (0..H-1) ozet metrikler.
    hourly_throughput: list[float] = field(default_factory=list)
    hourly_mean_wait_s: list[float | None] = field(default_factory=list)
    # Yon -> saatlik ortalama bekleme listesi.
    hourly_mean_wait_by_direction_s: dict[str, list[float | None]] = field(
        default_factory=dict,
    )

    # ---- olusturucu ------------------------------------------------------

    @classmethod
    def from_collector(
        cls, collector: MetricsCollector, horizon_seconds: float,
    ) -> MetricsReport:
        served = collector.vehicles_served
        waits = [v.wait_time for v in served if v.wait_time is not None]

        # Yon bazli ortalama bekleme + maksimum bekleme
        by_dir: dict[str, float | None] = {}
        max_by_dir: dict[str, float | None] = {}
        for d in Direction:
            d_waits = [
                v.wait_time for v in served
                if v.direction is d and v.wait_time is not None
            ]
            by_dir[d.value] = (sum(d_waits) / len(d_waits)) if d_waits else None
            max_by_dir[d.value] = max(d_waits) if d_waits else None

        # Tip bazli (normal vs emergency)
        by_type: dict[str, float | None] = {}
        type_waits: dict[VehicleType, list[float]] = {}
        for t in VehicleType:
            t_waits = [
                v.wait_time for v in served
                if v.vehicle_type is t and v.wait_time is not None
            ]
            type_waits[t] = t_waits
            by_type[t.value] = (sum(t_waits) / len(t_waits)) if t_waits else None

        # Kuyruk istatistikleri (snapshot'lardan)
        total_queues = [s.total_queue for s in collector.snapshots]
        mean_q = (sum(total_queues) / len(total_queues)) if total_queues else 0.0
        max_q = max(total_queues) if total_queues else 0

        throughput = (
            len(served) / (horizon_seconds / 3600.0)
            if horizon_seconds > 0 else 0.0
        )

        # ---- Faz Final: percentile (overall + per-type) ------------------
        wait_pct = _percentile_dict(waits)
        wait_pct_normal = _percentile_dict(type_waits.get(VehicleType.NORMAL, []))
        wait_pct_em = _percentile_dict(type_waits.get(VehicleType.EMERGENCY, []))

        # ---- Faz Final: cevresel proxy -----------------------------------
        # Idle = aracin yesili bekledigi sure (motor calisiyor).
        total_idle = float(sum(waits))
        fuel_l = total_idle * IDLE_FUEL_RATE_L_PER_S
        co2_g = fuel_l * CO2_GRAMS_PER_LITER_GASOLINE

        # ---- Faz Final: Jain's fairness index ----------------------------
        fairness = _jains_fairness([by_dir[d.value] for d in Direction])

        # ---- Faz Final: saatlik bucket'lar -------------------------------
        n_hours = max(1, int(np.ceil(horizon_seconds / HOURLY_BUCKET_S)))
        hourly_thru, hourly_wait, hourly_wait_dir = _hourly_aggregates(
            served, n_hours,
        )

        return cls(
            horizon_seconds=horizon_seconds,
            vehicles_served=len(served),
            mean_wait_time_s=(sum(waits) / len(waits)) if waits else None,
            max_wait_time_s=max(waits) if waits else None,
            mean_wait_by_direction_s=by_dir,
            mean_wait_by_type_s=by_type,
            throughput_per_hour=throughput,
            mean_queue_length=mean_q,
            max_queue_length=int(max_q),
            full_cycle_count=collector.full_cycle_count,
            signal_change_count=collector.signal_change_count,
            green_phase_count=collector.green_phase_count,
            preemption_count=collector.preemption_count,
            wait_percentiles_s=wait_pct,
            wait_percentiles_normal_s=wait_pct_normal,
            wait_percentiles_emergency_s=wait_pct_em,
            max_wait_by_direction_s=max_by_dir,
            total_idle_seconds=total_idle,
            fuel_liters_proxy=fuel_l,
            co2_grams_proxy=co2_g,
            fairness_index=fairness,
            hourly_throughput=hourly_thru,
            hourly_mean_wait_s=hourly_wait,
            hourly_mean_wait_by_direction_s=hourly_wait_dir,
        )

    # ---- JSON / CSV export -----------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "horizon_seconds": self.horizon_seconds,
            "vehicles_served": self.vehicles_served,
            "throughput_per_hour": _round_opt(self.throughput_per_hour, 2),
            "mean_wait_time_s": _round_opt(self.mean_wait_time_s, 2),
            "max_wait_time_s": _round_opt(self.max_wait_time_s, 2),
            "mean_queue_length": _round_opt(self.mean_queue_length, 2),
            "max_queue_length": self.max_queue_length,
            "full_cycle_count": self.full_cycle_count,
            "green_phase_count": self.green_phase_count,
            "signal_change_count": self.signal_change_count,
            "preemption_count": self.preemption_count,
            "mean_wait_by_direction_s": {
                k: _round_opt(v, 2) for k, v in self.mean_wait_by_direction_s.items()
            },
            "mean_wait_by_type_s": {
                k: _round_opt(v, 2) for k, v in self.mean_wait_by_type_s.items()
            },
            # ---- Faz Final genisletmesi --------------------------------------
            "wait_percentiles_s": {
                k: _round_opt(v, 2) for k, v in self.wait_percentiles_s.items()
            },
            "wait_percentiles_normal_s": {
                k: _round_opt(v, 2)
                for k, v in self.wait_percentiles_normal_s.items()
            },
            "wait_percentiles_emergency_s": {
                k: _round_opt(v, 2)
                for k, v in self.wait_percentiles_emergency_s.items()
            },
            "max_wait_by_direction_s": {
                k: _round_opt(v, 2) for k, v in self.max_wait_by_direction_s.items()
            },
            "total_idle_seconds": _round_opt(self.total_idle_seconds, 1),
            "fuel_liters_proxy": _round_opt(self.fuel_liters_proxy, 4),
            "co2_grams_proxy": _round_opt(self.co2_grams_proxy, 2),
            "fairness_index": _round_opt(self.fairness_index, 4),
            "hourly_throughput": [_round_opt(v, 2) for v in self.hourly_throughput],
            "hourly_mean_wait_s": [
                _round_opt(v, 2) for v in self.hourly_mean_wait_s
            ],
            "hourly_mean_wait_by_direction_s": {
                k: [_round_opt(v, 2) for v in lst]
                for k, lst in self.hourly_mean_wait_by_direction_s.items()
            },
        }

    def write_json(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

    def pretty_print(self) -> str:
        lines = [
            f" sure (sn)                : {self.horizon_seconds:.0f}",
            f" gecen arac sayisi         : {self.vehicles_served}",
            f" throughput (arac / saat)  : {self.throughput_per_hour:.2f}",
            f" ortalama bekleme (sn)     : {_fmt(self.mean_wait_time_s)}",
            f" maksimum bekleme (sn)     : {_fmt(self.max_wait_time_s)}",
            f" ortalama kuyruk uzunlugu  : {self.mean_queue_length:.2f}",
            f" maksimum kuyruk uzunlugu  : {self.max_queue_length}",
            f" tam cevrim sayisi         : {self.full_cycle_count}",
            f" yesil faz sayisi          : {self.green_phase_count}",
            f" preemption tetik sayisi   : {self.preemption_count}",
            " yon bazli ortalama bekleme:",
        ]
        for d, w in self.mean_wait_by_direction_s.items():
            lines.append(f"   {d} : {_fmt(w)} sn")
        lines.append(" tip bazli ortalama bekleme:")
        for t, w in self.mean_wait_by_type_s.items():
            lines.append(f"   {t:10s} : {_fmt(w)} sn")
        # ---- Faz Final genisletmesi ------------------------------------
        lines.append(" bekleme percentile'lari:")
        for k in sorted(self.wait_percentiles_s.keys()):
            lines.append(f"   {k} : {_fmt(self.wait_percentiles_s[k])} sn")
        lines.append(f" fairness index (Jain's)   : {_fmt(self.fairness_index, 4)}")
        lines.append(f" toplam idle (sn)          : {self.total_idle_seconds:.1f}")
        lines.append(f" tahmini yakit (L)         : {self.fuel_liters_proxy:.3f}")
        lines.append(f" tahmini CO2 (g)           : {self.co2_grams_proxy:.1f}")
        lines.append(" saatlik throughput (arac/saat):")
        for i, v in enumerate(self.hourly_throughput):
            lines.append(f"   saat {i} : {v:.2f}")
        return "\n".join(lines)


# ---------- ufak yardimcilar ------------------------------------------------


def _round_opt(v: float | None, digits: int = 2) -> float | None:
    return None if v is None else round(float(v), digits)


def _fmt(v: float | None, digits: int = 2) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


# ---------- Faz Final: percentile / fairness / hourly yardimcilari --------


def _percentile_dict(waits: list[float]) -> dict[str, float | None]:
    """np.percentile ile p50..p99 dilimlerini hesapla.

    Bos liste icin tum degerler None doner; veri olduktan sonra
    pct'ler 'p50', 'p75' gibi anahtarlarla doner. Sunum/JSON icin sade.
    """
    if not waits:
        return {f"p{p}": None for p in WAIT_PERCENTILES}
    arr = np.asarray(waits, dtype=float)
    return {f"p{p}": float(np.percentile(arr, p)) for p in WAIT_PERCENTILES}


def _jains_fairness(values: list[float | None]) -> float | None:
    """Jain's fairness index — F = (Sum x)^2 / (n * Sum x^2).

    Beklemenin yonler arasinda ne kadar esit dagildigini olcer.
    F=1 mukemmel adil (tum yonler ayni bekliyor). F=1/n tek yon
    avantajli. Bos veya tek-ogeli liste icin None doner.

    Beklemenin DUSUK olmasi degil, "yonler arasinda esit dagilim"
    olcusu — bu yuzden 'adaptif beklemeyi dusurur AMA fair midir?'
    sorusunu cevaplar.
    """
    xs = [v for v in values if v is not None and v >= 0.0]
    if len(xs) < 2:
        return None
    s = sum(xs)
    if s == 0.0:
        # Tum yonler ayni 0 ise mukemmel adil
        return 1.0
    sq = sum(v * v for v in xs)
    return (s * s) / (len(xs) * sq)


def _hourly_aggregates(
    served: list[Vehicle],
    n_hours: int,
) -> tuple[list[float], list[float | None], dict[str, list[float | None]]]:
    """Aracin variş zamanina gore saatlik bucket'a yerlestir.

    Doner: (hourly_throughput, hourly_mean_wait, hourly_mean_wait_by_dir).
    - throughput[i] = saat i'de varan arac sayisi (arac/saat -- 1 saat
      bucket oldugu icin sayi == hiz).
    - mean_wait[i] = saat i'de varan araclarin ortalama beklemesi.
    - by_dir[d.value][i] = saat i + yon d ortalama beklemesi.
    """
    buckets: list[list[Vehicle]] = [[] for _ in range(n_hours)]
    for v in served:
        h = int(v.arrival_time // HOURLY_BUCKET_S)
        if 0 <= h < n_hours:
            buckets[h].append(v)

    thru: list[float] = [float(len(b)) for b in buckets]

    def _mean_wait(vs: list[Vehicle]) -> float | None:
        ws = [v.wait_time for v in vs if v.wait_time is not None]
        return (sum(ws) / len(ws)) if ws else None

    mean_w: list[float | None] = [_mean_wait(b) for b in buckets]

    by_dir: dict[str, list[float | None]] = {}
    for d in Direction:
        per_hour: list[float | None] = []
        for b in buckets:
            d_vs = [v for v in b if v.direction is d]
            per_hour.append(_mean_wait(d_vs))
        by_dir[d.value] = per_hour

    return thru, mean_w, by_dir
