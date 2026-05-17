"""Domain modellerinin temel davranis testleri.

Bu testlerin tamami simulasyondan bagimsizdir — SimPy yok, sadece
pydantic/python. Faz 1'de tipler dogru kuruldu mu, hesaplanmis
ozellikler dogru cikiyor mu kontrol eder.
"""

import pytest
from pydantic import ValidationError

from intersection_sim.domain.config import ArrivalProfile, SimConfig
from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.signal import SignalConfig
from intersection_sim.domain.vehicle import Vehicle, VehicleType

# ---------- Direction --------------------------------------------------------


def test_directions_have_turkish_display_names() -> None:
    """Her yonun display_name_tr ozelligi Turkce kelime dondurmeli."""
    assert Direction.NORTH.display_name_tr == "Kuzey"
    assert Direction.SOUTH.display_name_tr == "Guney"
    assert Direction.EAST.display_name_tr == "Dogu"
    assert Direction.WEST.display_name_tr == "Bati"


def test_all_directions_contains_all_four_in_clockwise_order() -> None:
    """Sabit kontrolcu rotasyonu N -> E -> S -> W olarak duzenli olmali."""
    assert ALL_DIRECTIONS == [
        Direction.NORTH,
        Direction.EAST,
        Direction.SOUTH,
        Direction.WEST,
    ]
    assert len(ALL_DIRECTIONS) == 4
    assert set(ALL_DIRECTIONS) == set(Direction)


# ---------- Vehicle ----------------------------------------------------------


def test_vehicle_defaults_to_normal_and_no_crossings() -> None:
    v = Vehicle(vehicle_id=0, direction=Direction.NORTH, arrival_time=10.0)
    assert v.vehicle_type is VehicleType.NORMAL
    assert v.is_emergency is False
    assert v.cross_start_time is None
    assert v.cross_end_time is None
    assert v.wait_time is None
    assert v.total_time_in_system is None


def test_vehicle_wait_time_computed_from_arrival_and_cross_start() -> None:
    v = Vehicle(
        vehicle_id=1,
        direction=Direction.EAST,
        arrival_time=10.0,
        cross_start_time=42.0,
        cross_end_time=44.0,
    )
    assert v.wait_time == pytest.approx(32.0)
    assert v.total_time_in_system == pytest.approx(34.0)


def test_emergency_vehicle_flag() -> None:
    v = Vehicle(
        vehicle_id=2, direction=Direction.WEST,
        vehicle_type=VehicleType.EMERGENCY, arrival_time=0.0,
    )
    assert v.is_emergency is True


def test_vehicle_id_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        Vehicle(vehicle_id=-1, direction=Direction.NORTH, arrival_time=0.0)


# ---------- SignalConfig -----------------------------------------------------


def test_fixed_cycle_duration_matches_spec() -> None:
    """4 yon * (30 + 3 + 1) = 136 sn — spec'te belirtilen tam cevrim suresi."""
    cfg = SignalConfig()
    assert cfg.fixed_cycle_duration_s == pytest.approx(136.0)


def test_signal_config_rejects_zero_green() -> None:
    with pytest.raises(ValidationError):
        SignalConfig(green_duration_s=0.0)


# ---------- ArrivalProfile ---------------------------------------------------


def test_arrival_profile_distinguishes_peak_and_normal_hours() -> None:
    profile = ArrivalProfile()
    # Saat 03:00 normal -> 0.4 N
    normal_rate = profile.rate_for(Direction.NORTH, 3 * 3600.0)
    # Saat 08:00 yogun -> 0.8 N
    peak_rate = profile.rate_for(Direction.NORTH, 8 * 3600.0)
    assert normal_rate == pytest.approx(0.4)
    assert peak_rate == pytest.approx(0.8)
    assert peak_rate > normal_rate


def test_arrival_profile_evening_peak_window() -> None:
    """17:00-19:00 araligi yogun saate denk dusmeli."""
    profile = ArrivalProfile()
    # 17:30 yogun
    assert profile.rate_for(Direction.EAST, 17.5 * 3600.0) > profile.base_rate_per_min[Direction.EAST] - 0.001
    assert profile.rate_for(Direction.EAST, 17.5 * 3600.0) == pytest.approx(0.6)
    # 20:00 normal saate dondu
    assert profile.rate_for(Direction.EAST, 20.0 * 3600.0) == pytest.approx(0.3)


def test_sim_config_defaults_match_spec() -> None:
    cfg = SimConfig()
    assert cfg.horizon_seconds == 14400.0  # 4 saat
    assert cfg.seed == 42
    assert isinstance(cfg.signal, SignalConfig)
    assert isinstance(cfg.arrivals, ArrivalProfile)
