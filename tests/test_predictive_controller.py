"""Predictive (tahmine dayali) kontrolcu testleri.

Test edilenler:
1. Yeterli snapshot olmadiginda anlik kuyrukla karar verir (adaptif gibi).
2. Yeterli snapshot oldugunda trend kullanir; artan yon secilir.
3. Tam kosum testi: 4 yon, 4 saat, hata yok + 4 yesil faz / 1 cycle.
"""

from intersection_sim.controllers.predictive import (
    _LOOKBACK_K,
    HYBRID_ALPHA,
    _hybrid_score,
    _predict_queue,
    predictive_controller,
)
from intersection_sim.domain.config import SimConfig
from intersection_sim.domain.direction import Direction
from intersection_sim.metrics.metrics_collector import MetricsSnapshot
from intersection_sim.simulation.runner import run_with_controller


class _FakeIntersection:
    """Minimal stub — _predict_queue testleri icin sadece metrics ve queue_length."""

    def __init__(self) -> None:
        class _M:
            def __init__(self) -> None:
                self.snapshots: list[MetricsSnapshot] = []
        self.metrics = _M()
        self._q: dict[Direction, int] = {d: 0 for d in Direction}

    def queue_length(self, d: Direction) -> int:
        return self._q[d]


def test_predict_queue_without_snapshots_returns_current() -> None:
    """Hic snapshot yoksa adaptif gibi anlik kuyrugu doner."""
    inter = _FakeIntersection()
    inter._q[Direction.NORTH] = 5
    assert _predict_queue(inter, Direction.NORTH) == 5.0


def test_predict_queue_extrapolates_upward_trend() -> None:
    """Kuyruk artiyorsa tahmin son anlik degerden YUKSEK olmali."""
    inter = _FakeIntersection()
    # Son K snapshot'ta N kuyrugu: 1, 2, 3, 4, 5, 6 — duzgun yukseliyor
    for i, q in enumerate([1, 2, 3, 4, 5, 6]):
        snap = MetricsSnapshot(
            sim_time_s=float(i * 10),
            queue_lengths={Direction.NORTH: q, Direction.SOUTH: 0,
                           Direction.EAST: 0, Direction.WEST: 0},
            active_green=None,
        )
        inter.metrics.snapshots.append(snap)
    predicted = _predict_queue(inter, Direction.NORTH)
    # Son deger 6, slope=1 arac/10sn, forecast_horizon=30s -> +3
    # Beklenen ~9.0; en azindan son aniktan (6) yuksek olmali
    assert predicted > 6.0
    assert predicted == 9.0  # tam degerde de teyit


def test_predict_queue_clamps_negative_to_zero() -> None:
    """Hizla bosalan kuyrukta tahmin negatif olamaz."""
    inter = _FakeIntersection()
    # Kuyruk hizla bosaliyor: 10, 8, 6, 4, 2, 0
    for i, q in enumerate([10, 8, 6, 4, 2, 0]):
        snap = MetricsSnapshot(
            sim_time_s=float(i * 10),
            queue_lengths={Direction.NORTH: q, Direction.SOUTH: 0,
                           Direction.EAST: 0, Direction.WEST: 0},
            active_green=None,
        )
        inter.metrics.snapshots.append(snap)
    predicted = _predict_queue(inter, Direction.NORTH)
    # Son deger 0, slope=-2/10sn, forecast=30sn -> tahmin -6 ama 0'a clamp
    assert predicted == 0.0


def test_lookback_k_is_six_snapshots() -> None:
    """_LOOKBACK_K = 6 snapshot, yani 60 saniye tarihce."""
    assert _LOOKBACK_K == 6


def test_predictive_runs_full_4h_without_error() -> None:
    """Tam 4 saatlik kosum: simpy hata vermemeli, arac sayisi > 0."""
    cfg = SimConfig(seed=42, horizon_seconds=4 * 3600.0)
    intersection = run_with_controller(cfg, predictive_controller)
    report = intersection.metrics.build_report(cfg.horizon_seconds)
    assert report.vehicles_served > 0
    # Predictive de adaptif gibi cycle uretir (4 yesil faz = 1 cycle)
    assert report.full_cycle_count > 0
    # En azindan 4 yon (Kuzey/Guney/Dogu/Bati) icin yesil faz olmali
    assert report.green_phase_count >= 4
    # Predictive preemptive degil — preemption_count 0
    assert report.preemption_count == 0


# ---------- Hibrit score testleri (Faz Final v2 — hibrit fix) ---------------


def test_hybrid_score_constant_queue_equals_current() -> None:
    """Trend yokken (kuyruk degismiyor) hibrit skor = anlik kuyruk."""
    inter = _FakeIntersection()
    inter._q[Direction.NORTH] = 4
    # Son 6 snapshot'ta sabit kuyruk 4
    for i in range(6):
        snap = MetricsSnapshot(
            sim_time_s=float(i * 10),
            queue_lengths={Direction.NORTH: 4, Direction.SOUTH: 0,
                           Direction.EAST: 0, Direction.WEST: 0},
            active_green=None,
        )
        inter.metrics.snapshots.append(snap)
    # predicted == current (4), trend_bonus = 0, score = 4
    assert _hybrid_score(inter, Direction.NORTH) == 4.0


def test_hybrid_score_rising_queue_adds_bonus() -> None:
    """Kuyruk artiyorsa hibrit skor anlik kuyruktan YUKSEK olmali."""
    inter = _FakeIntersection()
    inter._q[Direction.NORTH] = 6  # anlik kuyruk
    # Yukselen trend: 1,2,3,4,5,6 -> predict = 9 (30 sn sonra)
    for i, q in enumerate([1, 2, 3, 4, 5, 6]):
        snap = MetricsSnapshot(
            sim_time_s=float(i * 10),
            queue_lengths={Direction.NORTH: q, Direction.SOUTH: 0,
                           Direction.EAST: 0, Direction.WEST: 0},
            active_green=None,
        )
        inter.metrics.snapshots.append(snap)
    score = _hybrid_score(inter, Direction.NORTH)
    # current=6, predicted=9, bonus = α × (9-6) = 0.3 × 3 = 0.9
    # score = 6 + 0.9 = 6.9
    assert score > 6.0  # anlik kuyruktan yuksek
    assert abs(score - (6.0 + HYBRID_ALPHA * 3.0)) < 1e-9


def test_hybrid_score_falling_queue_no_negative_bonus() -> None:
    """Azalan trend NEGATIF bonus yapmamali — score >= current."""
    inter = _FakeIntersection()
    inter._q[Direction.NORTH] = 0  # son anlik kuyruk
    # Azalan trend: 10,8,6,4,2,0 -> predict = 0 (negatif extrapolation 0'a clamp)
    for i, q in enumerate([10, 8, 6, 4, 2, 0]):
        snap = MetricsSnapshot(
            sim_time_s=float(i * 10),
            queue_lengths={Direction.NORTH: q, Direction.SOUTH: 0,
                           Direction.EAST: 0, Direction.WEST: 0},
            active_green=None,
        )
        inter.metrics.snapshots.append(snap)
    # predicted = 0, current = 0, bonus = max(0, 0-0) = 0, score = 0
    assert _hybrid_score(inter, Direction.NORTH) == 0.0


def test_hybrid_alpha_in_reasonable_range() -> None:
    """α sweep ile secildi — adaptive ile dengeli olmasi icin [0.1, 1.0]."""
    assert 0.1 <= HYBRID_ALPHA <= 1.0
