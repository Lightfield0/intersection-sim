"""Burst senaryosu — BurstEvent ve burst karşılaştırma testleri."""

from intersection_sim.domain.config import ArrivalProfile, BurstEvent
from intersection_sim.domain.direction import Direction
from intersection_sim.scenarios.burst import (
    DEFAULT_BURST_DIRECTION,
    DEFAULT_BURST_DURATION_S,
    DEFAULT_BURST_EXTRA_RATE,
    DEFAULT_BURST_START_S,
    compare_burst_controllers,
    make_burst_profile,
)

# ---------- BurstEvent ------------------------------------------------------


def test_burst_event_active_within_window() -> None:
    """Burst window içindeki anlarda aktif olmalı."""
    ev = BurstEvent(
        start_time_s=1800.0, duration_s=600.0,
        direction=Direction.NORTH, extra_rate_per_min=10.0,
    )
    # Başlamadan önce: pasif
    assert not ev.is_active_at(1000.0)
    # Tam başlangıç: aktif
    assert ev.is_active_at(1800.0)
    # Ortada: aktif
    assert ev.is_active_at(2100.0)
    # Tam bitişten 1 sn önce: aktif
    assert ev.is_active_at(2399.0)
    # Tam bitişte: pasif (yarı-açık aralık [start, start+dur))
    assert not ev.is_active_at(2400.0)
    # Bitiş sonrası: pasif
    assert not ev.is_active_at(3000.0)


def test_arrival_profile_rate_includes_burst() -> None:
    """ArrivalProfile.rate_for, aktif burst'lerin extra_rate'ini eklemeli."""
    ev = BurstEvent(
        start_time_s=1800.0, duration_s=600.0,
        direction=Direction.NORTH, extra_rate_per_min=15.0,
    )
    profile = ArrivalProfile(burst_events=[ev])

    # Burst dışı zamanda: sadece base rate (0.4 Kuzey base)
    base = profile.rate_for(Direction.NORTH, sim_time_s=0.0)
    assert abs(base - 0.4) < 1e-9

    # Burst sırasında Kuzey: base + extra
    burst_active = profile.rate_for(Direction.NORTH, sim_time_s=2000.0)
    assert abs(burst_active - (0.4 + 15.0)) < 1e-9

    # Burst sırasında BAŞKA yön (Güney): etkilenmez
    south_during = profile.rate_for(Direction.SOUTH, sim_time_s=2000.0)
    assert abs(south_during - 0.4) < 1e-9


def test_burst_event_invalid_negative_extra_rate_rejected() -> None:
    """Negatif extra_rate kabul edilmemeli (pydantic validation)."""
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        BurstEvent(
            start_time_s=0.0, duration_s=100.0,
            direction=Direction.NORTH, extra_rate_per_min=-5.0,
        )


def test_multiple_burst_events_accumulate() -> None:
    """Aynı yön + aynı zamanda iki burst → extra_rate toplanır."""
    ev1 = BurstEvent(
        start_time_s=1000.0, duration_s=500.0,
        direction=Direction.EAST, extra_rate_per_min=10.0,
    )
    ev2 = BurstEvent(
        start_time_s=1000.0, duration_s=500.0,
        direction=Direction.EAST, extra_rate_per_min=20.0,
    )
    profile = ArrivalProfile(burst_events=[ev1, ev2])
    # Base east = 0.3
    rate = profile.rate_for(Direction.EAST, sim_time_s=1200.0)
    assert abs(rate - (0.3 + 10.0 + 20.0)) < 1e-9


# ---------- Burst senaryosu karşılaştırması --------------------------------


def test_burst_default_constants_reasonable() -> None:
    """Default burst parametreleri makul aralıklarda."""
    assert DEFAULT_BURST_START_S > 0.0
    assert DEFAULT_BURST_DURATION_S > 0.0
    assert DEFAULT_BURST_EXTRA_RATE > 5.0  # anlamlı bir burst
    assert DEFAULT_BURST_DIRECTION in Direction


def test_make_burst_profile_creates_one_event() -> None:
    """make_burst_profile tek burst event'li profile döndürür."""
    profile = make_burst_profile()
    assert len(profile.burst_events) == 1
    ev = profile.burst_events[0]
    assert ev.direction is DEFAULT_BURST_DIRECTION
    assert ev.extra_rate_per_min == DEFAULT_BURST_EXTRA_RATE


def test_compare_burst_controllers_returns_four_results() -> None:
    """compare_burst_controllers tüm 4 kontrolcü için ScenarioResult döndürür."""
    results = compare_burst_controllers(
        seeds=[0, 1], duration_hours=1.0,
    )
    assert len(results) == 4
    names = [r.scenario.name for r in results]
    assert names == ["fixed", "adaptive", "predictive", "preemptive"]


def test_burst_fixed_controller_catastrophic() -> None:
    """Burst senaryosunda fixed kontrol kontrolden çıkmalı (adaptiften ÇOK kötü).

    Sunum kozu: 'sabit zamanlı kontrol burst'te catastrophic fail eder'.
    Adaptive < 100 sn, fixed > 500 sn beklenir.
    """
    results = compare_burst_controllers(
        seeds=[0, 1], duration_hours=2.0,
    )
    fixed = next(r for r in results if r.scenario.name == "fixed")
    adaptive = next(r for r in results if r.scenario.name == "adaptive")
    # Fixed adaptive'den en az 10 kat kötü olmalı
    assert fixed.mean_wait_time_s_mean > 10 * adaptive.mean_wait_time_s_mean
