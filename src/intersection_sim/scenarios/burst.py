"""Burst senaryosu — predictive controller'in trend yakalama gucu testi.

Mevcut comparison.csv durağan trafikte 4 kontrolcüyü karşılaştırıyor;
adaptive ve hibrit predictive orada **eşdeğer** ortalama bekleme veriyor.
Bu modul AYRI bir senaryoyu test eder:

    "Belirli bir saat dilim icinde tek yone ANI talep yiginlamasi"
    → SCATS / SCOOT tarzi sistemlerin ana sorun alani.

Gercek dunya karsiliklari:
* Okul cikisi (15:30 civari icin Kuzey'e burst)
* Mac sonu stadyum trafigi
* Kaza/yol kapanmasi sonrasi yonlendirme
* Cuma aksami toplu cikis

Beklenti: hibrit predictive trend bonusu ile bursti adaptifTEN ONCE
yakalamasi. Bu modul:

1. Standart 4 saat koşum + ortada 30 dk Kuzey burst (+20 arac/dk)
2. 4 kontrolcuyu 5 seed × 4 saat ile kosturur
3. ScenarioResult listesi -> comparison_burst.csv + 2 PNG
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from intersection_sim.domain.config import ArrivalProfile, BurstEvent, SimConfig
from intersection_sim.domain.direction import Direction
from intersection_sim.scenarios.definitions import ALL_SCENARIOS, ScenarioDef
from intersection_sim.scenarios.runner import (
    ScenarioResult,
    ScenarioRun,
    results_to_dataframe,
)
from intersection_sim.simulation.runner import run_with_controller

# Burst parametreleri (default sunum senaryosu)
DEFAULT_BURST_START_S: float = 1800.0      # saat 0.5 (30. dakika)
DEFAULT_BURST_DURATION_S: float = 1800.0   # 30 dakika
DEFAULT_BURST_DIRECTION: Direction = Direction.NORTH
DEFAULT_BURST_EXTRA_RATE: float = 20.0     # +20 arac/dk = 1200/saat ek yigin


def make_burst_profile(
    start_s: float = DEFAULT_BURST_START_S,
    duration_s: float = DEFAULT_BURST_DURATION_S,
    direction: Direction = DEFAULT_BURST_DIRECTION,
    extra_rate_per_min: float = DEFAULT_BURST_EXTRA_RATE,
) -> ArrivalProfile:
    """Burst event'li ArrivalProfile uretir."""
    event = BurstEvent(
        start_time_s=start_s,
        duration_s=duration_s,
        direction=direction,
        extra_rate_per_min=extra_rate_per_min,
    )
    return ArrivalProfile(burst_events=[event])


def run_burst_scenario(
    scenario: ScenarioDef,
    seeds: list[int],
    duration_hours: float,
    arrival_profile: ArrivalProfile,
) -> ScenarioResult:
    """Bir senaryoyu burst trafiginde N seed ile kosar."""
    runs: list[ScenarioRun] = []
    for s in seeds:
        cfg = SimConfig(
            seed=s,
            horizon_seconds=duration_hours * 3600.0,
            arrivals=arrival_profile,
        )
        intersection = run_with_controller(cfg, scenario.controller)
        report = intersection.metrics.build_report(cfg.horizon_seconds)
        runs.append(ScenarioRun(name=scenario.name, seed=s, report=report))
    return ScenarioResult(scenario=scenario, runs=runs)


def compare_burst_controllers(
    seeds: list[int],
    duration_hours: float,
    arrival_profile: ArrivalProfile | None = None,
) -> list[ScenarioResult]:
    """4 kontrolcuyu burst senaryosu altinda N seed ile karsilastir."""
    profile = arrival_profile or make_burst_profile()
    return [
        run_burst_scenario(sc, seeds, duration_hours, profile)
        for sc in ALL_SCENARIOS
    ]


def _save_burst_bar_chart(
    results: list[ScenarioResult],
    output_path: Path,
) -> None:
    """4 kontrolcunun ortalama bekleme + p95 yan yana bar chart'i."""
    names = [r.scenario.display_name_tr for r in results]
    colors = [r.scenario.color for r in results]
    means = [r.mean_wait_time_s_mean for r in results]
    p95s = [r.p95_wait_s_mean for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Ortalama bekleme
    bars1 = ax1.bar(names, means, color=colors, edgecolor="#1F2937", linewidth=0.8)
    for bar, v in zip(bars1, means):
        ax1.text(bar.get_x() + bar.get_width() / 2, v + max(means) * 0.02,
                 f"{v:.1f}", ha="center", va="bottom",
                 fontsize=10, fontweight="bold")
    ax1.set_title("Ani Talep — Ortalama Bekleme", fontsize=12)
    ax1.set_ylabel("Bekleme (sn)")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(axis="y", linestyle="--", alpha=0.3)
    # Eğer fixed çok büyükse log scale kullan
    if max(means) > 10 * min(means):
        ax1.set_yscale("log")
        ax1.set_ylabel("Bekleme (sn, log)")

    # p95
    bars2 = ax2.bar(names, p95s, color=colors, edgecolor="#1F2937", linewidth=0.8)
    for bar, v in zip(bars2, p95s):
        ax2.text(bar.get_x() + bar.get_width() / 2, v + max(p95s) * 0.02,
                 f"{v:.1f}", ha="center", va="bottom",
                 fontsize=10, fontweight="bold")
    ax2.set_title("Ani Talep — En Kötü %5 Bekleme", fontsize=12)
    ax2.set_ylabel("en kötü %5 bekleme (sn)")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(axis="y", linestyle="--", alpha=0.3)
    if max(p95s) > 10 * min(p95s):
        ax2.set_yscale("log")
        ax2.set_ylabel("en kötü %5 (sn, log)")

    fig.suptitle(
        "Ani talep: 30 dk boyunca Kuzey'e +20 araç/dk ek yığın "
        "(saat 0.5–1.0)",
        fontsize=11, fontweight="bold", color="#1B4D3E",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="intersection_sim.scenarios.burst",
        description="4 kontrolcuyu burst senaryosunda karsilastirir.",
    )
    parser.add_argument("--seeds", type=int, default=5,
                        help="Kac seed kullanilsin (default: 5)")
    parser.add_argument("--duration-hours", type=float, default=4.0,
                        help="Kosum suresi saat (default: 4)")
    parser.add_argument("--output", type=Path, default=Path("results"),
                        help="CSV / PNG cikti klasoru")
    parser.add_argument("--burst-start-min", type=float, default=30.0,
                        help="Burst basladigi dakika (default: 30. dk)")
    parser.add_argument("--burst-duration-min", type=float, default=30.0,
                        help="Burst suresi dakika (default: 30 dk)")
    parser.add_argument("--burst-extra-rate", type=float, default=20.0,
                        help="Burst ek hizi arac/dk (default: 20)")
    parser.add_argument("--burst-direction", type=str, default="N",
                        choices=["N", "S", "E", "W"],
                        help="Burst yonu (default: N)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    profile = make_burst_profile(
        start_s=args.burst_start_min * 60.0,
        duration_s=args.burst_duration_min * 60.0,
        direction=Direction(args.burst_direction),
        extra_rate_per_min=args.burst_extra_rate,
    )
    seeds = list(range(args.seeds))
    print(f"BURST karsilastirma basliyor: {args.seeds} seed × 4 kontrolcü × "
          f"{args.duration_hours}h (burst: yön={args.burst_direction}, "
          f"{args.burst_start_min}-{args.burst_start_min + args.burst_duration_min} dk, "
          f"+{args.burst_extra_rate} arac/dk)")

    results = compare_burst_controllers(seeds, args.duration_hours, profile)
    df = results_to_dataframe(results)
    csv_path = args.output / "comparison_burst.csv"
    df.to_csv(csv_path, index=False)

    png_path = args.output / "comparison_burst.png"
    _save_burst_bar_chart(results, png_path)

    print()
    print("=" * 70)
    print(" Burst Karşılaştırma Tablosu")
    print("=" * 70)
    print(df[[
        "controller", "mean_wait_s_mean", "p95_wait_s_mean",
        "emergency_wait_s_mean", "throughput_per_hour_mean",
        "fairness_index_mean",
    ]].to_string(index=False))
    print()
    print(f" yazildi: {csv_path}")
    print(f" yazildi: {png_path}")


if __name__ == "__main__":
    main()
