"""Coklu seed senaryo orkestrasyon ve toplulastirma.

Bir senaryoyu N seed ile kosar, raporları toplar ve ortalama / std
hesaplar. ``compare_controllers(seeds, duration_hours)`` ucunu birden
ayni cagrida kosturup karsilastirilabilir bir liste dondurur.

Triage projesinde ScenarioResult bir dataclass'ti; burada da ayni
yaklasimi tutuyoruz ama alan isimleri farkli (``mean_wait_time_s_mean``
yerine triage'da ``throughput_mean`` vardi).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean, pstdev

import pandas as pd

from intersection_sim.metrics.metrics_collector import MetricsReport
from intersection_sim.scenarios.definitions import ALL_SCENARIOS, ScenarioDef
from intersection_sim.simulation.runner import run_with_controller


@dataclass
class ScenarioRun:
    """Tek senaryo, tek seed: bir koşumun ham raporu."""

    name: str
    seed: int
    report: MetricsReport


@dataclass
class ScenarioResult:
    """Bir senaryonun N seed boyunca ortalaması + std degerleri.

    Sunum tablosu için to_row() metodu duzlestirilmis satir dondurur.
    """

    scenario: ScenarioDef
    runs: list[ScenarioRun]

    # ---- temel özet özellikleri ------------------------------------------

    @property
    def n_seeds(self) -> int:
        return len(self.runs)

    @property
    def mean_wait_time_s_mean(self) -> float:
        return float(mean(_collect_mean_wait(self.runs)))

    @property
    def mean_wait_time_s_std(self) -> float:
        return _safe_pstdev(_collect_mean_wait(self.runs))

    @property
    def emergency_wait_s_mean(self) -> float:
        return float(mean(_collect_type_wait(self.runs, "emergency")))

    @property
    def emergency_wait_s_std(self) -> float:
        return _safe_pstdev(_collect_type_wait(self.runs, "emergency"))

    @property
    def normal_wait_s_mean(self) -> float:
        return float(mean(_collect_type_wait(self.runs, "normal")))

    @property
    def normal_wait_s_std(self) -> float:
        return _safe_pstdev(_collect_type_wait(self.runs, "normal"))

    @property
    def throughput_per_hour_mean(self) -> float:
        return float(mean(r.report.throughput_per_hour for r in self.runs))

    @property
    def throughput_per_hour_std(self) -> float:
        return _safe_pstdev([r.report.throughput_per_hour for r in self.runs])

    @property
    def max_wait_s_mean(self) -> float:
        vals = [r.report.max_wait_time_s for r in self.runs if r.report.max_wait_time_s is not None]
        return float(mean(vals)) if vals else 0.0

    @property
    def preemption_count_mean(self) -> float:
        return float(mean(r.report.preemption_count for r in self.runs))

    @property
    def mean_queue_length_mean(self) -> float:
        return float(mean(r.report.mean_queue_length for r in self.runs))

    # ---- Faz Final genisletmesi ------------------------------------------

    @property
    def p95_wait_s_mean(self) -> float:
        vals = [
            r.report.wait_percentiles_s.get("p95") for r in self.runs
        ]
        valid = [v for v in vals if v is not None]
        return float(mean(valid)) if valid else 0.0

    @property
    def p95_emergency_wait_s_mean(self) -> float:
        vals = [
            r.report.wait_percentiles_emergency_s.get("p95") for r in self.runs
        ]
        valid = [v for v in vals if v is not None]
        return float(mean(valid)) if valid else 0.0

    @property
    def fairness_index_mean(self) -> float:
        vals = [r.report.fairness_index for r in self.runs]
        valid = [v for v in vals if v is not None]
        return float(mean(valid)) if valid else 0.0

    @property
    def co2_grams_proxy_mean(self) -> float:
        return float(mean(r.report.co2_grams_proxy for r in self.runs))

    @property
    def total_idle_seconds_mean(self) -> float:
        return float(mean(r.report.total_idle_seconds for r in self.runs))

    def to_row(self) -> dict[str, object]:
        """Duz bir sozluk — DataFrame'e ekleyip CSV'ye yazmak için."""
        return {
            "controller": self.scenario.name,
            "display_name_tr": self.scenario.display_name_tr,
            "n_seeds": self.n_seeds,
            "mean_wait_s_mean": round(self.mean_wait_time_s_mean, 2),
            "mean_wait_s_std": round(self.mean_wait_time_s_std, 2),
            "normal_wait_s_mean": round(self.normal_wait_s_mean, 2),
            "emergency_wait_s_mean": round(self.emergency_wait_s_mean, 2),
            "max_wait_s_mean": round(self.max_wait_s_mean, 2),
            "throughput_per_hour_mean": round(self.throughput_per_hour_mean, 2),
            "throughput_per_hour_std": round(self.throughput_per_hour_std, 2),
            "mean_queue_length_mean": round(self.mean_queue_length_mean, 2),
            "preemption_count_mean": round(self.preemption_count_mean, 2),
            # ---- Faz Final genisletmesi ----------------------------------
            "p95_wait_s_mean": round(self.p95_wait_s_mean, 2),
            "p95_emergency_wait_s_mean": round(self.p95_emergency_wait_s_mean, 2),
            "fairness_index_mean": round(self.fairness_index_mean, 4),
            "co2_grams_proxy_mean": round(self.co2_grams_proxy_mean, 2),
            "total_idle_seconds_mean": round(self.total_idle_seconds_mean, 1),
        }


# ---- yardimcilar -----------------------------------------------------------


def _collect_mean_wait(runs: list[ScenarioRun]) -> list[float]:
    """Her run'in ortalama bekleme suresini liste olarak topla."""
    return [r.report.mean_wait_time_s for r in runs if r.report.mean_wait_time_s is not None]


def _collect_type_wait(runs: list[ScenarioRun], type_key: str) -> list[float]:
    """Belirli tipin (normal / emergency) ortalama beklemesini topla."""
    out: list[float] = []
    for r in runs:
        v = r.report.mean_wait_by_type_s.get(type_key)
        if v is not None:
            out.append(v)
    return out


def _safe_pstdev(values: list[float]) -> float:
    """Tek elemanli listede pstdev 0 doner (NaN yerine)."""
    return float(pstdev(values)) if len(values) > 1 else 0.0


# ---- yuruyutucu fonksiyonlar -----------------------------------------------


def run_scenario(
    scenario: ScenarioDef,
    seeds: Iterable[int],
    duration_hours: float,
) -> ScenarioResult:
    """Bir senaryoyu N seed ile kosar, ScenarioResult dondurur."""
    seeds_list = list(seeds)
    runs: list[ScenarioRun] = []
    for s in seeds_list:
        config = scenario.build_config(seed=s, duration_hours=duration_hours)
        intersection = run_with_controller(config, scenario.controller)
        report = intersection.metrics.build_report(config.horizon_seconds)
        runs.append(ScenarioRun(name=scenario.name, seed=s, report=report))
    return ScenarioResult(scenario=scenario, runs=runs)


def compare_controllers(
    seeds: Iterable[int],
    duration_hours: float,
) -> list[ScenarioResult]:
    """Dort kontrolcuyu da N seed ile kosup ScenarioResult listesi dondurur.

    Donus sirasi: ``ALL_SCENARIOS`` sirasi
    (fixed -> adaptive -> predictive -> preemptive) — sunumda da bu
    sirayla gosterilir.
    """
    seeds_list = list(seeds)
    return [run_scenario(s, seeds_list, duration_hours) for s in ALL_SCENARIOS]


def results_to_dataframe(results: list[ScenarioResult]) -> pd.DataFrame:
    """Sonuc listesini duzlestir, CSV'ye yazmak için DataFrame yap."""
    return pd.DataFrame([r.to_row() for r in results])
