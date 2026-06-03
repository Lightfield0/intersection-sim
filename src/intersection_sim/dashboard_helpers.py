"""Streamlit-bagimsiz veri katmani.

Bu modul Streamlit ve Plotly import etmez — sadece pandas, matplotlib
ve domain nesneleri. Boylece dashboard.py'deki widget mantigi ile
hesaplama mantigi ayri kalir; testler hesaplamalari widget'siz
dogrulayabilir.

Triage projesinde benzer bir ayrim vardi ancak burada daha sade:
3 prepare-* fonksiyonu + 1 matplotlib diyagram figureru. Sankey yok,
Plotly yok.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.signal import LightState
from intersection_sim.domain.vehicle import VehicleType

if TYPE_CHECKING:
    from intersection_sim.metrics.metrics_collector import MetricsCollector, MetricsReport


# ---------- Zaman serisi (kuyruklar) -----------------------------------------


def prepare_queue_timeseries(snapshots_df: pd.DataFrame) -> pd.DataFrame:
    """Snapshot DataFrame'ini long-format zaman serisine cevirir.

    Girdi sutunlari: ``sim_time_s, queue_N, queue_S, queue_E, queue_W, ...``
    Cikti sutunlari: ``sim_time_s, direction, queue_length``

    Streamlit/matplotlib bu uzun formatta gruplayip cizgi cizebilir.
    """
    if snapshots_df.empty:
        return pd.DataFrame(columns=["sim_time_s", "direction", "queue_length"])

    value_cols = [f"queue_{d.value}" for d in Direction]
    melted = snapshots_df.melt(
        id_vars=["sim_time_s"],
        value_vars=value_cols,
        var_name="direction",
        value_name="queue_length",
    )
    # "queue_N" -> "N"
    melted["direction"] = melted["direction"].str.replace("queue_", "", regex=False)
    return melted


# ---------- Yon bazli ortalama bekleme ---------------------------------------


def prepare_direction_wait_df(report: MetricsReport) -> pd.DataFrame:
    """Yon bazli ortalama bekleme suresini DataFrame olarak dondurur.

    Sutunlar: ``direction, direction_tr, mean_wait_s``
    Sira ALL_DIRECTIONS sirasi (N, E, S, W) — sunumda istikrarli.
    """
    rows: list[dict[str, object]] = []
    for d in ALL_DIRECTIONS:
        rows.append({
            "direction": d.value,
            "direction_tr": d.display_name_tr,
            "mean_wait_s": report.mean_wait_by_direction_s.get(d.value),
        })
    return pd.DataFrame(rows)


# ---------- Arac tipi sayilari (pie chart icin) ------------------------------


def prepare_vehicle_type_counts(collector: MetricsCollector) -> dict[str, int]:
    """Normal ve acil arac sayilarini dondurur.

    MetricsReport araç sayilarini tutmuyor (sadece ortalamalari) — bu
    yuzden ham collector'a bakiyoruz.
    """
    normal = sum(1 for v in collector.vehicles_served
                 if v.vehicle_type is VehicleType.NORMAL)
    emergency = sum(1 for v in collector.vehicles_served
                    if v.vehicle_type is VehicleType.EMERGENCY)
    return {"normal": normal, "emergency": emergency}


# ---------- Kavsak diyagrami (statik matplotlib) -----------------------------


# Diyagram boyutlandirma sabitleri — diyagram fonksiyonunu okurken
# anlasilir hale getirir.
_AXIS_LIMIT = 10.0       # plot kenar uzakligi (her yon icin -10..+10)
_ROAD_HALF_WIDTH = 1.2   # yol genisliginin yarisi (kavsak ortasinda kavsigin boyutu)
_QUEUE_OFFSET = 2.0      # kuyruk ilk araci kavsaktan ne kadar uzakta basliyor
_VEHICLE_SIZE = 0.7      # her kuyruk araci icin kare boyutu
_VEHICLE_SPACING = 0.9   # araclar arasi mesafe
_SIGNAL_RADIUS = 0.55    # sinyal yuvarlak yaricapi
_SIGNAL_OFFSET = 1.7     # sinyal kavsaktan ne kadar uzakta (yolun yaninda)


_LIGHT_COLORS = {
    LightState.GREEN: "#16A34A",
    LightState.YELLOW: "#FACC15",
    LightState.RED: "#DC2626",
}


def build_intersection_diagram(
    signals: dict[Direction, LightState],
    queue_lengths: dict[Direction, int],
    *,
    title: str | None = None,
    max_vehicles_per_arm: int = 6,
) -> Figure:
    """4 yollu kavsagi yukaridan goren bir matplotlib diyagrami yapar.

    - Her yon icin: gri yol seridi, sinyal yuvarlagi, kuyruktaki araclar
      kucuk siyah dikdortgenler.
    - Kavsak ortasinda boş bir kare (yol kesişimi).

    ``max_vehicles_per_arm`` cok uzun kuyruklarda gosterilecek max arac
    sayisi — fazlasini sayi olarak yazariz ("...+12 daha" gibi).
    """
    fig, ax = plt.subplots(figsize=(8.0, 8.0))
    ax.set_xlim(-_AXIS_LIMIT, _AXIS_LIMIT)
    ax.set_ylim(-_AXIS_LIMIT, _AXIS_LIMIT)
    ax.set_aspect("equal")
    ax.set_axis_off()

    # 1. Yollar (her yon icin acik gri sirit)
    road_color = "#9CA3AF"
    # Kuzey-Guney yol (dikey serit)
    ax.add_patch(mpatches.Rectangle(
        (-_ROAD_HALF_WIDTH, -_AXIS_LIMIT),
        2 * _ROAD_HALF_WIDTH, 2 * _AXIS_LIMIT,
        facecolor=road_color, edgecolor="none", alpha=0.4,
    ))
    # Dogu-Bati yol (yatay serit)
    ax.add_patch(mpatches.Rectangle(
        (-_AXIS_LIMIT, -_ROAD_HALF_WIDTH),
        2 * _AXIS_LIMIT, 2 * _ROAD_HALF_WIDTH,
        facecolor=road_color, edgecolor="none", alpha=0.4,
    ))

    # 2. Kavsak ortasi
    ax.add_patch(mpatches.Rectangle(
        (-_ROAD_HALF_WIDTH, -_ROAD_HALF_WIDTH),
        2 * _ROAD_HALF_WIDTH, 2 * _ROAD_HALF_WIDTH,
        facecolor="#4B5563", edgecolor="white", linewidth=1.5,
    ))

    # 3. Her yon icin sinyal + kuyruk
    for d in ALL_DIRECTIONS:
        _draw_signal_and_queue(
            ax, d, signals[d], queue_lengths[d], max_vehicles_per_arm,
        )

    # 4. Yon etiketleri (kosegene yakin)
    _draw_direction_labels(ax)

    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color="#1F2937")

    fig.tight_layout()
    return fig


def _draw_signal_and_queue(
    ax: Any,
    direction: Direction,
    state: LightState,
    queue_len: int,
    max_vehicles: int,
) -> None:
    """Tek bir yon kolu icin sinyal yuvarlagi + kuyruktaki araclari ciz."""
    # Yonun "kavsaktan disariya" birim vektorleri
    # N: yukari (+y), S: asagi (-y), E: saga (+x), W: sola (-x)
    if direction is Direction.NORTH:
        # Kuzey kolu yukaridan asagiya geliyor (yani kuyruk yukarida)
        sig_x, sig_y = _ROAD_HALF_WIDTH + _SIGNAL_OFFSET, _SIGNAL_OFFSET
        veh_dir_x, veh_dir_y = 0.0, 1.0
    elif direction is Direction.SOUTH:
        sig_x, sig_y = -_ROAD_HALF_WIDTH - _SIGNAL_OFFSET, -_SIGNAL_OFFSET
        veh_dir_x, veh_dir_y = 0.0, -1.0
    elif direction is Direction.EAST:
        # Dogu kolu sagdan geliyor (kuyruk sagda)
        sig_x, sig_y = _SIGNAL_OFFSET, -_ROAD_HALF_WIDTH - _SIGNAL_OFFSET
        veh_dir_x, veh_dir_y = 1.0, 0.0
    else:  # WEST
        sig_x, sig_y = -_SIGNAL_OFFSET, _ROAD_HALF_WIDTH + _SIGNAL_OFFSET
        veh_dir_x, veh_dir_y = -1.0, 0.0

    # Sinyal yuvarlagi
    ax.add_patch(mpatches.Circle(
        (sig_x, sig_y), _SIGNAL_RADIUS,
        facecolor=_LIGHT_COLORS[state],
        edgecolor="#1F2937", linewidth=1.2,
    ))

    # Kuyruktaki araclar — kavsaktan disa dogru sirayla
    to_draw = min(queue_len, max_vehicles)
    for i in range(to_draw):
        # i'nin "kavsaktan uzakliği" = QUEUE_OFFSET + i * SPACING
        dist = _QUEUE_OFFSET + i * _VEHICLE_SPACING
        # Yon kolu uzerinde, road serit ortasinda
        if direction in (Direction.NORTH, Direction.SOUTH):
            vx = -0.4 * veh_dir_x  # 0
            vy = veh_dir_y * dist
            # araclari yolun kendi seritinde tut
            vx = 0.4 if direction is Direction.NORTH else -0.4
        else:  # EAST / WEST
            vx = veh_dir_x * dist
            vy = -0.4 if direction is Direction.EAST else 0.4

        ax.add_patch(mpatches.Rectangle(
            (vx - _VEHICLE_SIZE / 2, vy - _VEHICLE_SIZE / 2),
            _VEHICLE_SIZE, _VEHICLE_SIZE,
            facecolor="#1F2937", edgecolor="white", linewidth=0.5,
        ))

    # Eger sigamadigimiz araclar varsa, ucta sayi notu
    if queue_len > max_vehicles:
        extra = queue_len - max_vehicles
        far_x = veh_dir_x * (_QUEUE_OFFSET + (max_vehicles + 0.5) * _VEHICLE_SPACING)
        far_y = veh_dir_y * (_QUEUE_OFFSET + (max_vehicles + 0.5) * _VEHICLE_SPACING)
        if direction in (Direction.NORTH, Direction.SOUTH):
            far_x = 0.4 if direction is Direction.NORTH else -0.4
        else:
            far_y = -0.4 if direction is Direction.EAST else 0.4
        ax.text(
            far_x, far_y, f"+{extra}",
            ha="center", va="center", fontsize=10, color="#1F2937",
            fontweight="bold",
        )


def _draw_direction_labels(ax: Any) -> None:
    """4 koseye N/E/S/W etiketleri."""
    label_positions = {
        "Kuzey": (0.0, _AXIS_LIMIT - 0.5),
        "Doğu":  (_AXIS_LIMIT - 0.5, 0.0),
        "Güney": (0.0, -_AXIS_LIMIT + 0.5),
        "Batı":  (-_AXIS_LIMIT + 0.5, 0.0),
    }
    for text, (x, y) in label_positions.items():
        ha = "center" if y != 0 else ("left" if x < 0 else "right")
        va = "center" if x != 0 else ("bottom" if y < 0 else "top")
        ax.text(
            x, y, text,
            ha=ha, va=va, fontsize=11, color="#1F2937", fontweight="bold",
        )


# ---------- Faz Final: Dagilim helper'i --------------------------------------


def prepare_wait_distribution(
    collector: MetricsCollector,
) -> dict[str, Any]:
    """Bekleme suresi dagilim hazirlama.

    Doner: {'overall': [...], 'normal': [...], 'emergency': [...],
            'by_direction': {dir_value: [...]}}
    Histogram/boxplot icin kullanilir.
    """
    overall: list[float] = []
    normal: list[float] = []
    emergency: list[float] = []
    by_dir: dict[str, list[float]] = {d.value: [] for d in Direction}

    for v in collector.vehicles_served:
        if v.wait_time is None:
            continue
        overall.append(v.wait_time)
        if v.vehicle_type is VehicleType.EMERGENCY:
            emergency.append(v.wait_time)
        else:
            normal.append(v.wait_time)
        by_dir[v.direction.value].append(v.wait_time)

    return {
        "overall": overall,
        "normal": normal,
        "emergency": emergency,
        "by_direction": by_dir,
    }


# ---------- Faz Final: Saatlik heatmap DataFrame'i ---------------------------


def prepare_hourly_heatmap(report: MetricsReport) -> pd.DataFrame:
    """Saatlik bekleme heatmap'i icin uzun-format DataFrame.

    Sutunlar: ``hour, direction, direction_tr, mean_wait_s``.
    Streamlit veya matplotlib pivot ile heatmap yapabilir.
    """
    rows: list[dict[str, object]] = []
    for d in ALL_DIRECTIONS:
        per_hour = report.hourly_mean_wait_by_direction_s.get(d.value, [])
        for hour, wait in enumerate(per_hour):
            rows.append({
                "hour": hour,
                "direction": d.value,
                "direction_tr": d.display_name_tr,
                "mean_wait_s": wait if wait is not None else 0.0,
            })
    return pd.DataFrame(rows)


# ---------- Faz Final v2: Sensitivity sweep --------------------------------


def predictive_alpha_sweep(
    alphas: list[float],
    seeds: list[int],
    duration_hours: float = 2.0,
) -> pd.DataFrame:
    """Hibrit predictive'in α parametresini taratip metrik tablosu uretir.

    Her α icin: seed'ler boyunca koşum + ortalamalar. Sonuc DataFrame:
    sutunlar ``alpha, mean_wait_s, p95_wait_s, fairness_index``.

    Adaptive baseline da (α=0 değil, gerçek adaptive_controller) eklenir
    karsilastirma kolayligi için.
    """
    from intersection_sim.controllers import predictive as pred_mod
    from intersection_sim.controllers.adaptive import adaptive_controller
    from intersection_sim.domain.config import SimConfig
    from intersection_sim.simulation.runner import run_with_controller

    rows: list[dict[str, object]] = []

    # Adaptive baseline
    a_means: list[float] = []
    a_p95s: list[float] = []
    a_fairs: list[float] = []
    for s in seeds:
        cfg = SimConfig(seed=s, horizon_seconds=duration_hours * 3600.0)
        r = run_with_controller(cfg, adaptive_controller).metrics.build_report(
            cfg.horizon_seconds,
        )
        mean_w = r.mean_wait_time_s
        if mean_w is not None:
            a_means.append(mean_w)
        p95_w = r.wait_percentiles_s.get("p95")
        if p95_w is not None:
            a_p95s.append(p95_w)
        fair = r.fairness_index
        if fair is not None:
            a_fairs.append(fair)
    rows.append({
        "label": "adaptive (baseline)",
        "alpha": None,
        "mean_wait_s": sum(a_means) / len(a_means) if a_means else None,
        "p95_wait_s": sum(a_p95s) / len(a_p95s) if a_p95s else None,
        "fairness_index": sum(a_fairs) / len(a_fairs) if a_fairs else None,
    })

    # Predictive sweep
    original_alpha = pred_mod.HYBRID_ALPHA
    try:
        for alpha in alphas:
            pred_mod.HYBRID_ALPHA = alpha
            means: list[float] = []
            p95s: list[float] = []
            fairs: list[float] = []
            for s in seeds:
                cfg = SimConfig(seed=s, horizon_seconds=duration_hours * 3600.0)
                r = run_with_controller(
                    cfg, pred_mod.predictive_controller,
                ).metrics.build_report(cfg.horizon_seconds)
                mean_w = r.mean_wait_time_s
                if mean_w is not None:
                    means.append(mean_w)
                p95_w = r.wait_percentiles_s.get("p95")
                if p95_w is not None:
                    p95s.append(p95_w)
                fair = r.fairness_index
                if fair is not None:
                    fairs.append(fair)
            rows.append({
                "label": f"predictive α={alpha:.2f}",
                "alpha": alpha,
                "mean_wait_s": sum(means) / len(means) if means else None,
                "p95_wait_s": sum(p95s) / len(p95s) if p95s else None,
                "fairness_index": sum(fairs) / len(fairs) if fairs else None,
            })
    finally:
        # α'yi geri restore et — diger testleri etkilemeyelim
        pred_mod.HYBRID_ALPHA = original_alpha

    return pd.DataFrame(rows)
