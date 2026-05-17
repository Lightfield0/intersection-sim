"""dashboard_helpers birim testleri — Streamlit'siz, saf veri/matplotlib.

Streamlit UI'yi test etmiyoruz (zor + degeri az); ama yardimci fonksiyonlar
testlerle dogrulaniyor: dogru DataFrame sekli, dogru sayilar, matplotlib
figure dondurme smoke testi.
"""

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest
from matplotlib.figure import Figure

from intersection_sim.dashboard_helpers import (
    build_intersection_diagram,
    prepare_direction_wait_df,
    prepare_queue_timeseries,
    prepare_vehicle_type_counts,
)
from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.signal import LightState
from intersection_sim.domain.vehicle import Vehicle, VehicleType
from intersection_sim.metrics.metrics_collector import (
    MetricsCollector,
    MetricsReport,
)

# ---- prepare_queue_timeseries -----------------------------------------------


def test_queue_timeseries_long_format_with_4_directions() -> None:
    """4 yonun her biri icin satir uretmeli, sirayla."""
    # Iki snapshot zamanli sentetik veri
    df_in = pd.DataFrame([
        {"sim_time_s": 0.0, "queue_N": 1, "queue_S": 2, "queue_E": 3, "queue_W": 4,
         "active_green": "N", "total_queue": 10},
        {"sim_time_s": 10.0, "queue_N": 5, "queue_S": 0, "queue_E": 1, "queue_W": 0,
         "active_green": "E", "total_queue": 6},
    ])
    out = prepare_queue_timeseries(df_in)
    assert set(out.columns) == {"sim_time_s", "direction", "queue_length"}
    # 4 yon x 2 zaman = 8 satir
    assert len(out) == 8
    # Yon etiketi sadece "N", "S", "E", "W" — "queue_" on-eki olmamali
    assert set(out["direction"].unique()) == {"N", "S", "E", "W"}
    # Ilk zaman dilimi sayilari korunuyor mu
    t0_north = out[(out["sim_time_s"] == 0.0) & (out["direction"] == "N")]
    assert int(t0_north["queue_length"].iloc[0]) == 1


def test_queue_timeseries_empty_input_returns_empty_df() -> None:
    out = prepare_queue_timeseries(pd.DataFrame())
    assert out.empty
    assert list(out.columns) == ["sim_time_s", "direction", "queue_length"]


# ---- prepare_direction_wait_df ----------------------------------------------


def _build_report_with_direction_waits(waits: dict[Direction, float]) -> MetricsReport:
    """Yon bazli bekleme verisini sentetik yoldan rapora goister."""
    collector = MetricsCollector()
    # Her yon icin tek bir arac kaydet — wait_time = istenen deger
    for d, w in waits.items():
        v = Vehicle(
            vehicle_id=int(d.value.encode()[0]),  # benzersiz id
            direction=d,
            arrival_time=0.0,
            cross_start_time=w,    # wait_time = w - 0 = w
            cross_end_time=w + 2.0,
        )
        collector.record_vehicle_served(v)
    return collector.build_report(horizon_seconds=100.0)


def test_direction_wait_df_returns_all_four_directions_in_order() -> None:
    """4 yon icin satir donmeli, sirayla N, E, S, W."""
    waits = {
        Direction.NORTH: 5.0,
        Direction.EAST: 10.0,
        Direction.SOUTH: 15.0,
        Direction.WEST: 20.0,
    }
    report = _build_report_with_direction_waits(waits)
    df = prepare_direction_wait_df(report)

    assert list(df["direction"]) == [d.value for d in ALL_DIRECTIONS]
    assert df.loc[df["direction"] == "N", "mean_wait_s"].iloc[0] == pytest.approx(5.0)
    assert df.loc[df["direction"] == "W", "mean_wait_s"].iloc[0] == pytest.approx(20.0)
    # Turkce ad sutunu var
    assert "direction_tr" in df.columns
    assert df.loc[df["direction"] == "N", "direction_tr"].iloc[0] == "Kuzey"


def test_direction_wait_df_keeps_none_for_directions_without_vehicles() -> None:
    """Hic arac gormemis yonun wait_s None/NaN olmali (pandas None -> NaN)."""
    report = _build_report_with_direction_waits({Direction.NORTH: 8.0})
    df = prepare_direction_wait_df(report)
    # S, E, W icin pd.isna True olmali
    for d in (Direction.SOUTH, Direction.EAST, Direction.WEST):
        val = df.loc[df["direction"] == d.value, "mean_wait_s"].iloc[0]
        assert pd.isna(val), f"{d.value} mean_wait_s NaN olmali, deger: {val}"


# ---- prepare_vehicle_type_counts --------------------------------------------


def test_vehicle_type_counts_sums_correctly() -> None:
    collector = MetricsCollector()
    # 3 normal, 1 acil
    for i in range(3):
        collector.record_vehicle_served(Vehicle(
            vehicle_id=i, direction=Direction.NORTH, arrival_time=0.0,
        ))
    collector.record_vehicle_served(Vehicle(
        vehicle_id=99, direction=Direction.SOUTH,
        vehicle_type=VehicleType.EMERGENCY, arrival_time=0.0,
    ))

    counts = prepare_vehicle_type_counts(collector)
    assert counts["normal"] == 3
    assert counts["emergency"] == 1
    assert counts["normal"] + counts["emergency"] == len(collector.vehicles_served)


# ---- build_intersection_diagram ---------------------------------------------


def test_build_intersection_diagram_returns_matplotlib_figure() -> None:
    """Smoke test: figure dondurmeli, hata firlamamali."""
    signals = {d: LightState.RED for d in Direction}
    signals[Direction.NORTH] = LightState.GREEN
    queue_lengths = {
        Direction.NORTH: 3,
        Direction.SOUTH: 1,
        Direction.EAST: 7,
        Direction.WEST: 2,
    }
    fig = build_intersection_diagram(signals, queue_lengths, title="Test")
    assert isinstance(fig, Figure)
    # Title set edilmis mi
    assert any(ax.get_title() == "Test" for ax in fig.axes)


def test_diagram_handles_large_queue_with_overflow_indicator() -> None:
    """Kuyruk max_vehicles_per_arm'i asarsa hata cikmasin (overflow gosterilir)."""
    signals = {d: LightState.RED for d in Direction}
    queue_lengths = {
        Direction.NORTH: 50,  # cok uzun
        Direction.SOUTH: 0,
        Direction.EAST: 0,
        Direction.WEST: 0,
    }
    fig = build_intersection_diagram(
        signals, queue_lengths, max_vehicles_per_arm=5,
    )
    assert isinstance(fig, Figure)
