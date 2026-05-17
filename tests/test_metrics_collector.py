"""MetricsCollector ve MetricsReport birim testleri.

Sentetik araclar uretip dogrudan koleksioner'a yazdiriyoruz — bu
testler SimPy'siz hesaplamalari dogruluyor.
"""

import json
from pathlib import Path

from intersection_sim.domain.direction import Direction
from intersection_sim.domain.vehicle import Vehicle, VehicleType
from intersection_sim.metrics.metrics_collector import (
    GREEN_PHASES_PER_CYCLE,
    MetricsCollector,
    MetricsSnapshot,
)


def _make_served(
    pid: int, direction: Direction, arrival: float, cross_start: float, cross_end: float,
    vtype: VehicleType = VehicleType.NORMAL,
) -> Vehicle:
    """Sentetik (kosumda gercek araclar uretilmis gibi) bir Vehicle yarat."""
    return Vehicle(
        vehicle_id=pid,
        direction=direction,
        vehicle_type=vtype,
        arrival_time=arrival,
        cross_start_time=cross_start,
        cross_end_time=cross_end,
    )


# ---- temel arac kaydi ----


def test_wait_time_computed_from_arrival_and_cross_start() -> None:
    """Tek aracin bekleme suresi cross_start - arrival olmali."""
    c = MetricsCollector()
    c.record_vehicle_served(_make_served(0, Direction.NORTH, 0.0, 10.0, 12.0))
    c.record_vehicle_served(_make_served(1, Direction.NORTH, 5.0, 20.0, 22.0))

    report = c.build_report(horizon_seconds=60.0)
    assert report.vehicles_served == 2
    # Beklemeler: 10 sn + 15 sn = ortalama 12.5
    assert report.mean_wait_time_s == 12.5
    assert report.max_wait_time_s == 15.0


def test_per_direction_mean_wait_isolated() -> None:
    """Her yonun ortalama beklemesi sadece o yonun araclarindan hesaplanmali."""
    c = MetricsCollector()
    # N yonu: bekleme 10 + 20 = 15 ortalama
    c.record_vehicle_served(_make_served(0, Direction.NORTH, 0.0, 10.0, 12.0))
    c.record_vehicle_served(_make_served(1, Direction.NORTH, 0.0, 20.0, 22.0))
    # E yonu: bekleme 5 = 5 ortalama
    c.record_vehicle_served(_make_served(2, Direction.EAST, 0.0, 5.0, 7.0))

    report = c.build_report(60.0)
    assert report.mean_wait_by_direction_s["N"] == 15.0
    assert report.mean_wait_by_direction_s["E"] == 5.0
    # S ve W yonune hic arac gelmemis -> None
    assert report.mean_wait_by_direction_s["S"] is None
    assert report.mean_wait_by_direction_s["W"] is None


def test_per_type_mean_wait_separates_emergency_and_normal() -> None:
    """Normal ve acil araclar ayri ayri toplanmali."""
    c = MetricsCollector()
    c.record_vehicle_served(_make_served(0, Direction.NORTH, 0.0, 10.0, 12.0))
    c.record_vehicle_served(
        _make_served(1, Direction.NORTH, 0.0, 2.0, 4.0, vtype=VehicleType.EMERGENCY),
    )

    report = c.build_report(60.0)
    assert report.mean_wait_by_type_s["normal"] == 10.0
    assert report.mean_wait_by_type_s["emergency"] == 2.0


# ---- tam cevrim sayisi ----


def test_full_cycle_count_increments_per_four_green_phases() -> None:
    """4 yesil faz = 1 tam cevrim."""
    c = MetricsCollector()
    for _ in range(GREEN_PHASES_PER_CYCLE * 3):
        c.record_green_phase()
    assert c.green_phase_count == 12
    assert c.full_cycle_count == 3


def test_full_cycle_count_rounds_down_for_partial_cycles() -> None:
    """Eksik yesil faz tam cevrim sayilmaz (4'un kati olmali)."""
    c = MetricsCollector()
    for _ in range(7):  # 1 tam + 3 fazladan
        c.record_green_phase()
    assert c.full_cycle_count == 1


# ---- sinyal degisim sayaci ----


def test_signal_change_count_accumulates() -> None:
    c = MetricsCollector()
    c.record_signal_change()
    c.record_signal_change()
    c.record_signal_change()
    assert c.signal_change_count == 3


# ---- snapshot ortalama kuyruk ----


def test_mean_and_max_queue_from_snapshots() -> None:
    """Snapshot'lardaki kuyruk toplamlarinin ortalama/maks degeri raporda."""
    c = MetricsCollector()
    c.record_snapshot(MetricsSnapshot(
        sim_time_s=0.0,
        queue_lengths={Direction.NORTH: 2, Direction.SOUTH: 1,
                       Direction.EAST: 0, Direction.WEST: 0},
        active_green=Direction.NORTH,
    ))
    c.record_snapshot(MetricsSnapshot(
        sim_time_s=10.0,
        queue_lengths={Direction.NORTH: 5, Direction.SOUTH: 3,
                       Direction.EAST: 1, Direction.WEST: 0},
        active_green=Direction.EAST,
    ))
    report = c.build_report(20.0)
    # Toplam kuyruklar: 3 ve 9, ortalama 6.0
    assert report.mean_queue_length == 6.0
    assert report.max_queue_length == 9


# ---- JSON export ----


def test_write_json_round_trips(tmp_path: Path) -> None:
    """Rapor JSON'a yazilip okundugunda aynı sayilari dondurmeli."""
    c = MetricsCollector()
    c.record_vehicle_served(_make_served(0, Direction.NORTH, 0.0, 10.0, 12.0))

    out = tmp_path / "kpi.json"
    report = c.build_report(3600.0)
    report.write_json(out)
    data = json.loads(out.read_text())

    assert data["vehicles_served"] == 1
    assert data["mean_wait_time_s"] == 10.0
    # throughput: 1 arac / 1 saat = 1.0
    assert data["throughput_per_hour"] == 1.0
