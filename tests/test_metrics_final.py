"""Faz Final — genisletilmis MetricsReport alanlari icin testler.

Test edilenler:
* Percentile dilim hesaplari (overall + per-type)
* Jain's fairness index sinirlari [1/n, 1]
* CO2 / yakit proxy formul dogrulugu
* Saatlik aggregation: bucket sayisi, throughput esitlik kontrolu
"""

from intersection_sim.domain.direction import Direction
from intersection_sim.domain.vehicle import Vehicle, VehicleType
from intersection_sim.metrics.metrics_collector import (
    CO2_GRAMS_PER_LITER_GASOLINE,
    IDLE_FUEL_RATE_L_PER_S,
    MetricsCollector,
    _jains_fairness,
    _percentile_dict,
)


def _v(pid: int, d: Direction, arrival: float, cross_start: float,
       vtype: VehicleType = VehicleType.NORMAL) -> Vehicle:
    return Vehicle(
        vehicle_id=pid, direction=d, vehicle_type=vtype,
        arrival_time=arrival,
        cross_start_time=cross_start,
        cross_end_time=cross_start + 2.0,
    )


# ---------- Percentile helper birim testleri --------------------------------


def test_percentile_dict_empty_returns_none_for_all_levels() -> None:
    """Hic veri yoksa p50..p99 hepsi None."""
    pct = _percentile_dict([])
    for k in ("p50", "p75", "p90", "p95", "p99"):
        assert pct[k] is None


def test_percentile_dict_constant_data_returns_same_value() -> None:
    """Tum bekleme degerleri ayniysa her percentile o deger olmali."""
    pct = _percentile_dict([10.0] * 50)
    for k in ("p50", "p75", "p90", "p95", "p99"):
        assert pct[k] == 10.0


def test_percentile_dict_uniform_p50_is_median() -> None:
    """0..99 uniform veride p50 medyani 49.5 olmali (np.percentile linear)."""
    pct = _percentile_dict([float(i) for i in range(100)])
    assert pct["p50"] == 49.5
    # p95 ~ 94.05 (linear interpolation)
    assert 93.0 < pct["p95"] < 95.0


# ---------- Jain's fairness sinir testleri ----------------------------------


def test_fairness_all_equal_is_one() -> None:
    """Tum yonler ayni beklemede ise F=1 (mukemmel adil)."""
    assert _jains_fairness([10.0, 10.0, 10.0, 10.0]) == 1.0


def test_fairness_single_dominant_approaches_min() -> None:
    """Tek yon avantajli (digerleri 0) ise F = 1/n = 0.25 (4 yon icin).

    Formul: F = (Sum x)^2 / (n * Sum x^2)
    [100, 0, 0, 0] -> 100^2 / (4 * 100^2) = 1/4 = 0.25
    """
    f = _jains_fairness([100.0, 0.0, 0.0, 0.0])
    assert f is not None
    assert abs(f - 0.25) < 1e-9


def test_fairness_all_zero_is_one() -> None:
    """Tum yonler 0 bekliyor — limit olarak 1.0 (mukemmel adil bos sistem)."""
    assert _jains_fairness([0.0, 0.0, 0.0, 0.0]) == 1.0


def test_fairness_none_filtered_out() -> None:
    """None degerler hesaplamadan disarida tutulmali."""
    f = _jains_fairness([10.0, 10.0, None, None])
    assert f == 1.0  # 2 yondeki esit beklemeden F=1


def test_fairness_single_value_returns_none() -> None:
    """Tek yondeki bekleme ile fairness yorumu yapilamaz — None doner."""
    assert _jains_fairness([10.0]) is None
    assert _jains_fairness([10.0, None, None, None]) is None


# ---------- Cevresel proxy formul testleri ----------------------------------


def test_co2_zero_idle_zero_emission() -> None:
    """Hicbir bekleme yoksa CO2 / yakit 0 olmali."""
    c = MetricsCollector()
    # Tek arac, 0 saniye bekleme
    c.record_vehicle_served(_v(0, Direction.NORTH, 0.0, 0.0))
    r = c.build_report(horizon_seconds=3600.0)
    assert r.total_idle_seconds == 0.0
    assert r.fuel_liters_proxy == 0.0
    assert r.co2_grams_proxy == 0.0


def test_co2_formula_matches_constants() -> None:
    """Toplam idle * IDLE_FUEL_RATE * CO2_PER_L olmali."""
    c = MetricsCollector()
    # 3 arac, her biri 100 sn bekleme -> 300 sn toplam idle
    c.record_vehicle_served(_v(0, Direction.NORTH, 0.0, 100.0))
    c.record_vehicle_served(_v(1, Direction.EAST, 0.0, 100.0))
    c.record_vehicle_served(_v(2, Direction.WEST, 0.0, 100.0))
    r = c.build_report(horizon_seconds=3600.0)
    expected_idle = 300.0
    expected_fuel = expected_idle * IDLE_FUEL_RATE_L_PER_S
    expected_co2 = expected_fuel * CO2_GRAMS_PER_LITER_GASOLINE
    assert abs(r.total_idle_seconds - expected_idle) < 1e-6
    assert abs(r.fuel_liters_proxy - expected_fuel) < 1e-9
    assert abs(r.co2_grams_proxy - expected_co2) < 1e-6


# ---------- Saatlik aggregation testleri ------------------------------------


def test_hourly_buckets_match_horizon() -> None:
    """4 saatlik koşumda 4 bucket olusmali."""
    c = MetricsCollector()
    r = c.build_report(horizon_seconds=4 * 3600.0)
    assert len(r.hourly_throughput) == 4
    assert len(r.hourly_mean_wait_s) == 4


def test_hourly_throughput_sums_to_total() -> None:
    """Saatlik throughput'larin toplami toplam gecen arac sayisina esit."""
    c = MetricsCollector()
    # Saat 0: 3 arac, saat 1: 5 arac, saat 2: 2 arac
    times = (
        [(0.0, 5.0)] * 3 +
        [(3700.0, 3710.0)] * 5 +
        [(7300.0, 7320.0)] * 2
    )
    for i, (a, c_start) in enumerate(times):
        c.record_vehicle_served(_v(i, Direction.NORTH, a, c_start))
    r = c.build_report(horizon_seconds=3 * 3600.0)
    assert r.hourly_throughput[0] == 3.0
    assert r.hourly_throughput[1] == 5.0
    assert r.hourly_throughput[2] == 2.0
    assert sum(r.hourly_throughput) == float(r.vehicles_served)


def test_hourly_mean_wait_empty_bucket_is_none() -> None:
    """Hic arac gelmemiş saatte mean_wait None olmali."""
    c = MetricsCollector()
    # Sadece saat 0'da arac
    c.record_vehicle_served(_v(0, Direction.NORTH, 100.0, 110.0))
    r = c.build_report(horizon_seconds=3 * 3600.0)
    assert r.hourly_mean_wait_s[0] is not None
    assert r.hourly_mean_wait_s[1] is None
    assert r.hourly_mean_wait_s[2] is None


def test_hourly_by_direction_has_all_directions() -> None:
    """hourly_mean_wait_by_direction_s 4 yonun hepsi icin liste tutmali."""
    c = MetricsCollector()
    r = c.build_report(horizon_seconds=2 * 3600.0)
    for d in Direction:
        assert d.value in r.hourly_mean_wait_by_direction_s
        assert len(r.hourly_mean_wait_by_direction_s[d.value]) == 2


# ---------- Percentile entegrasyon testleri ---------------------------------


def test_emergency_percentiles_isolated_from_normal() -> None:
    """Acil ve normal araclarin percentile alanlari ayrik hesaplanmali."""
    c = MetricsCollector()
    # 10 normal arac (her biri 20 sn bekleme), 5 acil (her biri 4 sn bekleme)
    for i in range(10):
        c.record_vehicle_served(
            _v(i, Direction.NORTH, 0.0, 20.0, VehicleType.NORMAL),
        )
    for i in range(5):
        c.record_vehicle_served(
            _v(10 + i, Direction.EAST, 0.0, 4.0, VehicleType.EMERGENCY),
        )
    r = c.build_report(horizon_seconds=3600.0)
    assert r.wait_percentiles_normal_s["p50"] == 20.0
    assert r.wait_percentiles_emergency_s["p50"] == 4.0
    # Overall: 15 deger, 10'u 20.0, 5'i 4.0; medyan 20.0
    assert r.wait_percentiles_s["p50"] == 20.0
