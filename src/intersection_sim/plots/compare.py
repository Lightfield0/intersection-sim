"""4 kontrolcünün karşılaştırma grafikleri.

Sunumun ana gorselleri burada uretiliyor. Tüm grafikler sade matplotlib
ile, ``Agg`` backend üzerinde (headless ortam için). DejaVu Sans Türkçe
karakterleri sorunsuz gosterir, font.family olarak ayarlandi.

Uc temel grafik:
  1. plot_avg_wait        — ortalama bekleme (4 sutun bar chart)
  2. plot_emergency_wait  — acil arac beklemesi (vurgulu altin slayt)
  3. plot_throughput      — throughput (kontrolcüden bağımsız)

Bonus:
  4. plot_wait_distribution — 4 alt-grafik histogram (her kontrolcü için)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless backend — figure ekrana cizmek yerine PNG yazar

import matplotlib.pyplot as plt
import numpy as np

from intersection_sim.scenarios.runner import ScenarioResult
from intersection_sim.simulation.runner import run_with_controller

# Tüm metinlerde DejaVu Sans — Türkçe 'ı', 'ç', 'ğ' sorunsuz cizilir
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 11
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


def _setup_bar_axes(
    ax: Any,  # matplotlib Axes — typing stubs yok, Any kabul ediyoruz
    results: list[ScenarioResult],
) -> tuple[np.ndarray[Any, Any], list[str]]:
    """X-ekseni etiketlerini ve renkleri kurar, ortak bar layout."""
    labels = [r.scenario.display_name_tr for r in results]
    x = np.arange(len(labels))
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    return x, labels


def plot_avg_wait(results: list[ScenarioResult], path: Path) -> None:
    """Ortalama bekleme suresi — 4 sutunlu bar chart."""
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    x, _ = _setup_bar_axes(ax, results)

    heights = [r.mean_wait_time_s_mean for r in results]
    errs = [r.mean_wait_time_s_std for r in results]
    colors = [r.scenario.color for r in results]

    bars = ax.bar(
        x, heights, yerr=errs, capsize=6,
        color=colors, edgecolor="#1F2937", linewidth=1.0,
    )
    # Bar üzerine sayi etiketi
    for bar, h in zip(bars, heights):
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 1.0,
            f"{h:.1f} sn",
            ha="center", va="bottom", fontsize=12, fontweight="bold",
        )

    ax.set_ylabel("Ortalama bekleme süresi (sn)")
    ax.set_title("Ortalama Bekleme Süresi — 4 Kontrolcü")
    ax.set_ylim(0, max(heights) * 1.25)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_emergency_wait(results: list[ScenarioResult], path: Path) -> None:
    """Acil arac bekleme suresi — sunumun altin grafigi.

    Preemptive sutununa altin kenarli ekstra cerceve ekleniyor — sunumda
    "bunun üzerine konusacak isim" sutunu vurgulamak için.
    """
    fig, ax = plt.subplots(figsize=(8.0, 5.5))
    x, _ = _setup_bar_axes(ax, results)

    heights = [r.emergency_wait_s_mean for r in results]
    errs = [r.emergency_wait_s_std for r in results]
    colors = [r.scenario.color for r in results]

    bars = ax.bar(
        x, heights, yerr=errs, capsize=6,
        color=colors, edgecolor="#1F2937", linewidth=1.0,
    )

    # Preemptive sutununu altin cerceve ile vurgula
    preemptive_idx = next(
        (i for i, r in enumerate(results) if r.scenario.name == "preemptive"),
        None,
    )
    if preemptive_idx is not None:
        bars[preemptive_idx].set_edgecolor("#FFB400")
        bars[preemptive_idx].set_linewidth(3.5)

    for bar, h in zip(bars, heights):
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 0.8,
            f"{h:.1f} sn",
            ha="center", va="bottom", fontsize=12, fontweight="bold",
        )

    ax.set_ylabel("Acil araç ortalama bekleme süresi (sn)")
    ax.set_title("Acil Araç Bekleme Süresi — Ana Sunum Kozu", fontweight="bold")
    ax.set_ylim(0, max(heights) * 1.30)

    # Alt yazi: Sabit -> Preemptive yüzde dususu
    if len(results) >= 3:
        f_em = results[0].emergency_wait_s_mean
        p_em = results[2].emergency_wait_s_mean
        if f_em > 0:
            drop_pct = (f_em - p_em) / f_em * 100.0
            fig.text(
                0.5, 0.02,
                f"Sabit Zamanlı → Acil Öncelikli: %{drop_pct:.1f} düşüş",
                ha="center", fontsize=11, color="#1F2937", fontstyle="italic",
            )

    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_throughput(results: list[ScenarioResult], path: Path) -> None:
    """Throughput — kontrolcüler arasinda neredeyse ayni."""
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    x, _ = _setup_bar_axes(ax, results)

    heights = [r.throughput_per_hour_mean for r in results]
    errs = [r.throughput_per_hour_std for r in results]
    colors = [r.scenario.color for r in results]

    bars = ax.bar(
        x, heights, yerr=errs, capsize=6,
        color=colors, edgecolor="#1F2937", linewidth=1.0,
    )
    for bar, h in zip(bars, heights):
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 1.0,
            f"{h:.1f}",
            ha="center", va="bottom", fontsize=12, fontweight="bold",
        )

    ax.set_ylabel("Throughput (araç / saat)")
    ax.set_title("Throughput — Kontrolcü Tipinden Bağımsız")
    ax.set_ylim(0, max(heights) * 1.20)

    fig.text(
        0.5, 0.02,
        "Geliş Poisson'a bağlı; kontrolcü bekleme suresini optimize eder",
        ha="center", fontsize=10, color="#6B7280", fontstyle="italic",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_wait_distribution(results: list[ScenarioResult], path: Path) -> None:
    """Bonus: kontrolcü basina bekleme suresi histogrami (3 yan yana subplot).

    Her seed için TUM araclarin wait_time'i toplanir, hepsi tek bir
    histograma dokulur. Böylece "Adaptif'in çoğu arac kısa bekler ama
    bir kismi 30+ sn bekler" gibi distribution detaylari gozukur.

    NOT: Bu fonksiyon ScenarioResult kullanmiyor, dogrudan seed'leri
    yeniden kosturmasi gerekiyor — histogram ham wait_time degerlerine
    ihtiyac duyuyor, sadece ortalama yetersiz. Bu yuzden run'lari tekrar
    yapiyor; performans için az seed kullanin.
    """
    fig, axes = plt.subplots(1, len(results), figsize=(4.5 * len(results), 4.5),
                             sharey=True)
    if len(results) == 1:
        axes = [axes]

    for ax, res in zip(axes, results):
        # Tüm seed'lerin tüm araclarinin bekleme sureleri
        waits: list[float] = []
        for run in res.runs:
            # Run.report.mean_wait_time_s ortalama; ham veriye erişemiyoruz.
            # Bu yuzden seed'i yeniden kosturup ham listeyi cikariyoruz.
            config = res.scenario.build_config(
                seed=run.seed,
                duration_hours=run.report.horizon_seconds / 3600.0,
            )
            inter = run_with_controller(config, res.scenario.controller)
            for v in inter.metrics.vehicles_served:
                if v.wait_time is not None:
                    waits.append(v.wait_time)

        ax.hist(
            waits, bins=30, color=res.scenario.color,
            edgecolor="#1F2937", linewidth=0.5, alpha=0.85,
        )
        ax.set_title(res.scenario.display_name_tr, fontweight="bold")
        ax.set_xlabel("Bekleme süresi (sn)")
        ax.grid(axis="y", linestyle="--", alpha=0.3)

    axes[0].set_ylabel("Araç sayısı")
    fig.suptitle("Bekleme Süresi Dağılımı — Tüm Araclar",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def save_all_plots(
    results: list[ScenarioResult], output_dir: Path,
    *, include_distribution: bool = True,
) -> dict[str, Path]:
    """Tüm karşılaştırma grafiklerini diskte yazar.

    Donus: {"avg_wait": ..., "emergency_wait": ..., "throughput": ...}
    Path objeleri (caller print/log için kullanabilir).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {
        "avg_wait": output_dir / "comparison_avg_wait.png",
        "emergency_wait": output_dir / "comparison_emergency_wait.png",
        "throughput": output_dir / "comparison_throughput.png",
    }
    plot_avg_wait(results, paths["avg_wait"])
    plot_emergency_wait(results, paths["emergency_wait"])
    plot_throughput(results, paths["throughput"])

    if include_distribution:
        paths["wait_distribution"] = output_dir / "wait_time_distribution.png"
        plot_wait_distribution(results, paths["wait_distribution"])

    return paths
